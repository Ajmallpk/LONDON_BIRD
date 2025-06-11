from django.db import models
from django.utils.timezone import now
from products.models import product
from categories.models import categories

class ProductOffer(models.Model):
    product = models.ForeignKey(product, on_delete=models.CASCADE, related_name='product_offers')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Discount percentage (e.g., 20 for 20%)")
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def is_valid(self):
        current_time = now()
        return self.is_active and self.valid_from <= current_time <= self.valid_until

    def __str__(self):
        return f"{self.discount_percentage}% off on {self.product.name}"

class CategoryOffer(models.Model):
    category = models.ForeignKey(categories, on_delete=models.CASCADE, related_name='category_offers')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Discount percentage (e.g., 30 for 30%)")
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def is_valid(self):
        current_time = now()
        return self.is_active and self.valid_from <= current_time <= self.valid_until

    def __str__(self):
        return f"{self.discount_percentage}% off on {self.category.name}"

def get_best_offer_for_product(product_instance):
    current_time = now()
    best_discount = 0
    best_offer_type = None

    product_offers = ProductOffer.objects.filter(
        product=product_instance,
        is_active=True,
        valid_from__lte=current_time,
        valid_until__gte=current_time
    )
    for offer in product_offers:
        if offer.discount_percentage > best_discount:
            best_discount = offer.discount_percentage
            best_offer_type = 'product'

    if product_instance.category:
        category_offers = CategoryOffer.objects.filter(
            category=product_instance.category,
            is_active=True,
            valid_from__lte=current_time,
            valid_until__gte=current_time
        )
        for offer in category_offers:
            if offer.discount_percentage > best_discount:
                best_discount = offer.discount_percentage
                best_offer_type = 'category'

    return best_discount, best_offer_type