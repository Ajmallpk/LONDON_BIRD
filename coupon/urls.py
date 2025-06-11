from django.urls import path
from . import views

urlpatterns = [
    path('', views.coupon_management, name='coupon_management'),
    path('add/', views.add_coupon, name='add_coupon'),
    path('edit/<int:coupon_id>/', views.edit_coupon, name='edit_coupon'),
    path('delete/<int:coupon_id>/', views.delete_coupon, name='delete_coupon'),
    path('coupons/', views.user_available_coupons, name='user_available_coupons'),
]