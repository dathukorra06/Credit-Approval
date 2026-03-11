from django.urls import path
from .views import RegisterCustomerView

urlpatterns = [
    path('register', RegisterCustomerView.as_view(), name='register-customer'),
]
