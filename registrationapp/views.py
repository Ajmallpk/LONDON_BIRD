from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.utils import timezone as django_timezone
from datetime import timedelta, datetime
from django.contrib.auth import authenticate, login
from django.core.mail import send_mail
from django.http import JsonResponse
import random
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
import datetime as dt 
import re 
from django.views.decorators.cache import never_cache
from admin_panel.models import UserProfile  
from coupon.models import Coupon ,CouponUsage 
import string 
from django.contrib.auth.decorators import login_required 




def generate_otp():
    return random.randint(100000, 999999)

def send_otp_email(email, otp, purpose="Registration"):
    try:
        subject = f'Your OTP for {purpose}'
        message = f'Your OTP is: {otp}. It is valid for 1 minute.'
        from_email = 'ajuaamal@gmail.com'
        recipient_list = [email]
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        print(f"OTP {otp} sent to {email} for {purpose}")
        return True
    except Exception as e:
        print(f"Failed to send OTP email for {purpose}: {e}")
        return False






def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit."
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character."
    return True, ""



def generate_coupon(user):
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    while Coupon.objects.filter(code=code).exists():
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

    now = django_timezone.now()
    coupon = Coupon.objects.create(
        code=code,
        discount_type='Fixed',
        discount_amount=100.00,  
        max_discount=None,
        min_purchase=0.00,
        valid_from=now,
        valid_until=now + timedelta(days=30),
        is_active=True,
        usage_limit=1, 
        user=user,  
    )
    return coupon









@never_cache
def register(request):
    form_data = {}
    if request.method == 'POST':
        print("Form data:", request.POST)
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password').strip()
        confirm_password = request.POST.get('confirm_password').strip()
        referral_code = request.POST.get('referral_code', '').strip()
        terms = request.POST.get('terms')
        form_data = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'referral_code': referral_code,
        }

        errors = {}
        if not terms:
            errors['terms'] = "You must agree to the terms and conditions."
        if not username:
            errors['username'] = "Username is required."
        elif not re.match(r'^[a-zA-Z_]+$', username):
            errors['username'] = "Username must contain only letters and underscores."
        elif not re.search(r'[a-zA-Z]', username):
            errors['username'] = "Username must contain at least one letter."
        elif len(username) < 3 or len(username) > 150:
            errors['username'] = "Username must be between 3 and 150 characters."
        if not first_name:
            errors['first_name'] = "First name is required."
        elif not re.match(r'^[a-zA-Z]+$', first_name):
            errors['first_name'] = "First name must contain only letters."
        if not last_name:
            errors['last_name'] = "Last name is required."
        elif not re.match(r'^[a-zA-Z]+$', last_name):
            errors['last_name'] = "Last name must contain only letters."    
        if not email:
            errors['email'] = "Email is required."
        if not password:
            errors['password'] = "Password is required."
        if User.objects.filter(username=username).exists():
            errors['username'] = "Username already exists. Please choose a different one."
        if User.objects.filter(email=email).exists():
            errors['email'] = "Email is already registered. Please use a different email."
        if password != confirm_password:
            errors['password'] = "Passwords do not match."
        is_valid, error_message = validate_password(password)
        if not is_valid:
            errors['password'] = error_message
            
            
        
        if referral_code: 
            if not UserProfile.objects.filter(referral_code=referral_code).exists():  
                errors['referral_code'] = "Invalid referral code."  


        if errors:
            print("Validation errors:", errors)
            for error in errors.values():
                messages.error(request, error)
            return render(request, 'register.html', {'form_data': form_data})

        otp = generate_otp()
        expires_at = django_timezone.now() + timedelta(minutes=1)

        for key in ['email', 'reset_email', 'reg_otp', 'reg_otp_expires_at', 'otp', 'otp_expires_at', 'is_password_reset', 'username', 'password', 'first_name', 'last_name', 'referral_code']:
            request.session.pop(key, None)

        request.session['email'] = email
        request.session['reg_otp'] = otp
        request.session['reg_otp_expires_at'] = int(expires_at.timestamp())
        request.session['username'] = username
        request.session['password'] = password
        request.session['first_name'] = first_name
        request.session['last_name'] = last_name
        request.session['referral_code'] = referral_code
        request.session.modified = True
        print("Registration session data:", request.session.items())

        if not send_otp_email(email, otp, purpose="Registration"):
            messages.error(request, "Failed to send OTP email. Please try again.")
            print("Redirecting back to register due to email failure")
            return render(request, 'register.html', {'form_data': form_data})

        print("Redirecting to OTP page for registration")
        return redirect('verify_otp')
    return render(request, 'register.html', {'form_data': form_data})






@never_cache
def verify_otp(request):
    context = {}
    email = request.session.get('reset_email')
    if not email:
        email = request.session.get('email')
    if not email:
        return redirect('register')  
    context['email'] = email
    print("Verify OTP session:", request.session.items())

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')

        
        reg_otp = request.session.get('reg_otp')
        reg_otp_expires_at = request.session.get('reg_otp_expires_at')
        if reg_otp and reg_otp_expires_at:
            try:
                reg_expires_at = datetime.fromtimestamp(reg_otp_expires_at, tz=dt.timezone.utc)
                if django_timezone.now() > reg_expires_at:
                    print("Registration OTP expired")
                    context['error'] = 'Registration OTP has expired.'
                    context['reg_otp_expires_at'] = reg_otp_expires_at
                    return render(request, 'otp.html', context)
            except ValueError as e:
                print(f"Invalid registration OTP expiration format: {e}")
                context['error'] = 'Invalid registration OTP expiration format.'
                context['reg_otp_expires_at'] = reg_otp_expires_at
                return render(request, 'otp.html', context)

            if str(reg_otp) == entered_otp:
                username = request.session.get('username')
                password = request.session.get('password')
                first_name = request.session.get('first_name')
                last_name = request.session.get('last_name')
                referral_code = request.session.get('referral_code')  

                try:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    
                    
                    
                     
                    user_profile, created = UserProfile.objects.get_or_create(user=user)  

                    
                    if referral_code:  
                        try:  
                            referrer_profile = UserProfile.objects.get(referral_code=referral_code)  
                            user_profile.referred_by = referrer_profile  
                            user_profile.save() 

                            
                            coupon = generate_coupon(referrer_profile.user)  
                            messages.success(request, f"Your referrer has received a coupon: {coupon.code}")  
                        except UserProfile.DoesNotExist:  
                            pass  
                        
                        
                        
                except Exception as e:
                    print(f"Failed to create user: {e}")
                    context['error'] = 'Failed to create user. Username or email may already exist.'
                    context['reg_otp_expires_at'] = reg_otp_expires_at
                    return render(request, 'otp.html', context)

                for key in ['reg_otp', 'reg_otp_expires_at', 'username', 'email', 'password', 'first_name', 'last_name', 'referral_code']:
                    request.session.pop(key, None)
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                messages.success(request, "Signup successful! You are now logged in.")
                print("User registered and logged in, redirecting to login")
                return redirect('login')
            else:
                print("Invalid registration OTP entered")
                context['error'] = 'Invalid OTP. Please try again.'
                context['reg_otp_expires_at'] = reg_otp_expires_at
                return render(request, 'otp.html', context)

       
        forgot_otp = request.session.get('otp')
        forgot_otp_expires_at = request.session.get('otp_expires_at')
        if forgot_otp and forgot_otp_expires_at:
            try:
                forgot_expires_at = datetime.fromtimestamp(forgot_otp_expires_at, tz=dt.timezone.utc)
                if django_timezone.now() > forgot_expires_at:
                    print("Forgot password OTP expired")
                    context['error'] = 'Forgot password OTP has expired.'
                    context['otp_expires_at'] = forgot_otp_expires_at
                    return render(request, 'otp.html', context)
            except ValueError as e:
                print(f"Invalid forgot password OTP expiration format: {e}")
                context['error'] = 'Invalid forgot password OTP expiration format.'
                context['otp_expires_at'] = forgot_otp_expires_at
                return render(request, 'otp.html', context)

            if str(forgot_otp) == entered_otp:
                for key in ['otp', 'otp_expires_at', 'is_password_reset']:
                    request.session.pop(key, None)
                request.session.modified = True
                messages.success(request, 'OTP verified successfully.')
                print("Redirecting to reset password")
                return redirect('reset_password')
            else:
                print("Invalid forgot password OTP entered")
                context['error'] = 'Invalid OTP. Please try again.'
                context['otp_expires_at'] = forgot_otp_expires_at
                return render(request, 'otp.html', context)

        context['error'] = 'Invalid OTP. Please try again.'
        return render(request, 'otp.html', context)

    if request.session.get('reg_otp_expires_at'):
        context['reg_otp_expires_at'] = request.session.get('reg_otp_expires_at')
    if request.session.get('otp_expires_at'):
        context['otp_expires_at'] = request.session.get('otp_expires_at')
    return render(request, 'otp.html', context)






@never_cache
def login__view(request):
    form_data = {}
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        form_data['email'] = email
        print("data",form_data['email'])

        if not email or not password:
            messages.error(request, 'Please enter both email and password.')
            return render(request, 'login.html', {'form_data': form_data})

        try:
            user_obj = User.objects.get(email=email)
            if not user_obj.is_active:
                messages.error(request, "Your account has been blocked. Please contact the administrator for assistance.")
                return render(request, 'login.html', {'form_data': form_data})
            user = authenticate(request, username=user_obj.username, password=password)
            
        except User.DoesNotExist:
            user = None
       
                
        if user is not None:
            login(request, user)
            messages.success(request, "Login successful! Welcome back.")
            print("User logged in, redirecting to index")
            return redirect('index')
        else:
            messages.error(request, "Invalid email or password")
            return render(request, 'login.html', {'form_data': form_data})

    return render(request, 'login.html', {'form_data': form_data})







def resend_otp(request):
    email = request.session.get('email') or request.session.get('reset_email')
    if not email:
        print("No email in session")
        return JsonResponse({'success': False, 'message': 'Session expired. Please start over.'})

    if request.method == 'POST':
        is_password_reset = request.session.get('is_password_reset', False)
        otp_key = 'otp' if is_password_reset else 'reg_otp'
        expires_at_key = 'otp_expires_at' if is_password_reset else 'reg_otp_expires_at'

        current_otp = request.session.get(otp_key)
        current_expires_at = request.session.get(expires_at_key)

        if current_otp and current_expires_at:
            try:
                expires_at = datetime.fromtimestamp(current_expires_at, tz=dt.timezone.utc)
                if django_timezone.now() < expires_at:
                    time_remaining = (expires_at - django_timezone.now()).seconds
                    print(f"OTP still valid, {time_remaining} seconds remaining")
                    return JsonResponse({'success': False, 'message': f"Please wait {time_remaining} seconds before requesting a new OTP."})
            except ValueError:
                print("Invalid OTP expiration format in resend_otp")
                pass

        new_otp = generate_otp()
        new_expires_at = django_timezone.now() + timedelta(minutes=1)
        request.session[otp_key] = new_otp
        request.session[expires_at_key] = int(new_expires_at.timestamp())
        request.session.modified = True
        print(f"Resend OTP session ({'Password Reset' if is_password_reset else 'Registration'}):", request.session.items())

        purpose = "Password Reset" if is_password_reset else "Registration"
        if send_otp_email(email, new_otp, purpose=purpose):
            print(f"New OTP sent successfully for {purpose}")
            return JsonResponse({'success': True, 'message': f'New OTP sent successfully for {purpose}!'})
        else:
            print(f"Failed to send new OTP for {purpose}")
            return JsonResponse({'success': False, 'message': f'Failed to send OTP for {purpose}. Please try again.'})

    return JsonResponse({'success': False, 'message': 'Invalid request.'})





def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email').strip()
        try:
            user = User.objects.get(email=email)
            otp = generate_otp()
            expires_at = django_timezone.now() + timedelta(minutes=1)
            for key in ['email', 'reset_email', 'reg_otp', 'reg_otp_expires_at', 'otp', 'otp_expires_at', 'is_password_reset', 'username', 'password', 'first_name', 'last_name', 'referral_code']:
                request.session.pop(key, None)
            request.session['reset_email'] = email
            request.session['otp'] = otp
            request.session['otp_expires_at'] = int(expires_at.timestamp())
            request.session['is_password_reset'] = True
            request.session.modified = True
            print("Session data (forgot_password):", request.session.items())
            if send_otp_email(email, otp, purpose="Password Reset"):
                messages.success(request, 'OTP sent to your email. Please verify.')
                return redirect('verify_otp')
            else:
                messages.error(request, 'Failed to send OTP email. Please try again.')
        except User.DoesNotExist:
            print(f"No user found with email: {email}")
            messages.error(request, 'No user found with this email.')
    return render(request, 'forgott.html')





def reset_password(request):
    if request.method == 'POST':
        email = request.session.get('reset_email')
        if not email:
            messages.error(request, 'Session expired. Please start over.')
            return redirect('forgot_password')
        password = request.POST.get('new_password').strip()
        confirm_password = request.POST.get('confirm_password').strip()
        is_valid, error_message = validate_password(password)
        if not is_valid:
            messages.error(request, error_message)
        elif password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        else:
            try:
                user = User.objects.get(email=email)
                user.set_password(password)
                user.save()
                for key in ['reset_email', 'otp', 'otp_expires_at', 'is_password_reset']:
                    request.session.pop(key, None)
                request.session.modified = True
                messages.success(request, 'Password reset successfully. Please login.')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
        return render(request, 'reset.html')
    return render(request, 'reset.html')





@login_required
def referral_dashboard(request):
    user_profile = request.user.profile
   
    referral_coupons = Coupon.objects.filter(
        user=request.user,  
        is_active=True,
        valid_until__gt=django_timezone.now(),
    ).exclude(
        id__in=CouponUsage.objects.values('coupon_id')
    )
    context = {
        'referral_code': user_profile.referral_code,
        'referrals': user_profile.referrals.count(),
        'coupons': referral_coupons,
    }
    return render(request, 'referral_dashboard.html', context)