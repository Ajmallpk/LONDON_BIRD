
from django.shortcuts import render,redirect,get_object_or_404
from .models import product,Variant
from .forms import *
from categories.models import categories
from django.db.models import Q
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.paginator import Paginator
import base64
import uuid
from django.core.files.base import ContentFile
import re
from django.core.exceptions import ValidationError
from offer.models import ProductOffer, CategoryOffer
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from .models import product
from offer.models import ProductOffer
from datetime import datetime
from decimal import Decimal
from django.utils.timezone import make_aware
from django.views.decorators.cache import never_cache
from django.utils import timezone
from decimal import Decimal
from products.models import product, Variant, Size





def product_list(request):
    products = product.objects.all()
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(name__icontains=search_query)
    
    paginator = Paginator(products, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    
    product_offers = ProductOffer.objects.filter(product__in=products)
    product_offer_dict = {offer.product.id: offer for offer in product_offers}

    if request.method == 'POST':
        if 'add_product_offer' in request.POST:
            product_id = request.POST.get('product_id')
            offer_id = request.POST.get('offer_id', None)  
            discount_percentage = request.POST.get('discount_percentage')
            valid_from = request.POST.get('valid_from')
            valid_until = request.POST.get('valid_until')
            is_active = request.POST.get('is_active') == 'on'

            try:
                discount_percentage = Decimal(discount_percentage)
                if discount_percentage < 0 or discount_percentage > 100:
                    messages.error(request, "Discount percentage must be between 0 and 100.")
                    return render(request, 'product_list.html', {
                        'page_obj': page_obj,
                        'search_query': search_query,
                        'product_offer_dict': product_offer_dict,
                    })
                
                valid_from = make_aware(datetime.strptime(valid_from, '%Y-%m-%d'))
                valid_until = make_aware(datetime.strptime(valid_until, '%Y-%m-%d'))
                if valid_from > valid_until:
                    messages.error(request, "The 'Valid Until' date must be after the 'Valid From' date.")
                    return render(request, 'product_list.html', {
                        'page_obj': page_obj,
                        'search_query': search_query,
                        'product_offer_dict': product_offer_dict,
                    })

                if offer_id: 
                    offer = ProductOffer.objects.get(id=offer_id)
                    offer.discount_percentage = discount_percentage
                    offer.valid_from = valid_from
                    offer.valid_until = valid_until
                    offer.is_active = is_active
                    offer.save()
                    messages.success(request, f"Offer updated successfully for {offer.product.name}.")
                else:  
                    product_instance = product.objects.get(id=product_id)
                    ProductOffer.objects.create(
                        product=product_instance,
                        discount_percentage=discount_percentage,
                        valid_from=valid_from,
                        valid_until=valid_until,
                        is_active=is_active
                    )
                    messages.success(request, f"Offer added successfully for {product_instance.name}.")
            except ValueError as e:
                messages.error(request, "Invalid input. Please ensure all fields are filled correctly.")
                return render(request, 'product_list.html', {
                    'page_obj': page_obj,
                    'search_query': search_query,
                    'product_offer_dict': product_offer_dict,
                })
            except (product.DoesNotExist, ProductOffer.DoesNotExist):
                messages.error(request, "Product or offer not found.")
                return render(request, 'product_list.html', {
                    'page_obj': page_obj,
                    'search_query': search_query,
                    'product_offer_dict': product_offer_dict,
                })
            return redirect('product_list')

    return render(request, 'product_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'product_offer_dict': product_offer_dict,
    })





@never_cache
@staff_member_required
def toggle_product_status(request,product_id):
  if request.method=='POST':
    Product=get_object_or_404(product,id=product_id)
    Product.is_active= not Product.is_active
    Product.save()
  return redirect('product_list')





@never_cache
@staff_member_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST,request.FILES)
        if form.is_valid():
            form = form.save()
            messages.success(request, "Product added successfully, please add the variants")
            return redirect('product_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm()
    return render(request, 'add-products.html', {'form': form})








@never_cache
@staff_member_required
def edit_product(request, product_id):
    Product = get_object_or_404(product, id=product_id)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=Product)
        name = request.POST.get("name", "")
        
        if not re.match(r'^[A-Za-z\s]+$', name):
            custom_error_message = 'Product name must contain only letters and spaces. Numbers or special characters are not allowed.'
            return render(request, 'edit-products.html', {
                    'form': form,
                    'categories': Categories,
                    'product': Product,
                    'custom_error_message': custom_error_message
                })

        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect('product_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm(instance=Product)

    Categories = categories.objects.all()
    return render(request, 'edit-products.html', {
        'form': form,
        'categories': Categories,
        'product': Product,
       
    })








@never_cache
def product_details(request, product_id):
    
    variant = get_object_or_404(Variant, id=product_id)
    product_instance = product.objects.get(id=variant.product.id)
    variants = Variant.objects.filter(product__id=product_instance.id, is_active=True) 
    sizes = variant.sizes.all()

    
    for i in variants:
        print(f"Variant Product Name: {i.product.name}")

    
    related_products = Variant.objects.filter(
        product__category=product_instance.category,
        product__is_active=True,
        is_active=True  # Only active variants
    ).exclude(
        product=product_instance
    ).select_related('product')[:4] 

    
    print(f"Related Products: {list(related_products)}")
    for related in related_products:
        print(f"Related Product: {related.product.name}, Variant ID: {related.id}")

   
    current_date = timezone.now()
    applicable_offer = None
    original_price = product_instance.price if product_instance.price is not None else Decimal('0.00')
    discounted_price = original_price
    savings = Decimal('0.00')
    both_offers_available = False

   
    product_offer = None
    try:
        product_offer = ProductOffer.objects.get(
            product=product_instance,
            is_active=True,
            valid_from__lte=current_date,
            valid_until__gte=current_date
        )
    except ProductOffer.DoesNotExist:
        pass

    
    category_offer = None
    try:
        category_offer = CategoryOffer.objects.get(
            category=product_instance.category,
            is_active=True,
            valid_from__lte=current_date,
            valid_until__gte=current_date
        )
    except CategoryOffer.DoesNotExist:
        pass

    
    if product_offer and category_offer:
        both_offers_available = True
        if product_offer.discount_percentage >= category_offer.discount_percentage:
            applicable_offer = {
                'type': 'Product Offer',
                'discount_percentage': product_offer.discount_percentage,
                'valid_from': product_offer.valid_from,
                'valid_until': product_offer.valid_until
            }
            discounted_price = original_price * (1 - Decimal(product_offer.discount_percentage) / 100)
        else:
            applicable_offer = {
                'type': 'Category Offer',
                'discount_percentage': category_offer.discount_percentage,
                'valid_from': category_offer.valid_from,
                'valid_until': category_offer.valid_until
            }
            discounted_price = original_price * (1 - Decimal(category_offer.discount_percentage) / 100)
    elif product_offer:
        applicable_offer = {
            'type': 'Product Offer',
            'discount_percentage': product_offer.discount_percentage,
            'valid_from': product_offer.valid_from,
            'valid_until': product_offer.valid_until
        }
        discounted_price = original_price * (1 - Decimal(product_offer.discount_percentage) / 100)
    elif category_offer:
        applicable_offer = {
            'type': 'Category Offer',
            'discount_percentage': category_offer.discount_percentage,
            'valid_from': category_offer.valid_from,
            'valid_until': category_offer.valid_until
        }
        discounted_price = original_price * (1 - Decimal(category_offer.discount_percentage) / 100)

   
    if applicable_offer:
        savings = original_price - discounted_price

    context = {
        'product': variant,
        'variants': variants,
        'size': sizes,
        'applicable_offer': applicable_offer,
        'original_price': original_price,
        'discounted_price': discounted_price.quantize(Decimal('0.01')),
        'savings': savings.quantize(Decimal('0.01')),
        'both_offers_available': both_offers_available,
        'related_products': related_products,
    }
    return render(request, 'product_details.html', context)
    
    
    
@never_cache   
def variant_details(request,product_id,variant_id):
    Product = get_object_or_404(product,id=product_id)
    variant=get_object_or_404(Variant,id=variant_id,product=Product)
    
    variants = Product.variants.filter(is_active=True) 
    
    
    return render(request, 'variant_details.html', {
        'product': Product,
        'variant':variant,
        'variants': variants  
    })
    




@never_cache
def shop(request):
   
    variant_ids = (
    Variant.objects
    .filter(product__is_active=True, is_active=True)
    .order_by('product_id', 'id')
    .distinct('product_id')
    .values_list('id', flat=True)
)
    products = Variant.objects.filter(id__in=variant_ids).select_related('product')
    
    for i in products:
        print(i.product.name)


    category_id = request.GET.get('category')
    print(category_id)
    if category_id and category_id !="1":
        products = products.filter(product__category_id=category_id)

    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min and price_min.isdigit():
        products = products.filter(price__gte=price_min)
    if price_max and price_max.isdigit():
        products = products.filter(price__lte=price_max)
    
        
    sort = request.GET.get('sort', 'default')
    print(sort)
    if sort == 'price-desc':
        products = products.order_by('-product__price')
    elif sort == 'price-asc':
        products = products.order_by('product__price')
    elif sort == 'name-asc':
        products = products.order_by('product__name')
    elif sort == 'name-desc':
        products = products.order_by('-product__name')
    else:
        products = products.order_by('product__name') 

    paginator = Paginator(products, 8) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    
    Category = categories.objects.filter(is_listed=True)
    
        
    return render(request, 'shop_grid.html', {
        'products': page_obj,
       
        'categories': Category,
    })
    




@staff_member_required
@never_cache
def list_variants(request,product_id):
    selected_product = product.objects.get(id=product_id)
    variants = selected_product.variants.all()
    return render(request, 'list_variants.html', {'variants': variants})


@staff_member_required
@never_cache
def list_size(request,variant_id):
    selected_product = Variant.objects.get(id=variant_id)
    sizes = selected_product.sizes.all()
    return render(request, 'list_size.html', {'size': sizes,'product':selected_product})




 
    
@staff_member_required
@never_cache
def add_variant(request, product_id):
    selected_product = product.objects.get(id=product_id)
    variants = selected_product.variants.all()
    if request.method == 'POST':
        form = VariantForm(request.POST, request.FILES, product=selected_product)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = selected_product
            variant.save()
            return render(request, 'list_variants.html', {'variants': variants})
    else:
        form = VariantForm(product=selected_product)

    return render(request, 'add_variant.html', {'form': form})




@staff_member_required
@never_cache
def add_size(request, variant_id):
    selected_variant = get_object_or_404(Variant, id=variant_id)
    
    if request.method == 'POST':
        form = SizeForm(request.POST, variant=selected_variant)
        if form.is_valid():
            size = form.save()
            messages.success(request, 'Size added successfully!')
            return redirect('list_variants', product_id=selected_variant.product.id)
        else:
            print("Form errors:", form.errors)
            print("POST data:", request.POST)
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SizeForm(variant=selected_variant)
    return render(request, 'add_size.html', {'form': form, 'variant': selected_variant})





@staff_member_required
@never_cache
def edit_variant(request, variant_id):
    variant = get_object_or_404(Variant, id=variant_id)
    selected_product = product.objects.get(id=variant.product.id)
    variants = selected_product.variants.all()
    if request.method == 'POST':
        form = VariantForm(request.POST, request.FILES, instance=variant)
        if form.is_valid():
            
            form.save()
            messages.success(request, 'Variant updated successfully!')
            return render(request, 'list_variants.html', {'variants': variants})
        
        else:
            print(form.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        form = VariantForm(instance=variant)
    return render(request, 'edit_variant.html', {'form': form, 'variant': variant})






@staff_member_required
@never_cache
def delete_variant(request,variant_id):
    variant=get_object_or_404(Variant,id=variant_id)
    variant.delete()
    
    return redirect('list_variants',variant.product.id)






@staff_member_required
@never_cache
def list_variant(request, variant_id):
    if request.method == 'POST':
        variant = get_object_or_404(Variant, id=variant_id)
        variant.is_active = True
        variant.save()
        messages.success(request, f'Variant "{variant}" has been listed.')
        return redirect('list_variants', product_id=variant.product.id)
    return redirect('list_variants', product_id=variant.product.id)



@staff_member_required
@never_cache
def unlist_variant(request, variant_id):
    if request.method == 'POST':
        variant = get_object_or_404(Variant, id=variant_id)
        variant.is_active = False
        variant.save()
        messages.success(request, f'Variant "{variant}" has been unlisted.')
        return redirect('list_variants', product_id=variant.product.id)
    return redirect('list_variants', product_id=variant.product.id)