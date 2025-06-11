from django.urls import path
from .import views

urlpatterns = [
    
    
    
   path('', views.view_wishlist, name='view_wishlist'),
    path('add/<int:variant_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove/<int:wishlist_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('move-to-cart/<int:wishlist_id>/', views.move_to_cart, name='move_to_cart'),
    path('count/', views.get_wishlist_count, name='get_wishlist_count'),
    
    
    
]

  

