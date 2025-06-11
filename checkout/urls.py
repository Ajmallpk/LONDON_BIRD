from django.urls import path
from . import views



from django.urls import path
from . import views

urlpatterns = [
  
    path('checkout/', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
    path('order-success/<str:order_id>/', views.order_success, name='order_success'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
]