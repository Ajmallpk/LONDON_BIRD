from django.urls import path
from . import views

urlpatterns = [
    path('payment/<str:order_id>/', views.initiate_payment, name='initiate_payment'),
    path('payment/', views.initiate_combined_payment, name='initiate_combined_payment'),

    
    path('verify/', views.verify_payment, name='verify_payment'),
    path('success/<str:order_id>/', views.payment_success, name='payment_success'),
    path('failure/<str:order_id>/', views.payment_failure, name='payment_failure'),
   
]