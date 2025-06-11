import uuid
from django.db import models
from django.contrib.auth.models import User
from products.models import product, Variant, Size
from userprofile.models import Address, ShippingAddress
from django.utils import timezone
from datetime import timedelta
from offer.models import ProductOffer, CategoryOffer
from decimal import Decimal


def generate_order_id():
    
    date_part = timezone.now().strftime("%Y%m%d")  
    random_part = uuid.uuid4().hex[:6].upper()  
    return f"ORD-{date_part}-{random_part}"

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out For Delivery'),
        ('delivered', 'Delivered'),
        ('canceled', 'Canceled'),
        
    ]

    id = models.CharField(primary_key=True, max_length=50, default=generate_order_id, editable=False)  
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(ShippingAddress, on_delete=models.SET_NULL, null=True)
    payment_method = models.CharField(max_length=20)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, default='Pending')
    discount_applied = models.BooleanField(default=False)
    discount_coupon_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    balance_refund = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='processing')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    retry_payment_attempts = models.PositiveIntegerField(default=0)
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True) 
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    is_refunded = models.BooleanField(default=False)
    product_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

    def update_order(self):
        """
        Update the overall order status based on the status of its items.
        This method is called after item statuses are updated (e.g., in return_requests).
        It does not override the admin's manual status updates.
        """
        order_items = self.items.all()
        if not order_items.exists():
            if self.status != 'canceled': 
                self.status = 'canceled'
                self.save(update_fields=['status'])
            return True

        final_states = ['delivered', 'canceled', 'return_requested', 'returned', 'return_denied']
        all_items_in_final_state = all(item.status in final_states for item in order_items)

        print(f"All items in final state: {all_items_in_final_state}")

        if all_items_in_final_state:
            canceled_count = sum(1 for item in order_items if item.status == 'canceled')
            delivered_count = sum(1 for item in order_items if item.status == 'delivered')
            return_requested_count = sum(1 for item in order_items if item.status == 'return_requested')
            returned_count = sum(1 for item in order_items if item.status == 'returned')
            total_items = len(order_items)

            print(f"Canceled items: {canceled_count}, Delivered items: {delivered_count}, Return Requested items: {return_requested_count}, Returned items: {returned_count}")

            if canceled_count == total_items:
                print("All items are canceled. Setting order status to 'canceled'.")
                if self.status != 'canceled':
                    self.status = 'canceled'
            elif canceled_count + returned_count == total_items and returned_count >= 1 and canceled_count >= 1:
                print("All items are either canceled or returned. Setting order status to 'canceled'.")
                if self.status != 'canceled':
                    self.status = 'canceled'
            elif returned_count == total_items:
                print("All items are returned. Setting order status to 'returned'.")
                if self.status != 'returned':
                    self.status = 'returned'
            elif return_requested_count == total_items:
                print("All items are return requested. Setting order status to 'return_requested'.")
                if self.status != 'return_requested':
                    self.status = 'return_requested'
            elif delivered_count == total_items:
                print("All items are delivered. Setting order status to 'delivered'.")
                if self.status != 'delivered':
                    self.status = 'delivered'
            else:
                print("Mixed final states. Setting order status to 'delivered'.")
                if self.status not in ['canceled', 'returned', 'return_requested', 'delivered']:
                    self.status = 'delivered'
        else:
            print("Not all items are in final states. Setting order status to 'pending' if not manually set.")
            if self.status not in ['pending', 'shipped', 'out_for_delivery']:
                self.status = 'pending'

        self.save(update_fields=['status'])
        return True
        
    def update_status(self, new_status):
        """
        Update the order status and sync the status of all items.
        Also handle stock adjustments.
        Returns True if the update is successful, False otherwise.
        """
        
        if new_status not in [choice[0] for choice in self.ORDER_STATUS_CHOICES]:
            return False

     
        if new_status == 'canceled':
            if not self.can_be_canceled:
                return False

        status_mapping = {
            'pending': 'order_placed',
            'shipped': 'shipped',
            'out_for_delivery': 'out_for_delivery',
            'delivered': 'delivered',
            'canceled': 'canceled',
        }

        item_status = status_mapping.get(new_status)
        if not item_status:
            return False

     
        order_items = self.items.all()
        all_updated = True
        for item in order_items:
            if item.can_update_status(item_status):
                
                if item_status == 'canceled' and item.status not in ['canceled', 'returned', 'return_denied']:
                    if item.size:
                        item.size.stock += item.quantity
                        item.size.save()
                item.status = item_status
                item.updated_at = timezone.now()
                item.save()
            else:
                all_updated = False

       
        if all_updated:
            self.status = new_status
            self.save(update_fields=['status'])
            self.update_order()
            return True
        return False

    def decrease_stock(self):
        """
        Decrease stock when the order is placed.
        """
        for item in self.items.all():
            if item.size:
                size = item.size
                if size.stock >= item.quantity:
                    size.stock -= item.quantity
                    size.save()
                else:
                    raise ValueError(f"Not enough stock for {size}")

    @property
    def can_be_canceled(self):
        """
        Check if the entire order can be canceled.
        An order can be canceled if all its items can be canceled.
        """
        return all(item.can_update_status('canceled') for item in self.items.all())

    @property
    def can_be_returned(self):
        """
        Check if the order can be returned.
        An order can be returned if its status is 'delivered' (all items delivered)
        and it is within 7 days of the last update (when it was marked as delivered).
        """
        if self.status != 'delivered':
            return False
        time_difference = timezone.now() - self.updated_at
        return time_difference <= timedelta(days=7)
    
    
    
class OrderItem(models.Model):
    ORDER_ITEM_STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('order_placed', 'Order Placed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out For Delivery'),
        ('delivered', 'Delivered'),
        ('canceled', 'Canceled'),
        ('return_requested', 'Return Requested'),
        ('returned', 'Returned'),
        ('return_denied','Return_denied'),
        
        
    ]

    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(product, on_delete=models.CASCADE)
    product_variant = models.ForeignKey(Variant, on_delete=models.CASCADE, null=True, blank=True)
    size = models.ForeignKey(Size, on_delete=models.CASCADE, null=True, blank=True) 
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=ORDER_ITEM_STATUS_CHOICES, default='processing')
    cancel_reason = models.TextField(blank=True, null=True)
    return_reason = models.TextField(blank=True, null=True)
    return_requested_at = models.DateTimeField(blank=True, null=True)
    returned_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    final_offer_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def can_update_status(self, new_status):
        allowed_transitions = {
            'processing': ['order_placed'],
            'order_placed': ['shipped', 'canceled'],
            'shipped': ['out_for_delivery', 'canceled'],
            'out_for_delivery': ['delivered', 'canceled'],
            'delivered': ['return_requested'],
            'canceled': [],
            'return_requested': ['returned', 'return_denied'],
            'return': ['returned'],
            'returned': [],
            'return_denied': [],
        }
        return new_status in allowed_transitions.get(self.status, [])
    
    
    
    
    def get_original_unit_price(self):
        """Return the original unit price of the product."""
        if self.product.price is None:
            return Decimal('0.00')
        return Decimal(self.product.price)

    def get_discounted_unit_price(self):
        """Calculate the discounted unit price based on applicable offers."""
        product_instance = self.product
        current_date = timezone.now()

        discounted_price = Decimal(self.product.price)
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
                discounted_price = Decimal(product_instance.price) * (1 - Decimal(product_offer.discount_percentage) / 100)
            else:
                applicable_offer = category_offer
                discounted_price = Decimal(product_instance.price) * (1 - Decimal(category_offer.discount_percentage) / 100)
        elif product_offer:
            applicable_offer = product_offer
            discounted_price = Decimal(product_instance.price) * (1 - Decimal(product_offer.discount_percentage) / 100)
        elif category_offer:
            applicable_offer = category_offer
            discounted_price = Decimal(product_instance.price) * (1 - Decimal(category_offer.discount_percentage) / 100)

        return discounted_price.quantize(Decimal('0.01'))

    def get_total_original_price(self):
        """Calculate total original price (quantity * original unit price)."""
        return (self.quantity * self.get_original_unit_price()).quantize(Decimal('0.01'))

    def get_total_discounted_price(self):
        """Calculate total discounted price (quantity * discounted unit price)."""
        return (self.quantity * self.get_discounted_unit_price()).quantize(Decimal('0.01'))

    def get_savings(self):
        """Calculate savings based on the difference between original and discounted price."""
        return (self.get_total_original_price() - self.get_total_discounted_price()).quantize(Decimal('0.01'))