# user/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.utils import IntegrityError
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, update_session_auth_hash
from user.models import User, PublicUserProfile
from user.forms import PublicUserForm, PublicUserProfileForm
from grievance_app.forms import GrievanceForm
from grievance_app.models import Grievance
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.util import random_hex
import qrcode
import base64
from io import BytesIO
from django.urls import reverse
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

def create_public_user(request):
    if request.method == 'POST':
        user_form = PublicUserForm(request.POST)
        profile_form = PublicUserProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            try:
                user = user_form.save(commit=False)
                user.user_type = 'PUBLIC'
                user.save()
                profile = profile_form.save(commit=False)
                profile.user = user
                profile.save()
                messages.success(request, f"Public user '{user.username}' created successfully.")
                return redirect('public_user:user_dashboard')
            except IntegrityError as e:
                messages.error(request, f"Error: {str(e)}")
    else:
        user_form = PublicUserForm()
        profile_form = PublicUserProfileForm()
    
    return render(request, 'user/create_public_user.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

def view_public_users(request):
    public_users = PublicUserProfile.objects.select_related('user')
    return render(request, 'user/view_public_user.html', {'public_users': public_users})

def delete_public_user(request, username):
    user = get_object_or_404(User, username=username, user_type='PUBLIC')
    user.delete()
    messages.success(request, "Public user deleted successfully.")
    return redirect('public_user:view_public_users')

def update_public_user(request, username):
    user_instance = get_object_or_404(User, username=username, user_type='PUBLIC')
    profile_instance = get_object_or_404(PublicUserProfile, user=user_instance)

    user_form = PublicUserForm(request.POST or None, instance=user_instance)
    profile_form = PublicUserProfileForm(request.POST or None, instance=profile_instance)

    if request.method == 'POST':
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            new_password = user_form.cleaned_data['password']
            if new_password:
                user.set_password(new_password)
            else:
                user.password = user_instance.password
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user
            try:
                profile.save()
                messages.success(request, f"Public user '{user.username}' updated successfully.")
                return redirect('public_user:view_public_users')
            except IntegrityError as e:
                messages.error(request, f"Error: {str(e)}")

    return render(request, 'user/update_public_user.html', {
        'user': user_form,
        'user_profile': profile_form
    })

@login_required
def user_dashboard(request):
    grievances = Grievance.objects.all().order_by('-last_updated')
    status_counts = {
        'total': grievances.count(),
        'pending': grievances.filter(status='PENDING').count(),
        'in_progress': grievances.filter(status='IN_PROGRESS').count(),
        'resolved': grievances.filter(status='RESOLVED').count(),
        'rejected': grievances.filter(status='REJECTED').count(),
    }
    return render(request, 'user/user_dashboard.html', {
        'grievances': grievances,
        'status_counts': status_counts,
        'user': request.user
    })

def submit_complaint(request):
    form = GrievanceForm()
    return render(request, 'user/complaint_submission.html', {'form': form})

def help(request):
    return render(request, 'user/help_system.html')

@login_required
def account_settings(request):
    # First check 2FA verification if enabled
    if request.user.has_2fa_enabled() and not request.session.get('2fa_verified', False):
        request.session['next_url'] = reverse('public_user:account_settings')
        return redirect(reverse('public_user:verify_2fa'))

    user = request.user
    try:
        profile = user.public_profile
    except PublicUserProfile.DoesNotExist:
        profile = PublicUserProfile.objects.create(user=user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            user_form = PublicUserForm(request.POST, instance=user)
            profile_form = PublicUserProfileForm(request.POST, instance=profile)
            
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect(reverse('public_user:account_settings') + '#profile')
        
        elif 'change_password' in request.POST:
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_new_password')
            
            if not user.check_password(current_password):
                messages.error(request, "Your current password is incorrect.")
            elif new_password != confirm_password:
                messages.error(request, "New passwords don't match.")
            else:
                try:
                    validate_password(new_password, user)
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, "Password changed successfully!")
                    return redirect(reverse('public_user:account_settings') + '#security')
                except ValidationError as e:
                    for error in e.messages:
                        messages.error(request, error)
        
        elif 'toggle_2fa' in request.POST:
            if user.has_2fa_enabled():
                # Disable 2FA
                TOTPDevice.objects.filter(user=user).delete()
                messages.success(request, "Two-factor authentication has been disabled.")
            else:
                # Enable 2FA - redirect to verification
                request.session['next_url'] = reverse('public_user:account_settings') + '#security'
                return redirect(reverse('public_user:verify_2fa'))
            
            return redirect(reverse('public_user:account_settings') + '#security')

    # Initialize forms
    user_form = PublicUserForm(instance=user)
    profile_form = PublicUserProfileForm(instance=profile)
    
    # Remove password fields if they exist
    if 'password' in user_form.fields:
        user_form.fields.pop('password')
    if 'confirm_password' in user_form.fields:
        user_form.fields.pop('confirm_password')
    
    # 2FA context
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'user': user,
        'user_profile': profile,
        'has_2fa_enabled': user.has_2fa_enabled(),
        'active_tab': request.GET.get('tab', 'profile')
    }
    
    # Generate QR code if requested
    if not context['has_2fa_enabled'] and 'generate_2fa' in request.GET:
        device = user.get_totp_device()
        if not device.confirmed:
            device.key = random_hex(20)
            device.save()
        
        # Generate QR code
        provisioning_uri = device.config_url
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        context.update({
            'qr_code': img_str,
            'provisioning_uri': provisioning_uri,
            'device': device,
            'active_tab': 'security'
        })
    
    return render(request, 'user/account_settings.html', context)

@login_required
def verify_2fa(request):
    if request.method == 'POST':
        token = request.POST.get('token')
        device = request.user.get_totp_device()
        
        if device and device.verify_token(token):
            device.confirmed = True
            device.save()
            request.session['2fa_verified'] = True  # Mark session as verified
            
            # Redirect to originally requested URL or default
            next_url = request.session.pop('next_url', reverse('public_user:account_settings'))
            messages.success(request, "Two-factor authentication verified!")
            return redirect(next_url)
        else:
            messages.error(request, "Invalid verification code. Please try again.")
    
    return render(request, 'user/verify_2fa.html', {
        'user': request.user,
        'next_url': request.GET.get('next', '')
    })

@login_required
def disable_2fa(request):
    if request.method == 'POST':
        device = request.user.totpdevice_set.filter(name='default').first()
        if device:
            device.delete()
            messages.success(request, "Two-factor authentication has been disabled.")
    
    return redirect('public_user:account_settings')