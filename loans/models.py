from django.db import models
from customers.models import Customer


class Loan(models.Model):
    loan_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    loan_amount = models.FloatField()
    tenure = models.IntegerField(help_text="Tenure in months")
    interest_rate = models.FloatField(help_text="Annual interest rate as percentage")
    monthly_repayment = models.FloatField()
    emis_paid_on_time = models.IntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'loans'

    def __str__(self):
        return f"Loan {self.loan_id} - Customer {self.customer_id}"

    @property
    def repayments_left(self):
        """Calculate remaining EMIs based on tenure and EMIs paid."""
        from datetime import date
        if self.end_date and date.today() > self.end_date:
            return 0
        paid = self.emis_paid_on_time
        return max(0, self.tenure - paid)

    @property
    def is_active(self):
        """Check if loan is currently active."""
        from datetime import date
        if self.end_date is None:
            return True
        return date.today() <= self.end_date
