from django.urls import path
from .import views
from django.conf import settings
from django.conf.urls.static import static




urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('block-user/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock-user/<int:user_id>/', views.unblock_user, name='unblock_user'),
    path('users/', views.user_management, name='user_management'),
    path('orders/', views.admin_order_list, name='admin_orders_list'),
    path('orders/<str:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('return-requests/', views.return_requests, name='return_requests'),
    path('inventory/', views.inventory_management, name='inventory_management'),  
    # path('categories/delete/<int:category_id>/', views.delete_category, name='delete_category'),
    # path('logout/', views.logout_view, name='logout'),
    path('ledger/',views.generate_ledger_pdf,name='ledger'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
 
