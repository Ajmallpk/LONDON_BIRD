from django.urls import path
from . import views

urlpatterns=[

  path('products/',views.product_list,name='product_list'),
  path('products/add',views.add_product,name='add_product'),
  path('products/edit/<int:product_id>',views.edit_product,name='edit_product'),
  path('products/<int:product_id>/toggle-status/',views.toggle_product_status,name='toggle_product_status'),
  path('products/details/<int:product_id>/',views.product_details,name='product_details'),
  path('variant/details/<int:product_id>/<int:variant_id>/',views.variant_details,name='variant_details'),
  path('shop/',views.shop,name='shop'),
  path('products/variants/add/<int:product_id>/',views.add_variant,name='add_variant'),
  path('products/variant/edit/<int:variant_id>/',views.edit_variant,name='edit_variant'),
  path('products/variant/list/<int:product_id>/',views.list_variants,name='list_variants'),
  path('products/variant/delete/<int:variant_id>/',views.delete_variant,name='delete_variant'),
  path('products/variant/size/<int:variant_id>/',views.add_size,name='add_size'),
  path('products/size/list/<int:variant_id>/',views.list_size,name='list_size'),
  path('products/variant/list-variant/<int:variant_id>/', views.list_variant, name='list_variant'),
  path('products/variant/unlist-variant/<int:variant_id>/', views.unlist_variant, name='unlist_variant'),
  
  


]