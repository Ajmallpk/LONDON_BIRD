from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from .models import Order, OrderItem, ShippingAddress
from cart.models import Cart, CartItem
from userprofile.models import Address
from wallet.models import Wallet, WalletTransaction
from coupon.models import Coupon, CouponUsage
from django.utils.timezone import now
from django.http import JsonResponse

# In checkout/views.py

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()
    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect('cart')
    
    out_of_stock_items = [item for item in cart_items if item.size and item.size.stock < item.quantity]
    if out_of_stock_items:
        for item in out_of_stock_items:
            messages.error(request, f"{item.variant.product.name} (Size: {item.size.size}) is out of stock or has insufficient stock (Available: {item.size.stock}).")
        return redirect('cart')

    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    subtotal_original = sum(item.get_total_original_price() for item in cart_items)
    subtotal_discounted = sum(item.get_total_discounted_price() for item in cart_items)
    total_savings = subtotal_original - subtotal_discounted
    shipping = Decimal('40.00') if subtotal_discounted < 1000 else Decimal('0.00')
    coupon_discount = Decimal('0.00')
    coupon = None

    if 'coupon_code' in request.session:
        try:
            coupon = Coupon.objects.get(code=request.session['coupon_code'])
            current_time = now()
            if coupon.is_active and coupon.valid_from <= current_time <= coupon.valid_until:
                user_usage = CouponUsage.objects.filter(
                    coupon=coupon,
                    order__user=request.user,
                    order__status__in=['pending', 'processing', 'shipped', 'delivered']
                ).exists()
                if user_usage:
                    messages.error(request, "You have already used this coupon.")
                    del request.session['coupon_code']
                    coupon = None
                else:
                    if subtotal_discounted >= coupon.min_purchase:
                        if coupon.discount_type == 'Fixed':
                            coupon_discount = coupon.discount_amount
                        else:
                            coupon_discount = (coupon.discount_amount * subtotal_discounted) / Decimal('100')
                            if coupon.max_discount and coupon_discount > coupon.max_discount:
                                coupon_discount = coupon.max_discount
                    else:
                        messages.error(request, f"This coupon requires a minimum purchase of ₹{coupon.min_purchase}.")
                        del request.session['coupon_code']
                        coupon = None
            else:
                messages.error(request, "Coupon is not active or has expired.")
                del request.session['coupon_code']
                coupon = None
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
            del request.session['coupon_code']
            coupon = None

    final_total = subtotal_discounted + shipping - coupon_discount
    wallet, created = Wallet.objects.get_or_create(user=request.user)

    current_time = now()
    coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=current_time,
        valid_until__gte=current_time,
    )

    used_coupon_ids = CouponUsage.objects.filter(
        order__user=request.user,
        order__status__in=['pending', 'processing', 'shipped', 'delivered']
    ).values_list('coupon_id', flat=True)

    if request.method == 'POST':
        def validate_address_fields(name, street_address, city, state, country, postal_code, phone):
            required_fields = {
                'Name': name,
                'Street Address': street_address,
                'City': city,
                'State': state,
                'Country': country,
                'Postal Code': postal_code,
                'Phone': phone,
            }
            missing_fields = [field for field, value in required_fields.items() if not value]
            if missing_fields:
                return False, f"Please fill in all required fields: {', '.join(missing_fields)}"
            
            if not phone.isdigit() or len(phone) < 10:
                return False, "Phone number must be at least 10 digits."
            
            if not postal_code.isdigit() or len(postal_code) < 5:
                return False, "Postal code must be at least 5 digits."
            
            return True, None

        if 'add_new_address' in request.POST:
            name = request.POST.get('name')
            street_address = request.POST.get('street_address')
            city = request.POST.get('city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            postal_code = request.POST.get('postal_code')
            phone = request.POST.get('phone')

            is_valid, error_message = validate_address_fields(name, street_address, city, state, country, postal_code, phone)
            if not is_valid:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': error_message
                    }, status=400)
                else:
                    messages.error(request, error_message)
                    context = {
                        'cart_items': cart_items,
                        'subtotal_original': subtotal_original,
                        'subtotal_discounted': subtotal_discounted,
                        'total_savings': total_savings,
                        'shipping': shipping,
                        'coupon_discount': coupon_discount,
                        'final_total': final_total,
                        'addresses': addresses,
                        'default_address': default_address,
                        'coupon': coupon,
                        'wallet_balance': wallet.balance,
                        'allow_cod': final_total <= Decimal('1000.00'),
                        'coupons': coupons,
                        'used_coupon_ids': list(used_coupon_ids),
                        'new_address_data': request.POST,
                    }
                    return render(request, 'checkout.html', context)

            # Unset any existing default address
            Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

            # Create and set the new address as default
            new_address = Address(
                user=request.user,
                name=name,
                street_address=street_address,
                city=city,
                state=state,
                country=country,
                postal_code=postal_code,
                phone=phone,
                is_default=True  # Set as default
            )
            new_address.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': "New address added successfully and set as default!",
                    'address': {
                        'id': new_address.id,
                        'name': new_address.name,
                        'street_address': new_address.street_address,
                        'city': new_address.city,
                        'state': new_address.state,
                        'postal_code': new_address.postal_code,
                        'country': new_address.country,
                        'phone': new_address.phone,
                        'is_default': new_address.is_default,
                    }
                })
            else:
                messages.success(request, "New address added successfully and set as default!")
                addresses = Address.objects.filter(user=request.user)
                default_address = new_address  # Since we set it as default
                selected_address_id = new_address.id
                context = {
                    'cart_items': cart_items,
                    'subtotal_original': subtotal_original,
                    'subtotal_discounted': subtotal_discounted,
                    'total_savings': total_savings,
                    'shipping': shipping,
                    'coupon_discount': coupon_discount,
                    'final_total': final_total,
                    'addresses': addresses,
                    'default_address': default_address,
                    'coupon': coupon,
                    'wallet_balance': wallet.balance,
                    'allow_cod': final_total <= Decimal('1000.00'),
                    'coupons': coupons,
                    'used_coupon_ids': list(used_coupon_ids),
                    'selected_address_id': selected_address_id,
                }
                return render(request, 'checkout.html', context)

        elif 'edit_address' in request.POST:
            address_id = request.POST.get('address_id')
            if not address_id:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': "Address ID is required."
                    }, status=400)
                else:
                    messages.error(request, "Address ID is required.")
                    context = {
                        'cart_items': cart_items,
                        'subtotal_original': subtotal_original,
                        'subtotal_discounted': subtotal_discounted,
                        'total_savings': total_savings,
                        'shipping': shipping,
                        'coupon_discount': coupon_discount,
                        'final_total': final_total,
                        'addresses': addresses,
                        'default_address': default_address,
                        'coupon': coupon,
                        'wallet_balance': wallet.balance,
                        'allow_cod': final_total <= Decimal('1000.00'),
                        'coupons': coupons,
                        'used_coupon_ids': list(used_coupon_ids),
                        'edit_address_data': request.POST,
                    }
                    return render(request, 'checkout.html', context)

            try:
                address = Address.objects.get(id=address_id, user=request.user)
            except Address.DoesNotExist:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': "Address not found."
                    }, status=404)
                else:
                    messages.error(request, "Address not found.")
                    context = {
                        'cart_items': cart_items,
                        'subtotal_original': subtotal_original,
                        'subtotal_discounted': subtotal_discounted,
                        'total_savings': total_savings,
                        'shipping': shipping,
                        'coupon_discount': coupon_discount,
                        'final_total': final_total,
                        'addresses': addresses,
                        'default_address': default_address,
                        'coupon': coupon,
                        'wallet_balance': wallet.balance,
                        'allow_cod': final_total <= Decimal('1000.00'),
                        'coupons': coupons,
                        'used_coupon_ids': list(used_coupon_ids),
                        'edit_address_data': request.POST,
                    }
                    return render(request, 'checkout.html', context)

            name = request.POST.get('name')
            street_address = request.POST.get('street_address')
            city = request.POST.get('city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            postal_code = request.POST.get('postal_code')
            phone = request.POST.get('phone')

            is_valid, error_message = validate_address_fields(name, street_address, city, state, country, postal_code, phone)
            if not is_valid:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': error_message
                    }, status=400)
                else:
                    messages.error(request, error_message)
                    context = {
                        'cart_items': cart_items,
                        'subtotal_original': subtotal_original,
                        'subtotal_discounted': subtotal_discounted,
                        'total_savings': total_savings,
                        'shipping': shipping,
                        'coupon_discount': coupon_discount,
                        'final_total': final_total,
                        'addresses': addresses,
                        'default_address': default_address,
                        'coupon': coupon,
                        'wallet_balance': wallet.balance,
                        'allow_cod': final_total <= Decimal('1000.00'),
                        'coupons': coupons,
                        'used_coupon_ids': list(used_coupon_ids),
                        'edit_address_data': request.POST,
                    }
                    return render(request, 'checkout.html', context)

            address.name = name
            address.street_address = street_address
            address.city = city
            address.state = state
            address.country = country
            address.postal_code = postal_code
            address.phone = phone
            address.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': "Address updated successfully!",
                    'address': {
                        'id': address.id,
                        'name': address.name,
                        'street_address': address.street_address,
                        'city': address.city,
                        'state': address.state,
                        'postal_code': address.postal_code,
                        'country': address.country,
                        'phone': address.phone,
                        'is_default': address.is_default,
                    }
                })
            else:
                messages.success(request, "Address updated successfully!")
                addresses = Address.objects.filter(user=request.user)
                default_address = addresses.filter(is_default=True).first()
                selected_address_id = address.id
                context = {
                    'cart_items': cart_items,
                    'subtotal_original': subtotal_original,
                    'subtotal_discounted': subtotal_discounted,
                    'total_savings': total_savings,
                    'shipping': shipping,
                    'coupon_discount': coupon_discount,
                    'final_total': final_total,
                    'addresses': addresses,
                    'default_address': default_address,
                    'coupon': coupon,
                    'wallet_balance': wallet.balance,
                    'allow_cod': final_total <= Decimal('1000.00'),
                    'coupons': coupons,
                    'used_coupon_ids': list(used_coupon_ids),
                    'selected_address_id': selected_address_id,
                }
                return render(request, 'checkout.html', context)

        # Add a new endpoint to fetch addresses for the dropdown refresh
        elif 'fetch_addresses' in request.POST and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            addresses = Address.objects.filter(user=request.user)
            address_list = [
                {
                    'id': address.id,
                    'name': address.name,
                    'street_address': address.street_address,
                    'city': address.city,
                    'state': address.state,
                    'postal_code': address.postal_code,
                    'country': address.country,
                    'phone': address.phone,
                    'is_default': address.is_default,
                }
                for address in addresses
            ]
            return JsonResponse({
                'success': True,
                'addresses': address_list
            })

    context = {
        'cart_items': cart_items,
        'subtotal_original': subtotal_original,
        'subtotal_discounted': subtotal_discounted,
        'total_savings': total_savings,
        'shipping': shipping,
        'coupon_discount': coupon_discount,
        'final_total': final_total,
        'addresses': addresses,
        'default_address': default_address,
        'coupon': coupon,
        'wallet_balance': wallet.balance,
        'allow_cod': final_total <= Decimal('1000.00'),
        'coupons': coupons,
        'used_coupon_ids': list(used_coupon_ids),
    }

    return render(request, 'checkout.html', context)



@login_required
def apply_coupon(request):
    if request.method != 'POST':
        return redirect('checkout')

    coupon_code = request.POST.get('coupon_code')
    if not coupon_code:
        messages.error(request, "Please enter a coupon code.")
        return redirect('checkout')

    try:
        coupon = Coupon.objects.get(code=coupon_code)
        current_time = now()

        # Check if coupon is active and within validity period
        if not coupon.is_active:
            messages.error(request, "This coupon is not active.")
            return redirect('checkout')
        if coupon.valid_from > current_time or coupon.valid_until < current_time:
            messages.error(request, "This coupon has expired.")
            return redirect('checkout')

        # Check usage limit per coupon (global usage)
        # if coupon.get_usage_count() >= 1:  # Since usage_limit is hardcoded to 1
        #     messages.error(request, "Coupon usage limit reached.")
        #     return redirect('checkout')

        # Check if user has already used this coupon
        user_usage = CouponUsage.objects.filter(
            coupon=coupon,
            order__user=request.user,
            order__status__in=['pending', 'processing', 'shipped', 'delivered']
        ).exists()
        if user_usage:
            messages.error(request, "You have already used this coupon.")
            return redirect('checkout')

        # Validate minimum purchase amount
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.all()
        if not cart_items:
            messages.error(request, "Your cart is empty.")
            return redirect('cart')

        subtotal_discounted = sum(item.get_total_discounted_price() for item in cart_items)
        if subtotal_discounted < coupon.min_purchase:
            messages.error(request, f"This coupon requires a minimum purchase of ₹{coupon.min_purchase}.")
            return redirect('checkout')

        # If all validations pass, apply the coupon
        request.session['coupon_code'] = coupon_code
        messages.success(request, f"Coupon '{coupon_code}' applied successfully!")

    except Coupon.DoesNotExist:
        messages.error(request, "Invalid coupon code.")

    return redirect('checkout')

@login_required
def remove_coupon(request):
    if 'coupon_code' in request.session:
        coupon_code = request.session['coupon_code']
        del request.session['coupon_code']
        messages.success(request, f"Coupon '{coupon_code}' removed successfully!")
    return redirect('checkout')




@login_required
@transaction.atomic
def place_order(request):
    if request.method != 'POST':
        return redirect('checkout')

    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()
    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect('cart')

    
    for item in cart_items:
        if item.size and item.quantity > item.size.stock:
            messages.error(request, f"Not enough stock for {item.variant.product.name} (Size: {item.size.size}).")
            return redirect('cart')

    address_id = request.POST.get('shipping_address')
    payment_method = request.POST.get('payment_method')

    if not address_id:
        messages.error(request, "Please select an address.")
        return redirect('checkout')

    try:
        address = Address.objects.get(id=address_id, user=request.user)
    except Address.DoesNotExist:
        messages.error(request, "Invalid address selected.")
        return redirect('checkout')

    shipping_address = ShippingAddress.objects.create(
        user=request.user,
        name=address.name,
        address=address.street_address,
        city=address.city,
        state=address.state,
        country=address.country,
        postcode=address.postal_code,
        phone=address.phone
    )

   
    subtotal_original = sum(item.get_total_original_price() for item in cart_items)
    subtotal_discounted = sum(item.get_total_discounted_price() for item in cart_items)
    product_discount_amount = subtotal_original - subtotal_discounted 
    shipping = Decimal('40.00') if subtotal_discounted < 1000 else Decimal('0.00')
    coupon_discount = Decimal('0.00')
    discount_applied = False
    coupon = None

    
    if 'coupon_code' in request.session:
        try:
            coupon = Coupon.objects.get(code=request.session['coupon_code'])
            current_time = now()
            if not coupon.is_active or coupon.valid_from > current_time or coupon.valid_until < current_time:
                messages.error(request, "Coupon is not active or expired.")
                return redirect('checkout')
            # if coupon.usage_limit is not None and coupon.get_usage_count() >= coupon.usage_limit:
            #     messages.error(request, "Coupon usage limit reached.")
            #     return redirect('checkout')
            if subtotal_discounted < coupon.min_purchase:
                messages.error(request, f"This coupon requires a minimum purchase of ₹{coupon.min_purchase}.")
                return redirect('checkout')

            if coupon.discount_type == 'Fixed':
                coupon_discount = coupon.discount_amount
            else:
                coupon_discount = (coupon.discount_amount * subtotal_discounted) / Decimal('100')
                if coupon.max_discount and coupon_discount > coupon.max_discount:
                    coupon_discount = coupon.max_discount

            discount_applied = True
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
            return redirect('checkout')

   
    final_total = subtotal_discounted + shipping - coupon_discount

    
    created_order_ids = []
    wallet, created = Wallet.objects.get_or_create(user=request.user)

    
    if payment_method == "Cash on Delivery":
        order_status = 'pending'
        order_item_status = 'order_placed'
        payment_status = 'Pending'
    elif payment_method == "Razorpay":
        order_status = 'processing'
        order_item_status = 'processing'
        payment_status = 'Pending'
    elif payment_method == "Wallet":
        order_status = 'processing'
        order_item_status = 'processing'
        payment_status = 'Completed'
    else:
        messages.error(request, "Invalid payment method.")
        return redirect('checkout')

    
    if payment_method == "Cash on Delivery" and final_total > Decimal('1000.00'):
        messages.error(request, "Cash on Delivery is not available for orders above ₹1000.")
        return redirect('checkout')

    
    for i, item in enumerate(cart_items):
        item_total_original = item.get_total_original_price()
        item_total_discounted = item.get_total_discounted_price()

        
        if subtotal_discounted > 0:
            item_ratio = item_total_discounted / subtotal_discounted
        else:
            item_ratio = Decimal('0.00')

        
        item_shipping = (shipping * item_ratio).quantize(Decimal('0.01'))
        item_coupon_discount = (coupon_discount * item_ratio).quantize(Decimal('0.01'))
        item_product_discount = ((item_total_original - item_total_discounted) * item_ratio).quantize(Decimal('0.01')) if subtotal_discounted > 0 else (item_total_original - item_total_discounted)

        
        if i == len(cart_items) - 1:
            item_shipping = shipping - sum(Order.objects.get(id=order_id).shipping for order_id in created_order_ids)
            item_coupon_discount = coupon_discount - sum(Order.objects.get(id=order_id).discount_coupon_amount for order_id in created_order_ids)
            item_product_discount = product_discount_amount - sum(Order.objects.get(id=order_id).product_discount_amount for order_id in created_order_ids)

        
        item_final_total = (item_total_discounted + item_shipping - item_coupon_discount).quantize(Decimal('0.01'))

        
        if payment_method == "Wallet":
            if wallet.balance < item_final_total:
                messages.error(request, f"Insufficient wallet balance for item {item.variant.product.name}.")
                return redirect('checkout')

        
        order = Order.objects.create(
            user=request.user,
            shipping_address=shipping_address,
            payment_method=payment_method,
            total_price=item_final_total,
            status=order_status,
            payment_status=payment_status,
            discount_applied=discount_applied,
            discount_coupon_amount=item_coupon_discount,
            product_discount_amount=item_product_discount,
            shipping=item_shipping,
        )

        
        if coupon:
            CouponUsage.objects.create(
                coupon=coupon,
                order=order,
            )

        
        OrderItem.objects.create(
            order=order,
            product=item.variant.product,
            product_variant=item.variant,
            size=item.size,
            quantity=item.quantity,
            price=item_total_original,
            status=order_item_status,
            final_offer_price=item_total_discounted,
        )

        
        if item.size and item.quantity > 0:
            if item.size.stock < item.quantity:
                order.delete()
                messages.error(request, f"Not enough stock for {item.variant.product.name} (Size: {item.size.size}).")
                return redirect('cart')
            item.size.stock -= item.quantity
            item.size.save()

        
        if payment_method == "Wallet":
            wallet.balance -= item_final_total
            wallet.save()
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='DEBIT',
                amount=item_final_total,
                description=f'Payment for Order #{order.id}'
            )

        created_order_ids.append(order.id)

   
    cart.items.all().delete()

    
    if payment_method == 'Razorpay':
        total_amount = sum(Order.objects.get(id=order_id).total_price for order_id in created_order_ids)
        request.session['combined_order_ids'] = created_order_ids
        print("Combined Order IDs:", request.session.get('combined_order_ids'))
        request.session['combined_order_total'] = float(total_amount)
        return redirect('initiate_combined_payment')
    else:
        
        if 'coupon_code' in request.session:
            del request.session['coupon_code']
        messages.success(request, "All orders placed successfully!")
        return redirect('order_success', order_id=created_order_ids[-1])

    return redirect('checkout')



@login_required
def order_success(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('index')

    context = {'order': order}
    return render(request, 'order_success.html', context)