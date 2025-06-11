from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from checkout.models import Order, OrderItem, ShippingAddress
from django.urls import reverse
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os
import logging
from django.contrib import messages
from django.utils import timezone
from wallet.models import Wallet, WalletTransaction
import razorpay
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from decimal import Decimal


def is_admin(user):
    return user.is_authenticated and user.is_superuser


logger = logging.getLogger(__name__)
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def order_list(request):
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', '-created_at')
    status = request.GET.get('status', '')
    
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    
    if query:
        orders = orders.filter(
            Q(id__icontains=query) |
            Q(payment_method__icontains=query) |
            Q(items__product__name__icontains=query)
        ).distinct()
    
    if status:
        orders = orders.filter(status=status)
    
    orders = orders.order_by(sort)
    for order in orders:
        order.payment_type = order.payment_method
    
    context = {
        'orders': orders,
        'query': query,
        'sort': sort,
        'status': status,
        'status_choices': Order.ORDER_STATUS_CHOICES,
    }
    return render(request, 'order_list.html', context)







@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.all()
    
    status_colors = {
        'order_placed': '#6c757d',
        'processing': '#17a2b8',
        'shipped': '#007bff',
        'out_for_delivery': '#ffc107',
        'delivered': '#28a745',
        'canceled': '#dc3545',
        'return_requested': '#ff851b',
        'returned': '#6f42c1',
        'return_denied': '#343a40',
    }
    
    can_cancel_order = order.status in ['processing', 'pending']
    
    for item in order_items:
        item.status_color = status_colors.get(item.status, '#6c757d')
        item.can_be_canceled = item.can_update_status('canceled')
        item.can_be_returned = item.status == 'delivered'
    
    context = {
        'order': order,
        'order_items': order_items,
        'can_cancel_order': can_cancel_order,
    }
    return render(request, 'order_detail.html', context)








@login_required
def update_shipping_address(request, order_id):
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method'
        }, status=405)

    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status not in ['order_placed', 'processing']:
        return JsonResponse({
            'success': False,
            'message': 'Cannot change address for this order status'
        }, status=400)

    try:
        logger.debug(f"Request body: {request.body}")
        data = json.loads(request.body)
        address_id = data.get('address_id')
        
        if not address_id:
            return JsonResponse({
                'success': False,
                'message': 'No address selected'
            }, status=400)
        
        new_address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
        order.shipping_address = new_address
        order.updated_at = datetime.now()
        order.save()
        
        logger.info(f"Updated shipping address for order {order_id} to address {address_id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Shipping address updated successfully',
            'redirect_url': reverse('orders:order_detail', args=[order_id])
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Invalid request data: JSON decode error'
        }, status=400)
    except ShippingAddress.DoesNotExist:
        logger.error(f"Address with ID {address_id} not found for user {request.user.id}")
        return JsonResponse({
            'success': False,
            'message': 'Selected address not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in update_shipping_address: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'An unexpected error occurred: {str(e)}'
        }, status=500)







@login_required
def cancel_order(request, order_id):
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method'
        }, status=405)

    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.all()

    try:
        data = json.loads(request.body)
        cancel_reason = data.get('reason', '')

        if not order.can_be_canceled:
            return JsonResponse({
                'success': False,
                'message': 'Order cannot be canceled in its current status'
            }, status=400)

        if order.is_refunded:
            return JsonResponse({
                'success': False,
                'message': 'This order has already been refunded'
            }, status=400)

        
        for item in order_items:
            if item.status not in ['canceled', 'returned', 'return_denied'] and item.size and item.quantity > 0:
                item.size.stock += item.quantity
                item.size.save()

            item.status = 'canceled'
            item.cancel_reason = cancel_reason
            item.updated_at = datetime.now()
            item.save()

        
        order.update_order()

        
        wallet = Wallet.objects.get(user=request.user)  

        refund_amount = order.total_price

        if order.payment_method == 'Razorpay' and order.payment_status == 'Completed':
            
            try:
                payment_id = razorpay_client.order.fetch(order.razorpay_order_id)['payments'][0]['payment_id']
                razorpay_client.payment.refund(payment_id, {
                    "amount": int(refund_amount * 100),
                    "speed": "normal",
                    "notes": {"reason": f"Order {order.id} canceled by user"}
                })
                wallet.balance += refund_amount
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='CREDIT',
                    amount=refund_amount,
                    description=f"Refund for canceled order #{order.id} (Razorpay)"
                )
            except Exception as e:
                logger.error(f"Razorpay refund failed for order {order.id}: {str(e)}")
                wallet.balance += refund_amount
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='CREDIT',
                    amount=refund_amount,
                    description=f"Refund for canceled order #{order.id} (Razorpay refund failed)"
                )
        else:
            
            wallet.balance += refund_amount
            wallet.save()
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='CREDIT',
                amount=refund_amount,
                description=f"Refund for canceled order #{order.id}"
            )

        
        order.is_refunded = True
        order.balance_refunded = refund_amount
        order.save()

        return JsonResponse({
            'success': True,
            'message': f'Order canceled successfully. ₹{refund_amount} has been refunded to your wallet.',
            'redirect_url': reverse('orders:order_list')
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid request data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error canceling order {order_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)






@login_required
def cancel_reason(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status not in ['processing', 'pending']:
        messages.error(request, "Order cannot be canceled in its current status.")
        return redirect('orders:order_detail', order_id=order_id)
    
    if order.is_refunded:
        messages.error(request, "This order has already been refunded.")
        return redirect('orders:order_detail', order_id=order_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a reason for cancellation.")
            return render(request, 'cancel_reason.html', {'order': order})
        
        order_items = order.items.all()
        
        for item in order_items:
            if item.status not in ['canceled', 'returned', 'return_denied'] and item.size and item.quantity > 0:
                item.size.stock += item.quantity
                item.size.save()

            item.status = 'canceled'
            item.cancel_reason = reason
            item.updated_at = datetime.now()
            item.save()

        order.update_order()

       
        wallet = Wallet.objects.get(user=request.user)  

        refund_amount = order.total_price

        if order.payment_method == 'Razorpay' and order.payment_status == 'Completed':
            try:
                payment_id = razorpay_client.order.fetch(order.razorpay_order_id)['payments'][0]['payment_id']
                razorpay_client.payment.refund(payment_id, {
                    "amount": int(refund_amount * 100),
                    "speed": "normal",
                    "notes": {"reason": f"Order {order.id} canceled by user"}
                })
                wallet.balance += refund_amount
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='CREDIT',
                    amount=refund_amount,
                    description=f"Refund for canceled order #{order.id} (Razorpay)"
                )
            except Exception as e:
                logger.error(f"Razorpay refund failed for order {order.id}: {str(e)}")
                wallet.balance += refund_amount
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='CREDIT',
                    amount=refund_amount,
                    description=f"Refund for canceled order #{order.id} (Razorpay refund failed)"
                )
        else:
            wallet.balance += refund_amount
            wallet.save()
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='CREDIT',
                amount=refund_amount,
                description=f"Refund for canceled order #{order.id}"
            )

        order.is_refunded = True
        order.balance_refunded = refund_amount
        order.save()

        messages.success(request, f"Order canceled successfully. ₹{refund_amount} has been refunded to your wallet.")
        return redirect('order_detail', order_id=order_id)
    
    return render(request, 'cancel_reason.html', {'order': order})








@login_required
def return_reason(request, order_id, item_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_item = get_object_or_404(OrderItem, id=item_id, order=order)
    
    
    if order.status != 'delivered' or not order.can_be_returned:
        messages.error(request, "Return request cannot be made for this order.")
        return redirect('orders:order_detail', order_id=order_id)
    
    
    if order_item.status != 'delivered':
        messages.error(request, "This item cannot be returned in its current status.")
        return redirect('order_detail', order_id=order_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a reason for return.")
            return render(request, 'return_reason.html', {'order': order, 'item': order_item})
        
        order_item.status = 'return_requested'
        order_item.return_reason = reason
        order_item.return_requested_at = datetime.now()
        order_item.save()
        
        order.update_order()
        messages.success(request, "Return request submitted successfully.")
        return redirect('order_detail', order_id=order_id)
    
    return render(request, 'return_reason.html', {'order': order, 'item': order_item})








@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {'order': order}
    return render(request, 'order_success.html', context)








@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.all()
    
    # Debug: Print order items to verify data
    print(f"Order Items for {order.id}: {list(order_items)}")
    for item in order_items:
        print(f"Item: {item.product.name}, Quantity: {item.quantity}, Original Price: {item.get_original_unit_price()}, Offer Price: {item.final_offer_price}, Savings: {item.get_savings()}")

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order_id}.pdf"'
    
    doc = SimpleDocTemplate(
        response,
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='Title',
        fontSize=16,
        leading=20,
        alignment=1,  # Center
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    normal_style = ParagraphStyle(
        name='Normal',
        fontSize=10,
        leading=12,
        spaceAfter=6,
        fontName='Helvetica'
    )
    bold_style = ParagraphStyle(
        name='Bold',
        fontSize=10,
        leading=12,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    right_align_style = ParagraphStyle(
        name='RightAlign',
        fontSize=10,
        leading=12,
        alignment=2,  # Right
        spaceAfter=6,
        fontName='Helvetica'
    )

    # Header: Business Details
    elements.append(Paragraph("LONDON BIRD", title_style))
    elements.append(Paragraph("Calicut, Kakkanchery<br/>Brototype, Kinfra", normal_style))
    elements.append(Paragraph("Phone: +000000000000<br/>Email: londonbird@gmail.com", normal_style))
    elements.append(Spacer(1, 0.25 * inch))

    # Invoice Details
    elements.append(Paragraph("INVOICE", bold_style))
    elements.append(Paragraph(f"Invoice #{order.id}", normal_style))
    elements.append(Paragraph(f"Date: {order.created_at.strftime('%m/%d/%Y')}", normal_style))
    elements.append(Spacer(1, 0.25 * inch))

    # Customer Details: Bill To and Ship To
    elements.append(Paragraph("Bill To", bold_style))
    elements.append(Paragraph(f"{order.user.get_full_name() or order.user.username}", normal_style))
    elements.append(Paragraph("8157087993", normal_style))  # Placeholder; replace with actual phone number
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("Ship To", bold_style))
    if order.shipping_address:
        addr = order.shipping_address
        address_text = f"{addr.address}, {addr.city}, {addr.state} {addr.postcode}, {addr.country}"
        elements.append(Paragraph(address_text, normal_style))
    elements.append(Spacer(1, 0.1 * inch))

    # Payment Method and Order Status
    elements.append(Paragraph(f"Payment Method: {order.payment_method}", normal_style))
    elements.append(Paragraph(f"Order Status: {order.status.upper()}", normal_style))
    elements.append(Spacer(1, 0.25 * inch))

    # Product Table with Offer Price
    elements.append(Paragraph("Order Items", bold_style))
    col_widths = [2.2 * inch, 0.8 * inch, 1.2 * inch, 1.2 * inch, 1.1 * inch]  # Total 6.5in
    data = [['Product', 'Quantity', 'Price', 'Offer Price', 'Total']]
    total_product_discount = Decimal('0.00')
    
    for item in order_items:
        original_price = item.get_original_unit_price()
        offer_price = item.final_offer_price if item.final_offer_price > 0 else item.get_discounted_unit_price()
        savings = item.get_savings()
        total_product_discount += savings
        
        # Use offer price for total if applicable
        price_to_use = offer_price if savings > 0 else original_price
        total = item.quantity * price_to_use
        
        data.append([
            Paragraph(item.product.name, normal_style),
            Paragraph(str(item.quantity), normal_style),
            Paragraph(f"₹{original_price:,.2f}", normal_style),
            Paragraph(f"₹{offer_price:,.2f}" if savings > 0 else "-", normal_style),
            Paragraph(f"₹{total:,.2f}", normal_style)
        ])

    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Product name left-aligned
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),  # Other columns centered
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.25 * inch))

    # Summary: Subtotal, Product Discount, Coupon Discount, Delivery Charge, Grand Total
    subtotal = sum(item.quantity * item.get_original_unit_price() for item in order_items)
    coupon_discount = order.discount_coupon_amount if order.discount_applied else Decimal('0.00')
    delivery_charge = order.shipping
    total_discount = total_product_discount + coupon_discount
    grand_total = subtotal - total_discount + delivery_charge

    elements.append(Paragraph(f"Subtotal: ₹{subtotal:,.2f}", right_align_style))
    if total_product_discount > 0:
        elements.append(Paragraph(f"Product Discount: -₹{total_product_discount:,.2f}", right_align_style))
    if coupon_discount > 0:
        elements.append(Paragraph(f"Coupon Discount: -₹{coupon_discount:,.2f}", right_align_style))
    elements.append(Paragraph(f"Delivery Charge: ₹{delivery_charge:,.2f}", right_align_style))
    elements.append(Paragraph(f"Grand Total: ₹{grand_total:,.2f}", bold_style))
    elements.append(Spacer(1, 0.25 * inch))

    # Footer
    elements.append(Paragraph("Thank you for your purchase!", normal_style))
    elements.append(Paragraph("For any questions or concerns regarding this invoice, please contact our customer support.", normal_style))

    doc.build(elements)
    return response








@login_required
@user_passes_test(is_admin)
def handle_return(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        action = request.POST.get('action')
        print(f" action is {action}")
        

        order = get_object_or_404(Order, id=order_id)
        order_items = order.items.all()

        if order.is_refunded:
            messages.error(request, "This order has already been refunded.")
            return redirect('admin_dashboard')

        if action == 'accept':
            for item in order_items:
                if item.status not in ['canceled', 'returned', 'return_denied'] and item.size and item.quantity > 0:
                    item.size.stock += item.quantity
                    item.size.save()
                item.status = 'returned'
                item.returned_at = timezone.now()
                item.save()

            
            wallet = Wallet.objects.get(user=order.user)  

            refund_amount = order.total_price

            if order.payment_method == 'Razorpay' and order.payment_status == 'Completed':
                try:
                    payment_id = razorpay_client.order.fetch(order.razorpay_order_id)['payments'][0]['payment_id']
                    razorpay_client.payment.refund(payment_id, {
                        "amount": int(refund_amount * 100),
                        "speed": "normal",
                        "notes": {"reason": f"Order {order.id} returned"}
                    })
                    wallet.balance += refund_amount
                    wallet.save()
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type='CREDIT',
                        amount=refund_amount,
                        description=f"Refund for returned order #{order.id} (Razorpay)"
                    )
                except Exception as e:
                    logger.error(f"Razorpay refund failed for order {order.id}: {str(e)}")
                    wallet.balance += refund_amount
                    wallet.save()
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type='CREDIT',
                        amount=refund_amount,
                        description=f"Refund for returned order #{order.id} (Razorpay refund failed)"
                    )
            else:
                wallet.balance += refund_amount
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='CREDIT',
                    amount=refund_amount,
                    description=f"Refund for returned order #{order.id}"
                )

            order.is_refunded = True
            order.balance_refunded = refund_amount
            order.status = 'returned'
            order.save()

            messages.success(request, f'Return request for order {order.id} accepted, stock updated, and ₹{refund_amount} refunded to user\'s wallet.')
        elif action == 'deny':
            order.status = 'return_denied'
            order.save()
            print("iam working here, when order dening")
            for item in order_items:
                item.status = 'return_denied'
                item.save()
           
            print(f"order details:{order}")
            print(f"order status:{order.status}")

            messages.warning(request, f'Return request for order {order.id} denied.')

            

        return redirect('admin_dashboard')

    return redirect('admin_dashboard')




