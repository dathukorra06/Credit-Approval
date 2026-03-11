from datetime import date
from dateutil.relativedelta import relativedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from customers.models import Customer
from .models import Loan
from .serializers import (
    CheckEligibilityRequestSerializer,
    CheckEligibilityResponseSerializer,
    CreateLoanRequestSerializer,
    ViewLoanSerializer,
    LoanListItemSerializer,
)
from .credit_service import get_loan_eligibility, calculate_monthly_installment


class CheckEligibilityView(APIView):
    """
    POST /check-eligibility
    Check whether a customer is eligible for a loan based on credit score.
    """

    def post(self, request):
        serializer = CheckEligibilityRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        customer_id = data['customer_id']

        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': f'Customer {customer_id} not found.'}, status=status.HTTP_404_NOT_FOUND)

        result = get_loan_eligibility(
            customer=customer,
            loan_amount=data['loan_amount'],
            interest_rate=data['interest_rate'],
            tenure=data['tenure'],
        )

        response_data = {
            'customer_id': customer_id,
            'approval': result['approved'],
            'interest_rate': data['interest_rate'],
            'corrected_interest_rate': result['corrected_interest_rate'],
            'tenure': data['tenure'],
            'monthly_installment': result['monthly_installment'],
        }

        return Response(CheckEligibilityResponseSerializer(response_data).data, status=status.HTTP_200_OK)


class CreateLoanView(APIView):
    """
    POST /create-loan
    Process and create a new loan if eligible.
    """

    def post(self, request):
        serializer = CreateLoanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        customer_id = data['customer_id']

        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': f'Customer {customer_id} not found.'}, status=status.HTTP_404_NOT_FOUND)

        result = get_loan_eligibility(
            customer=customer,
            loan_amount=data['loan_amount'],
            interest_rate=data['interest_rate'],
            tenure=data['tenure'],
        )

        if not result['approved']:
            return Response({
                'loan_id': None,
                'customer_id': customer_id,
                'loan_approved': False,
                'message': result.get('rejection_reason', 'Loan not approved based on credit assessment.'),
                'monthly_installment': result['monthly_installment'],
            }, status=status.HTTP_200_OK)

        # Create the loan
        today = date.today()
        end_date = today + relativedelta(months=data['tenure'])

        loan = Loan.objects.create(
            customer=customer,
            loan_amount=data['loan_amount'],
            tenure=data['tenure'],
            interest_rate=result['corrected_interest_rate'],
            monthly_repayment=result['monthly_installment'],
            emis_paid_on_time=0,
            start_date=today,
            end_date=end_date,
        )

        # Update customer's current debt
        customer.current_debt = (customer.current_debt or 0) + data['loan_amount']
        customer.save(update_fields=['current_debt'])

        return Response({
            'loan_id': loan.loan_id,
            'customer_id': customer_id,
            'loan_approved': True,
            'message': 'Loan approved successfully.',
            'monthly_installment': result['monthly_installment'],
        }, status=status.HTTP_201_CREATED)


class ViewLoanView(APIView):
    """
    GET /view-loan/<loan_id>
    View details of a specific loan including customer info.
    """

    def get(self, request, loan_id):
        try:
            loan = Loan.objects.select_related('customer').get(pk=loan_id)
        except Loan.DoesNotExist:
            return Response({'error': f'Loan {loan_id} not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ViewLoanSerializer(loan)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ViewCustomerLoansView(APIView):
    """
    GET /view-loans/<customer_id>
    View all loans for a specific customer.
    """

    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': f'Customer {customer_id} not found.'}, status=status.HTTP_404_NOT_FOUND)

        loans = Loan.objects.filter(customer=customer)
        serializer = LoanListItemSerializer(loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
