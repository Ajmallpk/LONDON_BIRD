import razorpay
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from cart.models import Cart  

from checkout.models import Order




@login_required
def initiate_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # # Check if the order is in a payable state
    # if order.status != 'processing':
    #     print(order.status)
    #     messages.error(request, "This order cannot be paid for at this time.")
    #     return redirect('order_detail', order_id=order.id)

    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    
    amount = int(order.total_price * 100)  

    
    razorpay_order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "receipt": f"order_{order.id}",
        "payment_capture": 1 
    })

    
    order.razorpay_order_id = razorpay_order['id']
    order.payment_method = 'Razorpay'
    order.save(update_fields=['razorpay_order_id', 'payment_method'])

    
    context = {
        'order': order,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'amount': amount,
        'currency': "INR",
        'callback_url': request.build_absolute_uri('/payments/verify/'),
        'cancel_url': request.build_absolute_uri('/payments/failure/'),
    }
    return render(request, 'payment.html', context)



@login_required
def initiate_combined_payment(request):
    order_ids = request.session.get('combined_order_ids', [])
    total_amount = request.session.get('combined_order_total', 0)

    if not order_ids or total_amount <= 0:
        messages.error(request, "Something went wrong with your order.")
        return redirect('checkout')

   
    orders = Order.objects.filter(id__in=order_ids, user=request.user)
    if not orders.exists() or orders.count() != len(order_ids):
        messages.error(request, "Invalid orders for payment.")
        return redirect('checkout')

    
    subtotal = sum(order.items.first().final_offer_price for order in orders)  
    product_discount = sum(order.product_discount_amount for order in orders)
    shipping = sum(order.shipping for order in orders)
    coupon_discount = sum(order.discount_coupon_amount for order in orders)

    
    amount_in_paise = int(total_amount * 100)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    data = {
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": f"combined_order_{request.user.id}",
        "payment_capture": 1,
    }

    razorpay_order = client.order.create(data=data)

    
    orders.update(razorpay_order_id=razorpay_order['id'])

   
    request.session['razorpay_order_id'] = razorpay_order['id']

    context = {
        "razorpay_order_id": razorpay_order['id'],
        "razorpay_merchant_key": settings.RAZORPAY_KEY_ID,
        "amount": amount_in_paise,
        "currency": "INR",
        "callback_url": request.build_absolute_uri('/payments/verify/'),
        "cancel_url": request.build_absolute_uri('/payments/failure/'),
        "total": total_amount,
        "order_ids": order_ids,
        "subtotal": subtotal,
        "product_discount": product_discount,
        "shipping": shipping,
        "coupon_discount": coupon_discount,
    }

    return render(request, 'payment.html', context)





@login_required
def verify_payment(request):
    if request.method == 'POST':
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')

        
        combined_order_ids = request.session.get('combined_order_ids', [])

        if not combined_order_ids:
            messages.error(request, "No orders found for verification.")
            return redirect('checkout')

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        try:
            
            client.utility.verify_payment_signature(params_dict)

            
            orders = Order.objects.filter(id__in=combined_order_ids, user=request.user)
            orders.update(status='processing', payment_status='Completed', razorpay_order_id=razorpay_order_id, razorpay_payment_id=razorpay_payment_id)

            
            if 'combined_order_ids' in request.session:
                del request.session['combined_order_ids']
            if 'combined_order_total' in request.session:
                del request.session['combined_order_total']
            if 'coupon_code' in request.session:
                del request.session['coupon_code']

            messages.success(request, "Payment successful! Your orders have been placed.")
           
            return redirect('payment_success', order_id=combined_order_ids[-1])

        except razorpay.errors.SignatureVerificationError:
            
            messages.error(request, "Payment verification failed. Please try again.")
            return redirect('payment_failure')

    else:
        return redirect('checkout')



@login_required
def payment_success(request, order_id=None):
   
    if order_id:
        order = get_object_or_404(Order, id=order_id, user=request.user)
       
        if order.payment_status == 'pending':
            messages.error(request, "This order is not yet paid.")
           
            return redirect('order_list')

            
        return render(request, 'order_success.html', {'order': order})
    else:
       
        messages.error(request, "Order not found.")
        return redirect('orders') 



@login_required
def payment_failure(request, order_id=None):
    if order_id:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        return render(request, 'order_failure.html', {'order': order})
    else:
        messages.error(request, "Order not found.")
        return redirect('checkout')
