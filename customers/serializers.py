from rest_framework import serializers
from .models import Customer


class CustomerRegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    age = serializers.IntegerField()
    monthly_income = serializers.IntegerField()
    phone_number = serializers.IntegerField()


class CustomerResponseSerializer(serializers.ModelSerializer):
    monthly_income = serializers.IntegerField(source='monthly_salary')

    name = serializers.CharField(source='first_name')

    class Meta:
        model = Customer
        fields = ['customer_id', 'name', 'age', 'monthly_income', 'approved_limit', 'phone_number']
