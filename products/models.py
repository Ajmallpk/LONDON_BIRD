from django.db import models
from categories.models import categories
from django.db.models.signals import pre_save,post_save,post_delete
from django.dispatch import receiver



class product(models.Model):
  name=models.CharField(max_length=200)
  description=models.TextField()
  category=models.ForeignKey(categories,on_delete=models.CASCADE,null=True,blank=True,related_name="products")
  created_at=models.DateTimeField(auto_now_add=True)
  updated_at=models.DateField(auto_now=True)
  image_1=models.ImageField(upload_to='product_images/',null=True,blank=True,default=None)
  image_2=models.ImageField(upload_to='product_images/',null=True,blank=True)
  image_3=models.ImageField(upload_to='product_images/',null=True,blank=True)
  is_active=models.BooleanField(default=True)
  price=models.DecimalField(max_digits=10,decimal_places=2,default=None,null=True,blank=True)
  
  
  
def __str__(self):
  return self.name


 
@receiver(post_save, sender=categories)
def update_color_products_listing_status(sender, instance, **kwargs):
    
        product.objects.filter(category=instance).update(is_active=instance.is_listed)


  
  
  
class Variant(models.Model):
  SIZE_CHOICES= [
    ('S','Small'),
    ('M','Medium'),
    ('L','Large'),
    ('XL','Extra Large')
  ]
  product=models.ForeignKey(product,on_delete=models.CASCADE,related_name="variants")
 
 

  color=models.CharField(max_length=50)
  image_main=models.ImageField(upload_to='product_images/')
  image_1=models.ImageField(upload_to='product_images/',null=True,blank=True)
  image_2=models.ImageField(upload_to='product_images/',null=True,blank=True)
  image_3=models.ImageField(upload_to='product_images/',null=True,blank=True)
  is_active = models.BooleanField(default=True)
  

  def __str__(self):
    return f"{self.product.name}({self.color})"
  
  def get_discounted_price(self):
    """
    Calculate the discounted price for this variant based on ProductOffer or CategoryOffer.
    Returns the discounted price if an offer is applicable, otherwise returns the original price.
    """
    from django.utils import timezone
    from decimal import Decimal
    from offer.models import ProductOffer, CategoryOffer 

    current_date = timezone.now()
    original_price = self.product.price if self.product.price is not None else Decimal('0.00')

  
    product_offer = None
    try:
        product_offer = ProductOffer.objects.get(
            product=self.product,
            is_active=True,
            valid_from__lte=current_date,
            valid_until__gte=current_date
        )
    except ProductOffer.DoesNotExist:
        pass

    
    category_offer = None
    try:
        category_offer = CategoryOffer.objects.get(
            category=self.product.category,
            is_active=True,
            valid_from__lte=current_date,
            valid_until__gte=current_date
        )
    except CategoryOffer.DoesNotExist:
        pass

    
    discounted_price = original_price
    if product_offer and category_offer:
        if product_offer.discount_percentage >= category_offer.discount_percentage:
            discounted_price = original_price * (1 - Decimal(product_offer.discount_percentage) / 100)
        else:
            discounted_price = original_price * (1 - Decimal(category_offer.discount_percentage) / 100)
    elif product_offer:
        discounted_price = original_price * (1 - Decimal(product_offer.discount_percentage) / 100)
    elif category_offer:
        discounted_price = original_price * (1 - Decimal(category_offer.discount_percentage) / 100)

    return discounted_price.quantize(Decimal('0.01'))

  
  
  
  
class Size(models.Model):
  size = models.CharField(max_length=15)
  stock = models.BigIntegerField(default=0)
  variant = models.ForeignKey(Variant, related_name="sizes", on_delete=models.CASCADE)


  def __str__(self):
        return self.size
      
      
@receiver(post_save, sender=categories)
def update_color_products_and_variants_listing_status(sender, instance, **kwargs):
    # Update products
    products = product.objects.filter(category=instance)
    products.update(is_active=instance.is_listed)
    # Update variants based on category listing status
    Variant.objects.filter(product__category=instance).update(is_active=instance.is_listed)