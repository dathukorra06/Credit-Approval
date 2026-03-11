import math
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Customer
from .serializers import CustomerRegisterSerializer, CustomerResponseSerializer


class RegisterCustomerView(APIView):
    """
    POST /register
    Register a new customer and calculate their approved credit limit.
    approved_limit = 36 * monthly_salary (rounded to nearest lakh)
    """

    def post(self, request):
        serializer = CustomerRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        # Check if phone number already exists
        if Customer.objects.filter(phone_number=data['phone_number']).exists():
            return Response(
                {'error': 'A customer with this phone number already exists.'},
                status=status.HTTP_409_CONFLICT
            )

        monthly_salary = data['monthly_income']

        # Calculate approved limit: 36 * monthly_salary, rounded to nearest lakh (100,000)
        raw_limit = 36 * monthly_salary
        approved_limit = round(raw_limit / 100000) * 100000

        customer = Customer.objects.create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            age=data['age'],
            phone_number=data['phone_number'],
            monthly_salary=monthly_salary,
            approved_limit=approved_limit,
            current_debt=0.0,
        )

        response_serializer = CustomerResponseSerializer(customer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
