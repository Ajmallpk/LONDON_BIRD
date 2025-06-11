from django.db import models
from products.models import Variant
from products.models import Size
from django.contrib.auth.models import User
from offer.models import ProductOffer, CategoryOffer
from django.utils import timezone


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _str_(self):
        return f"Cart for {self.user.username if self.user else 'Anonymous'}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def _str_(self):
        return f"{self.quantity} x {self.variant.product.name} ({self.size.size})"
    
    
    def get_original_price(self):
        """Return the original price of the product."""
        if self.variant.product.price is None:
            return 0
        return self.variant.product.price

    def get_discounted_price(self):
        """Calculate the discounted price based on applicable offers."""
        product_instance = self.variant.product
        current_date = timezone.now()

        
        discounted_price = product_instance.price
        applicable_offer = None

        
        try:
            product_offer = ProductOffer.objects.get(
                product=product_instance,
                is_active=True,
                valid_from__lte=current_date,
                valid_until__gte=current_date
            )
        except ProductOffer.DoesNotExist:
            product_offer = None

        
        try:
            category_offer = CategoryOffer.objects.get(
                category=product_instance.category,
                is_active=True,
                valid_from__lte=current_date,
                valid_until__gte=current_date
            )
        except CategoryOffer.DoesNotExist:
            category_offer = None

     
        if product_offer and category_offer:
            if product_offer.discount_percentage >= category_offer.discount_percentage:
                applicable_offer = product_offer
                discounted_price = product_instance.price * (1 - product_offer.discount_percentage / 100)
            else:
                applicable_offer = category_offer
                discounted_price = product_instance.price * (1 - category_offer.discount_percentage / 100)
        elif product_offer:
            applicable_offer = product_offer
            discounted_price = product_instance.price * (1 - product_offer.discount_percentage / 100)
        elif category_offer:
            applicable_offer = category_offer
            discounted_price = product_instance.price * (1 - category_offer.discount_percentage / 100)

        return discounted_price

    def get_total_original_price(self):
        """Calculate total original price (quantity * original price)."""
        return self.quantity * self.get_original_price()

    def get_total_discounted_price(self):
        """Calculate total discounted price (quantity * discounted price)."""
        return self.quantity * self.get_discounted_price()

    def get_savings(self):
        """Calculate savings based on the difference between original and discounted price."""
        return self.get_total_original_price() - self.get_total_discounted_price()



