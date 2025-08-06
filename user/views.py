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
from django.urls import reverse
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE_DIR, 'static/data', 'Districtdataset.json'), encoding='utf-8') as f:
    json_data = json.load(f)
    district_data = json_data['data'][1:]  # Skip the header row

# Extract Unique Districts and Taluks Dynamically
def get_districts(request):
    districts = sorted(set(row[2] for row in district_data))
    return JsonResponse({'districts': districts})

def get_taluks(request, district_name):
    taluks = sorted(set(row[4] for row in district_data if row[2] == district_name))
    return JsonResponse({'taluks': taluks})

def get_villages(request, taluk_name):
    villages = sorted(set(row[6] for row in district_data if row[4] == taluk_name))
    return JsonResponse({'villages': villages})

def create_public_user(request):
    if request.method == 'POST':
        user_form = PublicUserForm(request.POST)
        profile_form = PublicUserProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            try:
                password = user_form.cleaned_data['password']
                user = user_form.save(commit=False)
                user.set_password(password)
                user.user_type = 'PUBLIC'
                user.is_active = True
                user.date_joined = timezone.now()
                user.save()

                profile = profile_form.save(commit=False)
                profile.user = user
                profile.save()

                messages.success(request, f"Public user '{user.username}' created successfully.")
                return redirect('public_user:user_dashboard')
            except Exception as e:
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

def delete_public_user_by_public(request):
    user=request.user
    user.is_active=False
    user.save()
    messages.success(request, "Public user deleted successfully.")
    return redirect('accounts:login')

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
    user = request.user
    
    # Get or create user profile
    profile, created = PublicUserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        # Handle profile update
        if 'update_profile' in request.POST:
            user_form = PublicUserForm(request.POST, instance=user)
            profile_form = PublicUserProfileForm(request.POST, instance=profile)
            
            if user_form.is_valid() and profile_form.is_valid():
                try:
                    user_form.save()
                    profile_form.save()
                    messages.success(request, "Profile updated successfully!")
                    return redirect(reverse('public_user:account_settings') + '#profile')
                except Exception as e:
                    messages.error(request, f"Error updating profile: {str(e)}")

        # Handle password change
        elif 'change_password' in request.POST:
            current_password = request.POST.get('current_password', '').strip()
            new_password = request.POST.get('new_password', '').strip()
            confirm_password = request.POST.get('confirm_new_password', '').strip()
            
            # Validate inputs
            if not all([current_password, new_password, confirm_password]):
                messages.error(request, "All password fields are required.")
            elif not user.check_password(current_password):
                messages.error(request, "Your current password is incorrect.")
            elif new_password != confirm_password:
                messages.error(request, "New passwords don't match.")
            elif current_password == new_password:
                messages.error(request, "New password must be different from current password.")
            else:
                try:
                    validate_password(new_password, user)
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)  # Important to keep user logged in
                    messages.success(request, "Password changed successfully!")
                    return redirect(reverse('public_user:account_settings') + '#security')
                except ValidationError as e:
                    for error in e.messages:
                        messages.error(request, error)
                except Exception as e:
                    messages.error(request, f"Error changing password: {str(e)}")

    # Initialize forms
    user_form = PublicUserForm(instance=user)
    profile_form = PublicUserProfileForm(instance=profile)
    
    # Remove password fields if they exist
    for field in ['password', 'confirm_password']:
        if field in user_form.fields:
            user_form.fields.pop(field)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'user': user,
        'user_profile': profile,
        'active_tab': request.GET.get('tab', 'profile')
    }
    
    return render(request, 'user/account_settings.html', context)