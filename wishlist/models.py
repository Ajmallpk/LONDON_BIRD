from django.db import models
from django.db import models
from django.contrib.auth.models import User
from products.models import product, Variant, Size

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, null=True, blank=True)
    size = models.ForeignKey(Size, on_delete=models.CASCADE, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'variant', 'size')

    def __str__(self):
        return f"{self.user.username}'s wishlist: {self.variant.product.name} ({self.variant.color}) , ({self.size.size})"