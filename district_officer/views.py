from pickle import TRUE
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.db import IntegrityError
from django.utils.crypto import get_random_string
from django.core.exceptions import PermissionDenied
from django.db import transaction  # Add this import at the top
import os
import random

from grievance_app.models import Grievance
from .models import DistrictOfficerProfile
from user.models import User
from core_app.models import Department, District
from .forms import DOCreateUserForm, DOUpdateUserForm, DistrictOfficerProfileForm
from .utils import generate_do_id
from collector.models import CollectorProfile
from collector.views import rank_departments, _is_collector,_is_DO

@login_required
def create_district_officer(request):
    collector_profile = getattr(request.user, "collector_profile", None)
    collector_district = getattr(collector_profile, "district", None)
    user_form = DOCreateUserForm(request.POST or None)

    if not collector_district:
        messages.error(request, "District information is missing. Please contact the administrator.")
        return redirect('district_officer:view_district_officers')

    if request.method == "POST":
        if user_form.is_valid():
            try:
                # Check for existing active officer
                if DistrictOfficerProfile.objects.filter(district=collector_district, is_active=True).exists():
                    messages.error(
                        request,
                        "An active District Officer is already assigned to this district. "
                        "Please deactivate the current officer before assigning a new one."
                    )
                    return redirect('district_officer:view_district_officers')

                with transaction.atomic():
                    username = generate_do_id(collector_district)
                    password = get_random_string(length=12)

                    user = user_form.save(commit=False)
                    user.username = username
                    user.set_password(password)
                    user.user_type = "district_officer"
                    user.is_active = True
                    user.date_joined = timezone.now()
                    user.save()

                    DistrictOfficerProfile.objects.create(
                        user=user,
                        officer_id=username,
                        district=collector_district,
                        is_active=True,
                        created_by=collector_profile
                    )

                    try:
                        group = Group.objects.get(name='district_officer')
                        user.groups.add(group)
                    except Group.DoesNotExist:
                        pass

                    try:
                        send_mail(
                            subject=f"District Officer Account Created - {collector_district.name}",
                            message=(
                                f"Dear {user.first_name or 'District Officer'},\n\n"
                                f"Your District Officer account has been created.\n\n"
                                f"Username: {username}\n"
                                f"Temporary Password: {password}\n\n"
                                f"Login: {request.build_absolute_uri(settings.LOGIN_URL)}\n"
                                f"Please change your password after logging in.\n\n"
                                f"District: {collector_district.name}\n\n"
                                f"This is an automated message."
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            fail_silently=False,
                        )
                        messages.success(request, f"Officer {username} created. Credentials sent to {user.email}.")
                    except Exception as e:
                        messages.warning(
                            request,
                            f"Officer created, but failed to send email: {str(e)}.\n"
                            f"Manual credentials: Username: {username}, Password: {password}"
                        )

                return redirect("district_officer:view_district_officers")

            except IntegrityError as e:
                messages.error(request, f"Error creating profile: {str(e)}")
                return redirect('district_officer:view_district_officers')

            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            # Show specific form errors
            for field, errors in user_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    return render(request, 'collector/create_do.html', {
        'user_form': user_form,
        'collector_district': collector_district
    })

@login_required
def view_district_officer_profile(request):
    collector_profile = getattr(request.user, "collector_profile", None)
    collector_district = getattr(collector_profile, "district", None)

    if not collector_district:
        messages.error(request, "District not assigned. Please contact admin.")
        return redirect("collector:collector_dashboard")

    try:
        district_officer = DistrictOfficerProfile.objects.select_related("user", "district").get(
            district=collector_district,
            is_active=True,
            user__is_active=True
        )
        context = {
            "district_officer": district_officer,
            "show_empty": False,
            "is_collector": True,
        }
    except DistrictOfficerProfile.DoesNotExist:
        context = {
            "show_empty": True,
            "is_collector": True,
            "collector_district": collector_district,
        }

    return render(request, "collector/do_profile_for_collector.html", context)

@login_required
@transaction.atomic
def update_district_officer(request, officer_id):
    officer = get_object_or_404(DistrictOfficerProfile, officer_id=officer_id)
    user_obj = officer.user

    # Determine user roles and permissions
    is_admin = request.user.is_superuser or request.user.user_type == "ADMIN"
    is_collector = _is_collector(request.user)
    is_do = _is_DO(request.user)
    
    # Get collector's district if collector
    collector_district = getattr(getattr(request.user, "collector_profile", None), "district", None) if is_collector else None
    
    # Check permissions
    can_edit = (
        is_admin or
        (is_collector and collector_district == officer.district) or
        (is_do and request.user == user_obj)  # DO can only edit themselves
    )
    
    if not can_edit:
        raise PermissionDenied("You are not authorized to update this profile.")

    if request.method == "POST":
        user_form = DOUpdateUserForm(request.POST, instance=user_obj)
        profile_form = DistrictOfficerProfileForm(request.POST, request.FILES, instance=officer, request=request)
        
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            
            # Preserve original active status (no one can change it)
            user.is_active = True
            user.save()

            profile = profile_form.save(commit=False)
            
            # Preserve original district and active status (no one can change these)
            profile.district = officer.district
            profile.is_active = True
            profile.save()

            messages.success(request, "Profile updated successfully.")
            
            # Determine redirect based on user type
            if is_collector:
                return redirect("district_officer:view_district_officers")
            elif is_do:
                return redirect("district_officer:DO_dashboard")
            else:  # admin
                return redirect("admin_app:admin_dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = DOUpdateUserForm(instance=user_obj)
        profile_form = DistrictOfficerProfileForm(instance=officer, request=request)

    # Select appropriate template
    if is_collector:
        template_name = "collector/update_do.html"
    elif is_do:
        template_name = "district_officer/update_do.html"  # Special template for DO self-edits
    else:
        template_name = "district_officer/update_do.html"  # Admin template

    return render(request, template_name, {
        "user_form": user_form,
        "profile_form": profile_form,
        "officer": officer,
        "is_self_edit": is_do,  # Flag for template to adjust UI
        "can_change_status": False,  # Explicitly tell template status can't be changed
    })



@login_required
def delete_district_officer(request, officer_id):
    officer = get_object_or_404(DistrictOfficerProfile, officer_id=officer_id)

    collector_district = getattr(getattr(request.user, "collector_profile", None), "district", None)
    is_admin = request.user.is_superuser or request.user.user_type == "ADMIN"
    is_collector = _is_collector(request.user) and collector_district == officer.district

    if not (is_admin or is_collector):
        raise PermissionDenied("You do not have permission to delete this officer.")

    if request.method == 'POST':
        officer.is_active = False
        officer.user.is_active = False
        officer.save()
        officer.user.save()

        messages.success(request, f"District Officer {officer.user.get_full_name()} has been deactivated.")
        return redirect("collector:collector_dashboard")

    # If GET request, redirect back to profile
    return redirect("district_officer:view_district_officers")

@login_required
def DO_dashboard(request):
    district = DistrictOfficerProfile.objects.select_related('user').get(user=request.user).district
    grievances = Grievance.objects.filter(district=district)
    total_all = grievances.count()
    pending_all = grievances.filter(status="PENDING").count()
    in_progress_all = grievances.filter(status="IN_PROGRESS").count()
    rejected_all = grievances.filter(status="REJECTED").count()
    escalated_all = grievances.filter(status="ESCALATED").count()
    resolved_all = total_all - pending_all - in_progress_all - rejected_all - escalated_all

    departments = (
        Department.objects
        .filter(district=district)
        .annotate(
            total=Count("grievance", filter=Q(grievance__district=district)),
            pending=Count("grievance", filter=Q(grievance__district=district, grievance__status="PENDING")),
            rejected=Count("grievance", filter=Q(grievance__district=district, grievance__status="REJECTED")),
        )
    )

    top3_departments = rank_departments(Department.objects.filter(district=district))
    district_name = district.name.lower()
    district_images_path = os.path.join(settings.STATICFILES_DIRS[0], 'images', district_name)
    district_images = []
    
    if os.path.exists(district_images_path):
        district_images = [
            f for f in os.listdir(district_images_path)
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
        ]
    dept_data = []
    for d in departments:
        total, pending, rejected = d.total, d.pending, d.rejected
        resolved = total - pending - rejected
        pending_pct = round((pending / total) * 100, 1) if total else 0
        rejected_pct = round((rejected / total) * 100, 1) if total else 0
        badge_class = (
            "danger" if pending_pct >= 75 else
            "warning" if pending_pct >= 25 else
            "success"
        )
        dept_data.append({
            "name": d.name,
            "code": d.code,
            "total": total,
            "pending": pending,
            "rejected": rejected,
            "resolved": resolved,
            "pending_percent": pending_pct,
            "rejected_percent": rejected_pct,
            "badge_class": badge_class,
        })

    context = {
        "counts": {
            "total": total_all,
            "pending": pending_all,
            "in_progress": in_progress_all,
            "resolved": resolved_all,
            "rejected": rejected_all,
            "escalated": escalated_all,
        },
        "district": district,
        "all_grievances": grievances,
        "departments": dept_data,
        "top3_departments": top3_departments,
        "district_images": district_images,

    }
    return render(request, "district_officer/district_officer_dashboard.html", context)
