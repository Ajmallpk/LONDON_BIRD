from django.shortcuts import render
from categories.models import categories
from products.models import product,Variant



def home(request):
    
    new_arrivals = product.objects.filter(is_active=True).prefetch_related('variants').order_by('-created_at')[:4]  
    Categories = categories.objects.filter(is_listed=True) 
    products = (
        Variant.objects.filter(product__is_active=True)
        .select_related("product")
        .order_by('-product__id')
        .distinct('product__id')
    )
    
    Product_variants = []
    for Product in new_arrivals:
        default_variant = Product.variants.all().first() 
        Product_variants.append((product, default_variant))
    
    return render(request, 'index.html', {
        'products': products,  
        'categories': Categories,
    })
    