from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import Address
from admin_panel.models import UserProfile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import os
import random
from django.conf import settings
from django.core.mail import send_mail
import string
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password
import time
import re

@login_required
def user_profile(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    address = user.addresses.filter(is_default=True).first() or user.addresses.first()
    
    if request.method == 'POST':
        profile_picture = request.FILES.get('profile_picture')
        if profile_picture:
            if not profile_picture.content_type.startswith('image/'):
                messages.error(request, 'Please upload a valid image file.')
                return redirect('user_profile')
            
            max_size = 5 * 1024 * 1024
            if profile_picture.size > max_size:
                messages.error(request, 'Image file is too large. Maximum size is 5MB.')
                return redirect('user_profile')
            
            if profile.profile_picture:
                try:
                    if os.path.isfile(profile.profile_picture.path):
                        os.remove(profile.profile_picture.path)
                except Exception as e:
                    messages.warning(request, f"Could not delete old profile picture: {str(e)}")
            
            profile.profile_picture = profile_picture
            profile.save()
            messages.success(request, 'Profile picture updated successfully.')
        else:
            messages.error(request, 'No image file was uploaded. Please try again.')
        
        return redirect('user_profile')
    
    context = {
        'user': user,
        'profile': profile,
        'address': address,
    }
    
    return render(request, 'user_profile.html', context)

@login_required
def edit_profile(request):
    user = request.user
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        if not all([username, first_name, last_name]):
            messages.error(request, 'All fields are required.')
            return redirect('edit_profile')
        
        if User.objects.exclude(id=user.id).filter(username=username).exists():
            messages.error(request, 'Username is already taken.')
            return redirect('edit_profile')
        
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('user_profile')
    context = {
        'user': user,
    }
    return render(request, 'edit_profile.html', context)





@login_required
def edit_email(request):
    user = request.user
    if request.method == 'POST':
        new_mail = request.POST.get('currentEmailInput', '').strip()

        
        if not new_mail:
            messages.error(request, 'Please enter an email address.')
            return redirect('edit_email')

        
        if len(new_mail) > 254:
            messages.error(request, 'Email address is too long (maximum 254 characters).')
            return redirect('edit_email')

        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, new_mail):
            messages.error(request, 'Please enter a valid email address (e.g., user@example.com).')
            return redirect('edit_email')

        
        if '.' not in new_mail.split('@')[-1]:
            messages.error(request, 'Email domain is invalid (e.g., must include a top-level domain like .com).')
            return redirect('edit_email')

        
        if new_mail.lower() == user.email.lower():
            messages.error(request, 'New email cannot be the same as your current email.')
            return redirect('edit_email')

        
        if User.objects.exclude(id=user.id).filter(email__iexact=new_mail).exists():
            messages.error(request, 'This email is already in use.')
            return redirect('edit_email')

        
        otp = ''.join(random.choices(string.digits, k=6))
        print(otp)
        request.session['otp'] = otp
        request.session['new_email'] = new_mail
        request.session['otp_timestamp'] = time.time()

       
        subject = 'Email Verification OTP'
        message = f'Your OTP for email verification is: {otp}. It is valid for 5 minutes.'
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [new_mail],
                fail_silently=False,
            )
            messages.success(request, f'An OTP has been sent to {new_mail}.')
            return redirect('verify_mail')
        except Exception as e:
            messages.error(request, f'Failed to send OTP: {str(e)}')
            return redirect('edit_email')

    return render(request, 'edit_email.html')






def profile_verify(request):
    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        stored_otp = request.session.get('otp')
        new_email = request.session.get('new_email')
        otp_timestamp = request.session.get('otp_timestamp')
        
        
        if not all([otp_entered, stored_otp, new_email, otp_timestamp]):
            messages.error(request, 'Invalid or expired OTP.')
            return redirect('edit_email')
         
        if time.time() - float(otp_timestamp) > 300:
            messages.error(request, 'OTP has expired. Please request a new one.')
            return redirect('edit_email')
        
        if otp_entered == stored_otp:
            user = request.user
            user.email = new_email
            user.save()
            
            del request.session['otp']
            del request.session['new_email']
            del request.session['otp_timestamp']
            messages.success(request, 'Email updated successfully.')
            return redirect('user_profile')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect('verify_mail')
    return render(request, 'profile_verify.html')




@login_required
def change_password(request):
    user = request.user
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        
        required_fields = {
            'Current Password': current_password,
            'New Password': new_password,
            'Confirm Password': confirm_password,
        }
        for field_name, field_value in required_fields.items():
            if not field_value:
                messages.error(request, f'{field_name} is required.')
                return redirect('change_password')

        
        if not check_password(current_password, user.password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('change_password')

        
        if new_password != confirm_password:
            messages.error(request, 'New password and confirm password do not match.')
            return redirect('change_password')

        
        if len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters long.')
            return redirect('change_password')
        if len(new_password) > 128:
            messages.error(request, 'New password cannot be longer than 128 characters.')
            return redirect('change_password')

        
        if check_password(new_password, user.password):
            messages.error(request, 'New password cannot be the same as the current password.')
            return redirect('change_password')

      
        if not re.search(r'[A-Z]', new_password):
            messages.error(request, 'New password must contain at least one uppercase letter.')
            return redirect('change_password')
        if not re.search(r'[a-z]', new_password):
            messages.error(request, 'New password must contain at least one lowercase letter.')
            return redirect('change_password')
        if not re.search(r'\d', new_password):
            messages.error(request, 'New password must contain at least one digit.')
            return redirect('change_password')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            messages.error(request, 'New password must contain at least one special character (e.g., !@#$%).')
            return redirect('change_password')

        
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password updated successfully.')
        return redirect('user_profile')

    return render(request, 'change_password.html')





@login_required
def address(request):
    user = request.user
    addresses = user.addresses.all()
    next_url = request.GET.get('next', 'user_address')
    form_data = {}  

    if request.method == 'POST':
        action = request.POST.get('action')
        next_url = request.POST.get('next', next_url)

        if action == 'save':
            address_id = request.POST.get('address_id')
            name = request.POST.get('name', '').strip()
            street_address = request.POST.get('street_address', '').strip()
            city = request.POST.get('city', '').strip()
            state = request.POST.get('state', '').strip()
            postal_code = request.POST.get('postal_code', '').strip()
            country = request.POST.get('country', '').strip()
            phone = request.POST.get('phone', '').strip()

            
            form_data = {
                'name': name,
                'street_address': street_address,
                'city': city,
                'state': state,
                'postal_code': postal_code,
                'country': country,
                'phone': phone,
            }

           
            required_fields = {
                'name': name,
                'street_address': street_address,
                'city': city,
                'state': state,
                'postal_code': postal_code,
                'country': country,
                'phone': phone,
            }
            for field_name, field_value in required_fields.items():
                if not field_value:
                    messages.error(request, f'{field_name.replace("_", " ").title()} is required.')
                    return render(request, 'address.html', {'addresses': addresses, 'next_url': next_url, 'form_data': form_data})

            
            if len(street_address) > 255:
                messages.error(request, 'Street address is too long (max 255 characters).')
                return render(request, 'address.html', {'addresses': addresses, 'next_url': next_url, 'form_data': form_data})

            
            text_pattern = r'^[A-Za-z\s]+$'
            if not re.match(text_pattern, name):
                messages.error(request, 'Name should only contain letters and spaces.')
                return render(request, 'address.html', {'addresses': addresses, 'next_url': next_url, 'form_data': form_data})
            if not re.match(text_pattern, city):
                messages.error(request, 'City should only contain letters and spaces.')
                return render(request, 'address.html', {'addresses': addresses, 'next_url': next_url, 'form_data': form_data})
            if not re.match(text_pattern, state):
                messages.error(request, 'State should only contain letters and spaces.')
                return render(request, 'address.html', {'addresses': addresses, 'next_url': next_url, 'form_data': form_data})
            if not re.match(text_pattern, country):
                messages.error(request, 'Country should only contain letters and spaces.')
                return render(request, 'address.html', {'addresses': addresses, 'next_url': next_url, 'form_data': form_data})

            
            postal_pattern = r'^\d{5}(-\d{4})?$|^\d{6}$'
            if not re.match(postal_pattern, postal_code):
                messages.error(request, 'Enter a valid postal code (e.g., 12345, 12345-6789 for US, or 123456 for India).')
                return render(request, 'address.html', {'addresses': addresses, 'next_url': next_url, 'form_data': form_data})

            
            if postal_code in ['00000', '000000', '00000-0000']:
                messages.error(request, 'Postal code cannot be all zeros.')
                return render(request, 'address.html', {'addresses': addresses, 'next_url': next_url, 'form_data': form_data})

            
            if len(postal_code) == 6 and not re.match(r'^[1-9]\d{5}$', postal_code):
                messages.error(request, 'Indian PIN code must start with a non-zero digit (e.g., 123456).')
                return render(request, 'address.html', {'addresses': addresses, 'next_url': next_url, 'form_data': form_data})

            
            phone_pattern = r'^\+?\d{10,15}$'
            if not re.match(phone_pattern, phone):
                messages.error(request, 'Enter a valid phone number (e.g., +911234567890 or 1234567890, 10-15 digits).')
                return render(request, 'address.html', {'addresses': addresses, 'next_url': next_url, 'form_data': form_data})

            
            duplicate_exists = Address.objects.filter(
                user=user,
                postal_code=postal_code,
                city=city,
            ).exclude(id=address_id if address_id else None).exists()
            if duplicate_exists:
                messages.error(request, 'An address with this postal code and city already exists.')
                return render(request, 'address.html', {'addresses': addresses, 'next_url': next_url, 'form_data': form_data})

            
            if address_id:
                address = get_object_or_404(Address, id=address_id, user=user)
                address.name = name.title()
                address.street_address = street_address
                address.city = city.title()
                address.state = state.title()
                address.postal_code = postal_code
                address.country = country.title()
                address.phone = phone
                if address.is_default:
                    Address.objects.filter(user=user, is_default=True).exclude(id=address.id).update(is_default=False)
                address.save()
                messages.success(request, 'Address updated successfully.')
            else:
                address = Address.objects.create(
                    user=user,
                    name=name.title(),
                    street_address=street_address,
                    city=city.title(),
                    state=state.title(),
                    postal_code=postal_code,
                    country=country.title(),
                    phone=phone,
                    is_default=(not user.addresses.exists())
                )
                messages.success(request, 'Address added successfully.')

        elif action == 'delete':
            address_id = request.POST.get('address_id')
            address = get_object_or_404(Address, id=address_id, user=user)
            address.delete()
            messages.success(request, 'Address deleted successfully.')

        return redirect(next_url)

    context = {
        'addresses': addresses,
        'next_url': next_url,
        'form_data': form_data,
    }
    return render(request, 'address.html', context)





@login_required
def set_default_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
    address.is_default = True
    address.save()
    messages.success(request, 'Default address updated successfully!')
    return redirect('user_address')