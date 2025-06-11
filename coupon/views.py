from django.utils.timezone import make_aware, now
from datetime import datetime
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime
from .models import Coupon
from django.utils.timezone import make_aware, now
from .models import Coupon, CouponUsage

def is_admin(user):
    return user.is_authenticated and user.is_superuser

@login_required
@user_passes_test(is_admin)
def coupon_management(request):
    coupons = Coupon.objects.all()
    
    
    status = request.GET.get('status', '')
    validity = request.GET.get('validity', '')
    
    if status:
        is_active = status == 'active'
        coupons = coupons.filter(is_active=is_active)
    
    if validity:
        if validity == 'valid':
            coupons = [coupon for coupon in coupons if coupon.is_valid()]
        elif validity == 'invalid':
            coupons = [coupon for coupon in coupons if not coupon.is_valid()]
    
    context = {
        'coupons': coupons,
        'status': status,
        'validity': validity,
    }
    return render(request, 'coupon_management.html', context)

@login_required
@user_passes_test(is_admin)
def add_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        discount_type = request.POST.get('discount_type')
        discount_amount = request.POST.get('discount_amount')
        max_discount = request.POST.get('max_discount')
        min_purchase = request.POST.get('min_purchase')
        valid_from = request.POST.get('valid_from') 
        valid_until = request.POST.get('valid_until')  
        is_active = request.POST.get('is_active') == 'on'

        try:
            
            if valid_from:
                valid_from = make_aware(datetime.strptime(valid_from, '%Y-%m-%dT%H:%M'))
            else:
                valid_from = now()  
            if valid_until:
                valid_until = make_aware(datetime.strptime(valid_until, '%Y-%m-%dT%H:%M'))
            else:
                raise ValidationError("Valid until date is required.") 

            
            discount_amount = Decimal(discount_amount) if discount_amount else None
            max_discount = Decimal(max_discount) if max_discount else None
            min_purchase = Decimal(min_purchase) if min_purchase else Decimal('0.00')
            

            
            if not code:
                raise ValidationError("Coupon code is required.")
            if not discount_amount:
                raise ValidationError("Discount amount is required.")
            if not valid_from or not valid_until:
                raise ValidationError("Valid from and valid until dates are required.")

            
            coupon = Coupon(
                code=code,
                discount_type=discount_type,
                discount_amount=discount_amount,
                max_discount=max_discount,
                min_purchase=min_purchase,
                valid_from=valid_from,
                valid_until=valid_until,
                is_active=is_active,
            )

            coupon.full_clean()
            coupon.save()
            messages.success(request, f"Coupon '{code}' created successfully!")
            return redirect('coupon_management')

        except ValidationError as e:
            messages.error(request, f"Error creating coupon: {e}")
        except ValueError as e:
            messages.error(request, f"Invalid input format: {e}. Ensure all numeric fields are valid and dates are in the correct format (e.g., 2025-05-28T13:34).")
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {e}. Ensure the coupon code is unique.")

    return render(request, 'add_coupon.html')

@login_required
@user_passes_test(is_admin)
def edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)

    if request.method == 'POST':
        code = request.POST.get('code')
        discount_type = request.POST.get('discount_type')
        discount_amount = request.POST.get('discount_amount')
        max_discount = request.POST.get('max_discount')
        min_purchase = request.POST.get('min_purchase')
        valid_from = request.POST.get('valid_from')
        valid_until = request.POST.get('valid_until')
        is_active = request.POST.get('is_active') == 'on'

        try:
            if valid_from:
                valid_from = make_aware(datetime.strptime(valid_from, '%Y-%m-%dT%H:%M'))
            if valid_until:
                valid_until = make_aware(datetime.strptime(valid_until, '%Y-%m-%dT%H:%M'))

            coupon.code = code
            coupon.discount_type = discount_type
            coupon.discount_amount = Decimal(discount_amount) if discount_amount else None
            coupon.max_discount = Decimal(max_discount) if max_discount else None
            coupon.min_purchase = Decimal(min_purchase) if min_purchase else Decimal('0.00')
            coupon.valid_from = valid_from
            coupon.valid_until = valid_until
           
            coupon.is_active = is_active

            coupon.full_clean()
            coupon.save()
            messages.success(request, f"Coupon '{code}' updated successfully!")
            return redirect('coupon_management')

        except ValidationError as e:
            messages.error(request, f"Error updating coupon: {e}")
        except ValueError as e:
            messages.error(request, f"Invalid input format: {e}. Ensure all numeric fields are valid and dates are in the correct format (e.g., 2025-05-28T13:34).")
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {e}. Ensure the coupon code is unique.")

    context = {
        'coupon': coupon,
    }
    return render(request, 'edit_coupon.html', context)

@login_required
@user_passes_test(is_admin)
def delete_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == 'POST':
        usage_count = coupon.get_usage_count()
        if usage_count > 0:
            messages.error(request, f"Cannot delete coupon '{coupon.code}' because it has been used in {usage_count} order(s).")
        else:
            coupon.delete()
            messages.success(request, f"Coupon '{coupon.code}' deleted successfully!")
        return redirect('coupon_management')
    return redirect('coupon_management')

@login_required
def user_available_coupons(request):
    """
    Display available coupons for the logged-in user.
    Filters coupons that are active, within validity period, and not fully used.
    Also identifies which coupons the user has already used.
    """
    
    current_time = now()

    
    available_coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=current_time,
        valid_until__gte=current_time
    )

    
    available_coupons = [
        coupon for coupon in available_coupons
        if coupon.get_usage_count() < 1  
    ]

    
    used_coupon_ids = CouponUsage.objects.filter(
        order__user=request.user
    ).values_list('coupon_id', flat=True).distinct()

    context = {
        'coupons': available_coupons,
        'used_coupon_ids': used_coupon_ids,
    }
    return render(request, 'user_available_coupons.html', context)