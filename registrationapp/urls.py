
from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('login/', views.login__view, name='login'),
    path('register/', views.register, name='register'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('resend_otp/', views.resend_otp, name='resend_otp'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('logout/', LogoutView.as_view(next_page='index'), name='logout'),
    path('referral-dashboard/', views.referral_dashboard, name='referral_dashboard'),
]


