
from django.urls import path
from . import views



urlpatterns = [
    path('wallet/', views.wallet_page, name='wallet_page'),
    path('wallet/add-money/', views.add_money, name='add_money'),
]
