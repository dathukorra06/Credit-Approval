"""
Management command to trigger background data ingestion tasks.
Usage: python manage.py ingest_data
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Trigger background Celery tasks to ingest customer and loan data from Excel files.'

    def handle(self, *args, **options):
        from customers.tasks import ingest_customer_data
        from loans.tasks import ingest_loan_data

        self.stdout.write('Dispatching customer data ingestion task...')
        result_c = ingest_customer_data.delay()
        self.stdout.write(f'  Task ID: {result_c.id}')

        self.stdout.write('Dispatching loan data ingestion task...')
        result_l = ingest_loan_data.delay()
        self.stdout.write(f'  Task ID: {result_l.id}')

        self.stdout.write(self.style.SUCCESS(
            'Both ingestion tasks dispatched. Monitor Celery worker logs for progress.'
        ))
