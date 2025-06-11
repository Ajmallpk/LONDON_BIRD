from django.urls import path,include
from . import views 

urlpatterns = [

  path('/category_list',views.category_list, name='category_list'),
  path('/add_category',views.add_category, name='add_category'),
  path('/edit_category/<int:id>',views.edit_category,name='edit_category'),
  path('/category_list/unlist_category/<int:id>',views.unlist_category,name='Unlist_category'),
]