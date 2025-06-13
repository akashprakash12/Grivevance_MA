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


# -------------------------------
# Login View
# -------------------------------
def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user:
                if user.is_active:
                    login(request, user)
                    return redirect('accounts:dashboard')  # 🧭 Common dashboard route
                else:
                    messages.error(request, "Your account is inactive.")
            else:
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
        return render(request, 'admin_dashboard.html', context)

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
        return render(request, 'public_user/public_dashboard.html', {'user': user})

    # === Fallback (Invalid Group or No Group Assigned) ===
    messages.error(request, "Access denied. Invalid role.")
    return redirect('accounts:login')