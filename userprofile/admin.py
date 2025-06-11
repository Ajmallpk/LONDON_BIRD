from django.contrib import admin
from .models import Address,ShippingAddress
# Register your models here.


admin.site.register(Address),
admin.site.register(ShippingAddress),