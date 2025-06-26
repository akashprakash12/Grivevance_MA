from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.conf import settings
import random
import string
from .models import DistrictOfficerProfile
from user.models import User
from core_app.models import District
from .forms import DOCreateUserForm,DOUpdateUserForm,DistrictOfficerProfileForm
from .utils import generate_do_id
from django.contrib.auth.decorators import login_required
from django.utils.crypto import get_random_string
from collector.models import CollectorProfile
from django.db.models import Q
from django.core.paginator import Paginator
from .utils import DistrictOfficerIDTracker
@login_required
def create_district_officer(request):
    # Get collector's district if user is a collector
    collector_district = None
    if hasattr(request.user, 'collector_profile'):
        collector_district = request.user.collector_profile.district

    user_form = DOCreateUserForm(request.POST or None)
    
    if request.method == "POST":
        if user_form.is_valid():
            try:
                collector = request.user
                collector_profile = CollectorProfile.objects.filter(user=collector).first()

                if not collector_profile or not collector_profile.district:
                    messages.error(request, "District information is missing. Please contact admin.")
                    return redirect('/district_officer/view/')

                district = collector_profile.district

                # ✅ Generate officer_id
                username = generate_do_id(district)

                
                # Generate secure password
                password = get_random_string(length=12)
                
                # Create user
                user = user_form.save(commit=False)
                user.username = username
                user.set_password(password)
                user.user_type = "DIST_OFFICER"
                user.is_active = True
                user.date_joined = timezone.now()
                user.save()
                
                # Create profile
                DistrictOfficerProfile.objects.create(
                    user=user,
                    officer_id=username,
                    district=district,
                    is_active=True
                )
                
                # Add to District Officer group if exists
                try:
                    group = Group.objects.get(name='district_officers')
                    user.groups.add(group)
                except Group.DoesNotExist:
                    pass
                
                # Send credentials email
                try:
                    send_mail(
                        subject=f"District Officer Account Created - {username}",
                        message=f"""Hello {user.first_name or 'District Officer'},

Your account has been created with the following details:

Username: {username}
Temporary Password: {password}

Please log in immediately at {settings.LOGIN_URL} and:
1. Change your password
2. Update your profile details

District: {district.name}

This is an automated message. Please do not reply.""",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],  # Using the email from the form
                        fail_silently=False,
                    )
                    messages.success(request, f"District Officer {username} created successfully. Credentials sent to {user.email}.")
                except Exception as e:
                    messages.error(request, f"Officer created but failed to send email: {str(e)}")
                    messages.warning(request, f"Please manually provide these credentials to the officer: Username: {username}, Temp Password: {password}")
                
                return redirect('district_officer:view_district_officers')
                
            except Exception as e:
                messages.error(request, f"Error creating District Officer: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    
    context = {
        'user_form': user_form,
        'is_collector': collector_district is not None,
        'collector_district': collector_district
    }
    
    return render(request, 'collector/create_do.html', context)
@login_required
def view_district_officers(request):
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')
    
    officers = DistrictOfficerProfile.objects.select_related('user', 'district').order_by('-is_active', 'user__last_name')
    
    # Apply filters
    if search_query:
        officers = officers.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(officer_id__icontains=search_query) |
            Q(district__name__icontains=search_query)
        )
    
    if status_filter != 'all':
        officers = officers.filter(is_active=(status_filter == 'active'))
    
    # Pagination
    paginator = Paginator(officers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'officers': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'is_paginated': paginator.num_pages > 1
    }
    
    template = 'collector/list_do.html'
    if request.user.user_type == "ADMIN" or request.user.is_superuser:
        template = 'collector/list_do.html'
        
    return render(request, template, context)

@login_required
def update_district_officer(request, officer_id):
    officer = get_object_or_404(DistrictOfficerProfile, officer_id=officer_id)
    user_obj = officer.user

    user_form = DOUpdateUserForm(request.POST or None, instance=user_obj)
    profile_form = DistrictOfficerProfileForm(
        request.POST or None, 
        instance=officer, 
        request=request
    )

    if request.method == "POST":
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, f"{officer.officer_id} updated successfully.")
            return redirect("district_officer:view_district_officers")

        messages.error(request, "Please correct the errors below.")

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "officer": officer
    }
    
    template = 'district_officer/edit.html'
    if request.user.user_type == "ADMIN" or request.user.is_superuser:
        template = 'district_officer/admin_edit.html'
        
    return render(request, template, context)

@login_required
def delete_district_officer(request, officer_id):
    officer = get_object_or_404(DistrictOfficerProfile, officer_id=officer_id)

    if request.method == "POST":
        username = officer.officer_id
        officer.user.delete()
        messages.success(request, f"{username} deleted successfully.")
        return redirect("district_officer:view_district_officers")

    context = {"officer": officer}
    
    template = 'district_officer/confirm_delete.html'
    if request.user.user_type == "ADMIN" or request.user.is_superuser:
        template = 'district_officer/admin_confirm_delete.html'
        
    return render(request, template, context)