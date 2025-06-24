from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# Forms and models
from .forms import LoginForm
from grievance_app.models import Grievance
from core_app.models import Department, District

from collector.models import CollectorProfile
from officer.models import OfficerProfile
from user.models import User
from django.contrib.auth import update_session_auth_hash


# -------------------------------
# Login View (first‑time redirect)
# -------------------------------
def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                # Check if user is inactive in User model
                if not user.is_active:
                    messages.error(request, "Your account is inactive.")
                    return redirect('accounts:login')

                # Additional check for collectors
                if user.user_type == 'COLLECTOR':
                    try:
                        collector_profile = CollectorProfile.objects.get(user=user)
                        if not collector_profile.is_active:
                            messages.error(request, "Your collector account has been deactivated.")
                            return redirect('accounts:login')
                    except CollectorProfile.DoesNotExist:
                        messages.error(request, "Collector profile not found.")
                        return redirect('accounts:login')

                # === first‑time logic ===
                groups = set(user.groups.values_list('name', flat=True))
                first_login_roles = {'collector', 'district_officer'}
                is_first_login = (user.last_login is None)

                if first_login_roles & groups and is_first_login:
                    login(request, user)                       # create session
                    request.session['force_pwd_reset'] = True  # mark session only
                    return redirect('accounts:custom_reset_password')
                # ========================

                login(request, user)
                return redirect('accounts:dashboard')

            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})

# -------------------------------
# Logout View
# -------------------------------
def user_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('accounts:login')


# -------------------------------
# Common Dashboard
# -------------------------------

@login_required
def dashboard(request):
    user = request.user
    groups = list(user.groups.values_list('name', flat=True))  # Get user group(s)
    context = {}

    # === Admin Dashboard ===
    if 'admin' in groups:
        context.update({
            'departments': Department.objects.all(),
            'users': User.objects.all(),
        })
        return render(request, 'core_app/department_form.html', context)

    # === Collector Dashboard ===
    elif 'collector' in groups:
        try:
            # Instead of rendering here, redirect to dedicated view
            return redirect('collector:collector_dashboard')  # URL name should point to your collector_dashboard view
        except CollectorProfile.DoesNotExist:
            messages.error(request, "Collector profile not found.")
            return redirect('accounts:login')

    # === Officer Dashboard ===
    elif 'officer' in groups:
        try:
            profile = OfficerProfile.objects.get(user=user)
            context['department'] = profile.department
            context['is_hod'] = profile.is_hod

            if profile.is_hod:
                return render(request, 'officer/hod_dashboard.html', context)
            else:
                return render(request, 'officer/officer_dashboard.html', context)

        except OfficerProfile.DoesNotExist:
            messages.error(request, "Officer profile not found.")
            return redirect('accounts:login')

    # === Public User Dashboard ===
    elif 'public' in groups:
        return render(request, 'user/create_public_user.html', {'user': user})
    
    elif 'district_officer' in groups:
        return render(request, 'district_officer/district_officer_dashboard.html', {'user': user})

    # === Fallback (Invalid Group or No Group Assigned) ===
    messages.error(request, "Access denied. Invalid role.")
    return redirect('accounts:login')




# accounts/views.py


@login_required
def custom_reset_password(request):
    if request.method == 'POST':
        password1 = request.POST.get('password1', '').strip()
        password2 = request.POST.get('password2', '').strip()

        if not password1 or not password2:
            messages.error(request, "Please fill in all fields.")
        elif password1 != password2:
            messages.error(request, "Passwords do not match.")
        elif len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters.")
        else:
            # Change password
            user = request.user
            user.set_password(password1)
            user.save()

            # Optional: keep user logged in after password change
            update_session_auth_hash(request, user)

            messages.success(request, "Password changed successfully.")
            return redirect('accounts:login')

    return render(request, 'accounts/custom_reset_password.html')
