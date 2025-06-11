from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from checkout.models import Order  
from django.contrib.auth.models import User
class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('Fixed', 'Fixed Amount'),
        ('Percentage', 'Percentage'),
    ]

    code = models.CharField(max_length=20, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='Fixed')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Maximum discount amount for percentage discounts")
    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Minimum purchase amount to apply the coupon")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    # usage_limit = models.PositiveIntegerField(default=1, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupons', null=True, blank=True)  
    def __str__(self):
        return self.code

    def clean(self):
        if self.valid_until <= self.valid_from:
            raise ValidationError("Valid until date must be after valid from date.")
        if self.discount_amount <= 0:
            raise ValidationError("Discount amount must be greater than zero.")
        if self.discount_type == 'Percentage' and (self.discount_amount > 100):
            raise ValidationError("Percentage discount cannot exceed 100%.")
        if self.discount_type == 'Percentage' and (not self.max_discount or self.max_discount <= 0):
            raise ValidationError("Maximum discount must be provided and greater than zero for percentage discounts.")
        if self.min_purchase < 0:
            raise ValidationError("Minimum purchase amount cannot be negative.")

    def is_valid(self):
        now = timezone.now()
       
        return (self.is_active and 
                self.valid_from <= now <= self.valid_until)

    def get_usage_count(self, user=None):
        """
        Get the number of times the coupon has been used.
        If user is provided, returns the usage count for that specific user.
        If user is None, returns the global usage count (for admin purposes).
        """
        query = self.couponusage_set.all()
        if user:
            query = query.filter(order__user=user)
        return query.count()

    class Meta:
        ordering = ['-created_at']

class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Coupon {self.coupon.code} used in Order {self.order.id}"