import os
import logging
from celery import shared_task
from django.conf import settings
import openpyxl
from datetime import datetime

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def ingest_loan_data(self):
    """
    Background task to ingest loan data from loan_data.xlsx
    into the database on startup.
    Depends on customers already being ingested.
    """
    from loans.models import Loan
    from customers.models import Customer

    file_path = os.path.join(settings.DATA_DIR, 'loan_data.xlsx')

    if not os.path.exists(file_path):
        logger.error(f"Loan data file not found: {file_path}")
        return {'status': 'error', 'message': 'File not found'}

    try:
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active

        created_count = 0
        skipped_count = 0
        error_count = 0

        rows = list(ws.iter_rows(min_row=2, values_only=True))

        for row in rows:
            if not any(row):
                continue

            customer_id, loan_id, loan_amount, tenure, interest_rate, monthly_payment, emis_on_time, start_date, end_date = row

            if not loan_id or not customer_id:
                continue

            try:
                customer = Customer.objects.get(pk=int(customer_id))
            except Customer.DoesNotExist:
                logger.warning(f"Customer {customer_id} not found, skipping loan {loan_id}")
                error_count += 1
                continue

            # Parse dates
            def parse_date(val):
                if val is None:
                    return None
                if isinstance(val, datetime):
                    return val.date()
                try:
                    return datetime.strptime(str(val), '%Y-%m-%d').date()
                except Exception:
                    try:
                        return datetime.strptime(str(val), '%d-%m-%Y').date()
                    except Exception:
                        return None

            _, created = Loan.objects.update_or_create(
                loan_id=int(loan_id),
                defaults={
                    'customer': customer,
                    'loan_amount': float(loan_amount) if loan_amount else 0.0,
                    'tenure': int(tenure) if tenure else 0,
                    'interest_rate': float(interest_rate) if interest_rate else 0.0,
                    'monthly_repayment': float(monthly_payment) if monthly_payment else 0.0,
                    'emis_paid_on_time': int(emis_on_time) if emis_on_time else 0,
                    'start_date': parse_date(start_date),
                    'end_date': parse_date(end_date),
                }
            )

            if created:
                created_count += 1
            else:
                skipped_count += 1

        logger.info(f"Loan ingestion complete: {created_count} created, {skipped_count} updated, {error_count} errors")
        return {'status': 'success', 'created': created_count, 'updated': skipped_count, 'errors': error_count}

    except Exception as exc:
        logger.error(f"Error ingesting loan data: {exc}")
        raise self.retry(exc=exc, countdown=10)
