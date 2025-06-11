from django.urls import path
from .views import sales_report  # Adjust based on your views file

urlpatterns = [
    
    path('sales-report/', sales_report, name='sales_report'),
]