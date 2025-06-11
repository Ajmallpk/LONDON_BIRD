from django.urls import path
from . import views


urlpatterns=[

  path('userprofile/',views.user_profile,name='user_profile'),
  path('editprofile/',views.edit_profile,name='edit_profile'),
  path('editemail/',views.edit_email,name='edit_email'),
  path('verifyotp/',views.profile_verify,name='verify_mail'),
  path('changepassword/',views.change_password,name='change_password'),
  path('address/',views.address,name='user_address'),
  # path('add_address/',views.add_address,name='add_address'),
  path('set_default_address/<int:address_id>/', views.set_default_address, name='set_default_address'),
  

  


]

  
  


