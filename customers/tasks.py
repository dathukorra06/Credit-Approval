import os
import logging
from celery import shared_task
from django.conf import settings
import openpyxl

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def ingest_customer_data(self):
    """
    Background task to ingest customer data from customer_data.xlsx
    into the database on startup.
    """
    from customers.models import Customer

    file_path = os.path.join(settings.DATA_DIR, 'customer_data.xlsx')

    if not os.path.exists(file_path):
        logger.error(f"Customer data file not found: {file_path}")
        return {'status': 'error', 'message': 'File not found'}

    try:
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active

        created_count = 0
        skipped_count = 0

        # Skip header row
        rows = list(ws.iter_rows(min_row=2, values_only=True))

        for row in rows:
            if not any(row):
                continue

            customer_id, first_name, last_name, age, phone_number, monthly_salary, approved_limit = row

            if not customer_id:
                continue

            # current_debt defaults to 0 if not in source data
            _, created = Customer.objects.update_or_create(
                customer_id=int(customer_id),
                defaults={
                    'first_name': str(first_name) if first_name else '',
                    'last_name': str(last_name) if last_name else '',
                    'age': int(age) if age else None,
                    'phone_number': int(phone_number) if phone_number else 0,
                    'monthly_salary': int(monthly_salary) if monthly_salary else 0,
                    'approved_limit': int(approved_limit) if approved_limit else 0,
                    'current_debt': 0.0,
                }
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1

        logger.info(f"Customer ingestion complete: {created_count} created, {skipped_count} updated")
        return {'status': 'success', 'created': created_count, 'updated': skipped_count}

    except Exception as exc:
        logger.error(f"Error ingesting customer data: {exc}")
        raise self.retry(exc=exc, countdown=5)
