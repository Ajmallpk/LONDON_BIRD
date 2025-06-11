### Updated (Adjusted redirect parameter)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from .models import Wishlist
from products.models import Variant, Size
from cart.models import Cart, CartItem
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@login_required
def view_wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items_count = cart.items.count()
    context = {
        'wishlist_items': wishlist_items,
        'cart_items': cart_items_count,
    }
    return render(request, 'wishlist.html', context)




@login_required
def add_to_wishlist(request, variant_id):
    if request.method == 'POST':
        logger.debug(f"Attempting to add variant with ID {variant_id} to wishlist")
        try:
            variant = get_object_or_404(Variant, id=variant_id)
            logger.debug(f"Found variant: {variant.product.name} ({variant.color})")
        except Exception as e:
            logger.error(f"Variant with ID {variant_id} not found: {str(e)}")
            raise

        size_id = request.POST.get('size_id')
        print(size_id)
        logger.debug(f"Received size_id: {size_id}")
        if size_id:
            size = get_object_or_404(Size, id=size_id, variant=variant)
        else:
            size = None

        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            variant=variant,
            size=size,
            
        )

        if created:
            messages.success(request, f"{variant.product.name} ({variant.color}) has been added to your wishlist.")
        else:
            messages.info(request, f"{variant.product.name} ({variant.color}) is already in your wishlist.")

        return redirect('view_wishlist')  
    return redirect('index')




@login_required
def remove_from_wishlist(request, wishlist_id):
    wishlist_item = get_object_or_404(Wishlist, id=wishlist_id, user=request.user)
    product_name = wishlist_item.variant.product.name
    wishlist_item.delete()
    messages.success(request, f"{product_name} has been removed from your wishlist.")
    return redirect('view_wishlist')



@login_required
def move_to_cart(request, wishlist_id):
    wishlist_item = get_object_or_404(Wishlist, id=wishlist_id, user=request.user)

    if not wishlist_item.variant.product.is_active or not wishlist_item.variant.product.category.is_listed:
        messages.error(request, "This product is not available.")
        wishlist_item.delete()
        return redirect('view_wishlist')

    if wishlist_item.size and wishlist_item.size.stock < 1:
        messages.error(request, "This product is out of stock.")
        return redirect('view_wishlist')

    cart, created = Cart.objects.get_or_create(user=request.user)

    cart_item = CartItem.objects.filter(
        cart=cart,
        variant=wishlist_item.variant,
        size=wishlist_item.size
    ).first()

    if cart_item:
        if cart_item.quantity + 1 > wishlist_item.size.stock:
            messages.error(request, "Cannot add more items than available in stock.")
            return redirect('view_wishlist')
        if cart_item.quantity + 1 > 10:
            messages.error(request, "Maximum quantity limit reached for this product.")
            return redirect('view_wishlist')
        cart_item.quantity += 1
        cart_item.save()
    else:
        cart_item = CartItem.objects.create(
            cart=cart,
            variant=wishlist_item.variant,
            size=wishlist_item.size,
            quantity=1
        )

    wishlist_item.delete()
    messages.success(request, f"{wishlist_item.variant.product.name} has been moved to your cart.")
    return redirect('view_wishlist')




@login_required
def get_wishlist_count(request):
    count = Wishlist.objects.filter(user=request.user).count()
    return HttpResponse(count)
