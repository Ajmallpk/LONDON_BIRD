from django.urls import path
from .import views

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('<str:order_id>/', views.order_detail, name='order_detail'),
    path('<str:order_id>/update-address/', views.update_shipping_address, name='update_shipping_address'),
    path('success/<str:order_id>/', views.order_success, name='order_success'),
    path('<str:order_id>/invoice/', views.download_invoice, name='download_invoice'),
    path('<str:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('<str:order_id>/cancel-reason/', views.cancel_reason, name='cancel_reason'),
    path('<str:order_id>/<str:item_id>/return-reason/', views.return_reason, name='return_reason'),
    path('orders/handle-return/', views.handle_return, name='handle_return'),
    # path('handle-return/', views.handle_return, name='handle_return'),

]