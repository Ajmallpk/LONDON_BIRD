from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.template.loader import get_template
from django.core.exceptions import ValidationError
from PIL import Image
import os
from django.conf import settings
from io import BytesIO
from django.core.files.base import ContentFile
from django.views.decorators.cache import never_cache
from checkout.models import Order, OrderItem
from products.models import Size
from django.utils import timezone
from django.db.models import F
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.contrib.auth import authenticate, login
from django.template.loader import get_template
from django.utils import timezone
from checkout.models import Order, OrderItem
from products.models import product, Variant, Size
from categories.models import categories
from django.http import FileResponse
from datetime import datetime, timedelta
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import pytz




def is_admin(user):
    return user.is_authenticated and user.is_superuser

def admin_login(request):
    try:
        template = get_template('adminlogin.html')
        print(f"Template found: {template.origin}")
    except Exception as e:
        print(f"Template error: {e}")
        
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid admin credentials.')
    return render(request, 'adminlogin.html')

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    
    return render(request, 'dashboard.html')





@login_required
@user_passes_test(is_admin)
def user_management(request):
    users = User.objects.filter(is_staff=False).order_by('-date_joined')
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | Q(email__icontains=search_query)
        )
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'users.html', {
        'page_obj': page_obj,
        'search_query': search_query,
    })





@login_required
@user_passes_test(is_admin)
def block_user(request, user_id):
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        user.is_active = False
        user.save()
        messages.success(request, f'{user.username} has been blocked.')
        return redirect('user_management')
    return render(request, 'confirm_block.html', {'user': user})




@login_required
@user_passes_test(is_admin)
def unblock_user(request, user_id):
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        user.is_active = True
        user.save()
        messages.success(request, f'{user.username} has been unblocked.')
        return redirect('user_management')
    return render(request, 'confirm_unblock.html', {'user': user})




@login_required
@user_passes_test(is_admin)
def admin_order_list(request):
    query = request.GET.get('search', '')
    sort = request.GET.get('sort', '-created_at')
    status = request.GET.get('status', '')
    page_number = request.GET.get('page')

    orders = Order.objects.all().select_related('user').prefetch_related('items')

    if query:
        orders = orders.filter(
            Q(id__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query)
        )

    if status:
        orders = orders.filter(status=status)

    orders = orders.order_by(sort)

    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_orderlist.html', {
        'page_obj': page_obj,
        'search_query': query,
        'sort': sort,
        'status': status,
        'status_choices': Order.ORDER_STATUS_CHOICES,
    })





@login_required
@user_passes_test(is_admin)
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all()

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status:
            if new_status == 'canceled' and not order.can_be_canceled:
                messages.error(request, "This order cannot be canceled because some items are in a non-cancelable state.")
            elif order.update_status(new_status):
                messages.success(request, f"Order status updated to {new_status}.")
                return redirect('admin_orders_list')
            else:
                messages.error(request, f"Cannot update order status to {new_status} from {order.status}.")
        else:
            messages.error(request, "No status provided.")
        return redirect('admin_order_detail', order_id=order.id)

    return render(request, 'admin_orderdetail.html', {
        'order': order,
        'order_items': order_items,
        'status_choices': Order.ORDER_STATUS_CHOICES,
    })





@login_required
@user_passes_test(is_admin)
def return_requests(request):
    return_items = OrderItem.objects.filter(order__status='return_requested') \
        .select_related('order__user', 'product', 'product_variant', 'size')

    return render(request, 'admin_reuturnrequest.html', {
        'return_items': return_items,
    })




@login_required
@user_passes_test(is_admin)
def inventory_management(request):
    sizes = Size.objects.all().select_related('variant__product')

    if request.method == 'POST':
        size_id = request.POST.get('size_id')
        new_stock = request.POST.get('stock')
        size = get_object_or_404(Size, id=size_id)

        if new_stock and new_stock.isdigit() and int(new_stock) >= 0:
            
            size.stock = F('stock') - size.stock + int(new_stock)
            size.save()
            size.refresh_from_db()  
            messages.success(request, f"Stock updated for {size}.")
           
        else:
            messages.error(request, "Invalid stock value. Please enter a non-negative number.")

        return redirect('inventory_management')

    return render(request, 'inventory_management.html', {
        'sizes': sizes,
    })
    






KOLKATA_TZ = pytz.timezone('Asia/Kolkata')
    
    
    
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    timezone.activate(KOLKATA_TZ)
    
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)

   
    date_filter = request.GET.get('date_filter', 'custom')
    custom_start = request.GET.get('start_date')
    custom_end = request.GET.get('end_date')

    if date_filter == 'daily':
        start_date = end_date - timedelta(days=1)
    elif date_filter == 'weekly':
        start_date = end_date - timedelta(days=7)
    elif date_filter == 'monthly':
        start_date = end_date - timedelta(days=30)
    elif date_filter == 'yearly':
        start_date = end_date - timedelta(days=365)
    elif date_filter == 'custom' and custom_start and custom_end:
        try:
            start_date = datetime.strptime(custom_start, '%Y-%m-%d')
            start_date = KOLKATA_TZ.localize(start_date)
            end_date = datetime.strptime(custom_end, '%Y-%m-%d')
            end_date = KOLKATA_TZ.localize(end_date.replace(hour=23, minute=59, second=59))
        except ValueError:
            messages.error(request, "Invalid date format. Using default range (last 30 days).")

  
    all_orders = Order.objects.filter(status='delivered')
    total_revenue_ever = 0
    for order in all_orders:
        order_items = order.items.exclude(status='returned')
        order_revenue = sum(item.final_offer_price * item.quantity for item in order_items)
        total_revenue_ever += order_revenue

    
    pending_orders = Order.objects.filter(status='pending').count()

    
    total_users = User.objects.filter(is_staff=False).count()

   
    orders_in_range = Order.objects.filter(
        created_at__range=[start_date, end_date],
        status='delivered'
    )

    
    sales_data = {}
    current_date = start_date.date()
    end_date_date = end_date.date()
    delta = timedelta(days=1)

    while current_date <= end_date_date:
        sales_data[current_date.strftime('%Y-%m-%d')] = 0
        current_date += delta

    for order in orders_in_range:
        order_items = order.items.exclude(status='returned')
        order_revenue = sum(item.final_offer_price * item.quantity for item in order_items)
        order_date = order.created_at.astimezone(KOLKATA_TZ).date().strftime('%Y-%m-%d')
        if order_date in sales_data:
            sales_data[order_date] += float(order_revenue)

    chart_labels = list(sales_data.keys())
    chart_data = list(sales_data.values())

    
    top_products = (
        OrderItem.objects.filter(
            order__created_at__range=[start_date, end_date],
            order__status='delivered'
        )
        .exclude(status='returned')
        .values('product__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:10] 
    )

   
    top_categories = (
        OrderItem.objects.filter(
            order__created_at__range=[start_date, end_date],
            order__status='delivered'
        )
        .exclude(status='returned')
        .values('product__category__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:10]  
    )

    
    if request.method == 'POST' and 'generate_ledger' in request.POST:
        ledger_start_date = request.POST.get('ledger_start_date')
        ledger_end_date = request.POST.get('ledger_end_date')

        try:
            ledger_start = KOLKATA_TZ.localize(datetime.strptime(ledger_start_date, '%Y-%m-%d'))
            ledger_end = KOLKATA_TZ.localize(datetime.strptime(ledger_end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        except ValueError:
            messages.error(request, "Invalid date format for ledger generation.")
            ledger_start = start_date
            ledger_end = end_date

        ledger_orders = Order.objects.filter(
            created_at__range=[ledger_start, ledger_end],
            status='delivered'
        ).exclude(items__status='returned').distinct()

        return generate_ledger_pdf(ledger_orders, ledger_start, ledger_end)

    context = {
        'total_revenue_ever': total_revenue_ever,
        'pending_orders': pending_orders,
        'total_users': total_users,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'top_products': top_products,
        'top_categories': top_categories,
        'start_date': start_date.date(),
        'end_date': end_date.date(),
        'date_filter': date_filter,
    }
    return render(request, 'dashboard.html', context)

def generate_ledger_pdf(orders, start_date, end_date):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    elements.append(Paragraph(f"Ledger Book ({start_date.date()} to {end_date.date()})", title_style))

    
    data = [['Date', 'Order ID', 'Customer', 'Products', 'Payment Method', 'Amount (₹)']]
    for order in orders:
        order_items = order.items.exclude(status='returned')
        if not order_items.exists():
            continue
        products = "; ".join([f"{item.product.name} (Qty: {item.quantity})" for item in order_items])
        amount = sum(item.final_offer_price * item.quantity for item in order_items)
        data.append([
            order.created_at.astimezone(KOLKATA_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            order.id,
            order.user.username,
            products,
            order.payment_method,
            f"{amount:.2f}"
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='ledger_book.pdf')