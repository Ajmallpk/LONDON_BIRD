from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import Variant, Size, Cart, CartItem
from django.db.models import Q
import json
import logging

logger = logging.getLogger(__name__)

@login_required
def add_to_cart(request, variant_id):
    logger.debug(f"Adding to cart: variant_id={variant_id}, user={request.user.username}")
    variant = get_object_or_404(Variant, id=variant_id)
    size_id = request.POST.get('size_id')
    logger.debug(f"Received size_id={size_id}")

    if not size_id:
        logger.error("No size_id provided in request.")
        messages.error(request, "Please select a size.")
        return redirect('product_details', product_id=variant.product.id)

    try:
        size = get_object_or_404(Size, id=size_id)
    except Exception as e:
        logger.error(f"Invalid size_id: {size_id}, error: {str(e)}")
        messages.error(request, "Invalid size selected.")
        return redirect('product_details', product_id=variant.product.id)

    if size.stock < 1:
        logger.warning(f"Out of stock: size={size.size}, stock={size.stock}")
        messages.error(request, "This product is out of stock.")
        return redirect('product_details', product_id=variant.product.id)

    cart, created = Cart.objects.get_or_create(user=request.user)
    logger.debug(f"Cart {'created' if created else 'retrieved'} for user={request.user.username}")

    cart_item = CartItem.objects.filter(cart=cart, variant=variant, size=size).first()
    if cart_item:
        if cart_item.quantity + 1 > size.stock:
            logger.warning(f"Stock limit exceeded: item_quantity={cart_item.quantity}, stock={size.stock}")
            messages.error(request, "Cannot add more items than available in stock.")
            return redirect('product_details', product_id=variant.product.id)
        if cart_item.quantity + 1 > 10:
            logger.warning(f"Max quantity limit reached: item_quantity={cart_item.quantity}")
            messages.error(request, "Maximum quantity limit reached for this product.")
            return redirect('product_details', product_id=variant.product.id)
        cart_item.quantity += 1
        cart_item.save()
        logger.debug(f"Updated cart item: quantity={cart_item.quantity}")
    else:
        if 1 > size.stock:
            logger.warning(f"Cannot add item: stock={size.stock}")
            messages.error(request, "Cannot add more items than available in stock.")
            return redirect('product_details', product_id=variant.product.id)
        cart_item = CartItem.objects.create(cart=cart, variant=variant, size=size, quantity=1)
        logger.debug(f"Created new cart item: variant={variant.id}, size={size.size}")

    messages.success(request, "Product added to cart successfully!")
    logger.info(f"Product added to cart: variant={variant.id}, size={size.size}, user={request.user.username}")
    return redirect('cart')




@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all().filter(variant__product__is_active=True)
    
    
    total_original = sum(item.get_total_original_price() for item in cart_items)
    total_discounted = sum(item.get_total_discounted_price() for item in cart_items)
    total_savings = total_original - total_discounted

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total_original': total_original,
        'total_discounted': total_discounted,
        'total_savings': total_savings,
    })

@login_required
def update_cart_quantity(request, item_id):
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        logger.debug(f"Found cart item: id={item_id}, user={request.user.username}")

        try:
            data = json.loads(request.body)
            action = data.get('action')
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body")
            return JsonResponse({'success': False, 'message': 'Invalid request data.'})

        logger.debug(f"Received action: {action}")

        if action == 'increment':
            if cart_item.quantity + 1 > cart_item.size.stock:
                logger.warning(f"Stock limit reached: quantity={cart_item.quantity}, stock={cart_item.size.stock}")
                return JsonResponse({'success': False, 'message': 'Cannot add more items than available in stock.'})
            if cart_item.quantity + 1 > 10:
                logger.warning(f"Max quantity limit reached: quantity={cart_item.quantity}")
                return JsonResponse({'success': False, 'message': 'Maximum quantity limit reached.'})
            cart_item.quantity += 1
        elif action == 'decrement':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
            else:
                cart_item.delete()
                logger.debug(f"Item removed: id={item_id}")
                return JsonResponse({'success': True, 'message': 'Item removed from cart.'})
        else:
            logger.error(f"Invalid action: {action}")
            return JsonResponse({'success': False, 'message': 'Invalid action.'})

        cart_item.save()
        logger.debug(f"Saved cart item: quantity={cart_item.quantity}")

        try:
            cart_items = cart_item.cart.items.all()
            total_original = sum(item.get_total_original_price() for item in cart_items)
            total_discounted = sum(item.get_total_discounted_price() for item in cart_items)
        except Exception as e:
            logger.error(f"Error calculating totals: {str(e)}")
            return JsonResponse({'success': False, 'message': 'Error calculating cart total.'})

        logger.debug(f"Returning response: quantity={cart_item.quantity}, item_total={cart_item.get_total_discounted_price()}, cart_total={total_discounted}")

        return JsonResponse({
            'success': True,
            'quantity': cart_item.quantity,
            'item_total': float(cart_item.get_total_discounted_price()),
            'item_original_total': float(cart_item.get_total_original_price()),
            'cart_total_original': float(total_original),
            'cart_total_discounted': float(total_discounted),
            'savings': float(total_original - total_discounted),
        })

    except Exception as e:
        logger.error(f"Unexpected error in update_cart_quantity: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': 'An unexpected error occurred.'}, status=500)

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Product removed from cart.")
    return redirect('cart')

@login_required
def clear_cart(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart.items.all().delete()
    messages.success(request, "Cart cleared successfully.")
    return redirect('cart')