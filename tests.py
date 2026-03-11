"""
Unit tests for the Credit Approval System.
Run with: python manage.py test
"""
from datetime import date, timedelta
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from customers.models import Customer
from loans.models import Loan
from loans.credit_service import calculate_credit_score, calculate_monthly_installment, get_loan_eligibility


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def make_customer(**kwargs):
    defaults = {
        'first_name': 'Test',
        'last_name': 'User',
        'age': 30,
        'phone_number': 9000000001,
        'monthly_salary': 50000,
        'approved_limit': 1800000,
        'current_debt': 0,
    }
    defaults.update(kwargs)
    return Customer.objects.create(**defaults)


def make_loan(customer, **kwargs):
    defaults = {
        'loan_amount': 100000,
        'tenure': 12,
        'interest_rate': 10.0,
        'monthly_repayment': 8792.0,
        'emis_paid_on_time': 12,
        'start_date': date.today() - timedelta(days=400),
        'end_date': date.today() - timedelta(days=30),
    }
    defaults.update(kwargs)
    return Loan.objects.create(customer=customer, **defaults)


# ---------------------------------------------------------------------------
# Credit service tests
# ---------------------------------------------------------------------------

class TestCalculateMonthlyInstallment(TestCase):

    def test_zero_interest(self):
        emi = calculate_monthly_installment(12000, 0, 12)
        self.assertAlmostEqual(emi, 1000.0, places=2)

    def test_standard_emi(self):
        # 100000 at 12% annual for 12 months
        emi = calculate_monthly_installment(100000, 12, 12)
        self.assertAlmostEqual(emi, 8884.88, places=1)

    def test_emi_positive(self):
        emi = calculate_monthly_installment(500000, 10, 60)
        self.assertGreater(emi, 0)


class TestCreditScore(TestCase):

    def test_no_loans_returns_50(self):
        customer = make_customer(phone_number=9000000010)
        score = calculate_credit_score(customer)
        self.assertEqual(score, 50)

    def test_high_debt_returns_zero(self):
        customer = make_customer(phone_number=9000000011, approved_limit=100000)
        # Active loan exceeding approved limit
        make_loan(customer, loan_amount=200000,
                  start_date=date.today() - timedelta(days=30),
                  end_date=date.today() + timedelta(days=300))
        score = calculate_credit_score(customer)
        self.assertEqual(score, 0)

    def test_perfect_payment_history(self):
        customer = make_customer(phone_number=9000000012)
        make_loan(customer, emis_paid_on_time=12, tenure=12,
                  start_date=date.today() - timedelta(days=400),
                  end_date=date.today() - timedelta(days=30))
        score = calculate_credit_score(customer)
        self.assertGreater(score, 30)

    def test_score_in_valid_range(self):
        customer = make_customer(phone_number=9000000013)
        for i in range(3):
            make_loan(customer, emis_paid_on_time=6, tenure=12,
                      start_date=date.today() - timedelta(days=400),
                      end_date=date.today() - timedelta(days=30))
        score = calculate_credit_score(customer)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


class TestGetLoanEligibility(TestCase):

    def test_approved_high_score(self):
        customer = make_customer(phone_number=9000000020)
        # Add some good history
        make_loan(customer, emis_paid_on_time=12, tenure=12,
                  start_date=date.today() - timedelta(days=400),
                  end_date=date.today() - timedelta(days=30))
        result = get_loan_eligibility(customer, 50000, 15.0, 12)
        self.assertIn('approved', result)
        self.assertIn('monthly_installment', result)

    def test_emi_exceeds_50_percent_salary(self):
        customer = make_customer(phone_number=9000000021, monthly_salary=20000)
        # Active loan with high EMI
        make_loan(customer, monthly_repayment=15000, tenure=24,
                  start_date=date.today() - timedelta(days=10),
                  end_date=date.today() + timedelta(days=700))
        result = get_loan_eligibility(customer, 50000, 10.0, 12)
        self.assertFalse(result['approved'])

    def test_corrected_interest_rate_applied(self):
        customer = make_customer(phone_number=9000000022)
        # Low credit history to get score in 30-50 range
        for i in range(8):
            make_loan(customer, emis_paid_on_time=0, tenure=12,
                      start_date=date.today() - timedelta(days=400),
                      end_date=date.today() - timedelta(days=30))
        result = get_loan_eligibility(customer, 50000, 8.0, 12)
        # If approved with low score bracket, rate should be corrected
        if result['approved']:
            self.assertGreaterEqual(result['corrected_interest_rate'], 12.0)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestRegisterAPI(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_register_success(self):
        payload = {
            'first_name': 'Alice',
            'last_name': 'Smith',
            'age': 28,
            'monthly_income': 60000,
            'phone_number': 9876543210,
        }
        response = self.client.post('/register', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn('customer_id', data)
        self.assertEqual(data['approved_limit'], 2200000)  # 36*60000=2160000 → nearest lakh = 2200000

    def test_register_duplicate_phone(self):
        make_customer(phone_number=9111111111)
        payload = {
            'first_name': 'Bob',
            'last_name': 'Jones',
            'age': 35,
            'monthly_income': 50000,
            'phone_number': 9111111111,
        }
        response = self.client.post('/register', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_register_missing_fields(self):
        response = self.client.post('/register', {'first_name': 'Only'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestCheckEligibilityAPI(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer(phone_number=9222222222)

    def test_check_eligibility_valid(self):
        payload = {
            'customer_id': self.customer.customer_id,
            'loan_amount': 100000,
            'interest_rate': 15.0,
            'tenure': 12,
        }
        response = self.client.post('/check-eligibility', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('approval', data)
        self.assertIn('monthly_installment', data)
        self.assertIn('corrected_interest_rate', data)

    def test_check_eligibility_customer_not_found(self):
        payload = {
            'customer_id': 99999,
            'loan_amount': 100000,
            'interest_rate': 15.0,
            'tenure': 12,
        }
        response = self.client.post('/check-eligibility', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestCreateLoanAPI(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer(phone_number=9333333333)
        # Good payment history
        make_loan(self.customer, emis_paid_on_time=12, tenure=12,
                  start_date=date.today() - timedelta(days=400),
                  end_date=date.today() - timedelta(days=30))

    def test_create_loan_success(self):
        payload = {
            'customer_id': self.customer.customer_id,
            'loan_amount': 50000,
            'interest_rate': 15.0,
            'tenure': 12,
        }
        response = self.client.post('/create-loan', payload, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        data = response.json()
        self.assertIn('loan_approved', data)
        self.assertIn('monthly_installment', data)

    def test_create_loan_invalid_customer(self):
        payload = {
            'customer_id': 99999,
            'loan_amount': 50000,
            'interest_rate': 15.0,
            'tenure': 12,
        }
        response = self.client.post('/create-loan', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestViewLoanAPI(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer(phone_number=9444444444)
        self.loan = make_loan(self.customer,
                              start_date=date.today() - timedelta(days=10),
                              end_date=date.today() + timedelta(days=350))

    def test_view_loan_success(self):
        response = self.client.get(f'/view-loan/{self.loan.loan_id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['loan_id'], self.loan.loan_id)
        self.assertIn('customer', data)

    def test_view_loan_not_found(self):
        response = self.client.get('/view-loan/999999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestViewCustomerLoansAPI(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer(phone_number=9555555555)
        make_loan(self.customer)
        make_loan(self.customer, loan_amount=200000, tenure=24)

    def test_view_all_loans(self):
        response = self.client.get(f'/view-loans/{self.customer.customer_id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 2)

    def test_view_loans_invalid_customer(self):
        response = self.client.get('/view-loans/99999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
