from django.urls import path
from . import views

urlpatterns = [
    path('offer-management/', views.offer_management, name='offer_management'),
    path('add-product-offer/', views.add_product_offer, name='add_product_offer'),
    path('edit-product-offer/<int:offer_id>/', views.edit_product_offer, name='edit_product_offer'),
    path('delete-product-offer/<int:offer_id>/', views.delete_product_offer, name='delete_product_offer'),
    path('add-category-offer/', views.add_category_offer, name='add_category_offer'),
    path('edit-category-offer/<int:offer_id>/', views.edit_category_offer, name='edit_category_offer'),
    path('delete-category-offer/<int:offer_id>/', views.delete_category_offer, name='delete_category_offer'),
]