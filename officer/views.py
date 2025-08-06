from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.utils import IntegrityError
from django.contrib.auth.models import Group
from django.utils.crypto import get_random_string
from django.core.mail import send_mail

from user.models import User
from officer.models import OfficerProfile, OfficerIDTracker
from core_app.models import Department
from .forms import OfficerForm, OfficerAdminForm

# Generate unique officer username
def officer_auto_id(department_code):
    department = Department.objects.get(code=department_code)
    tracker, _ = OfficerIDTracker.objects.get_or_create(department=department)
    tracker.last_used += 1
    tracker.save()
    return f"{department.code}OFF{tracker.last_used:03d}"


# ✅ Collector: Create Officer (department auto-filled)
def create_officer_collector(request):
    collector_district = request.user.collector_profile.district
    officer_dept = Department.objects.filter(district=collector_district).first()
    
    if not officer_dept:
        messages.error(request, "No department found for your district.")
        return redirect('home')

    user_form = OfficerForm(request.POST or None)
    
    if request.method == 'POST' and user_form.is_valid():
        try:
            random_password = get_random_string(12)
            user_instance = user_form.save(commit=False)
            user_instance.set_password(random_password)
            user_instance.user_type = 'OFFICER'
            user_instance.is_active = True
            user_instance.date_joined = timezone.now()
            user_instance.username = officer_auto_id(officer_dept.code)
            user_instance.save()

            is_hod = bool(request.POST.get("is_hod"))
            OfficerProfile.objects.create(
                user=user_instance,
                department=officer_dept,
                is_hod=is_hod
            )

            group_name = 'officer_hod' if is_hod else 'officer'
            group = Group.objects.get(name=group_name)
            user_instance.groups.add(group)

            send_mail(
                subject="Your Officer Account Credentials",
                message=(
                    f"Hello {user_instance.first_name},\n\n"
                    f"Username: {user_instance.username}\n"
                    f"Password: {random_password}\n\n"
                    f"Please log in and change your password.\n\n"
                    f"Regards,\nCollector's Office"
                ),
                from_email=None,
                recipient_list=[user_instance.email],
                fail_silently=False,
            )

            messages.success(request, f"Officer '{user_instance.username}' created successfully.")
            return redirect('collector:department_card', department_id=officer_dept.code)

        except IntegrityError:
            messages.error(request, "This department already has a HOD.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return render(request, 'collector/create_officer_collector.html', {
        'form': user_form,
        'department': officer_dept
    })


# ✅ Admin: Create Officer
def create_officer_admin(request):
    if not request.user.groups.filter(name="admin").exists():
        messages.error(request, "Permission denied.")
        return redirect('home')

    user_form = OfficerAdminForm(request.POST or None)

    if request.method == 'POST' and user_form.is_valid():
        try:
            dept = user_form.cleaned_data["department"]
            random_password = get_random_string(12)
            user_instance = user_form.save(commit=False)
            user_instance.set_password(random_password)
            user_instance.user_type = 'OFFICER'
            user_instance.is_active = True
            user_instance.date_joined = timezone.now()
            user_instance.username = officer_auto_id(dept.code)
            user_instance.save()

            is_hod = bool(request.POST.get("is_hod"))
            OfficerProfile.objects.create(
                user=user_instance,
                department=dept,
                is_hod=is_hod
            )

            group_name = 'officer_hod' if is_hod else 'officer'
            group = Group.objects.get(name=group_name)
            user_instance.groups.add(group)

            send_mail(
                subject="Your Officer Account Credentials",
                message=(
                    f"Hello {user_instance.first_name},\n\n"
                    f"Username: {user_instance.username}\n"
                    f"Password: {random_password}\n\n"
                    f"Please log in and change your password.\n\n"
                    f"Regards,\nAdmin"
                ),
                from_email=None,
                recipient_list=[user_instance.email],
                fail_silently=False,
            )

            messages.success(request, f"Officer '{user_instance.username}' created successfully.")
            return redirect('officer:view_officers_admin')

        except IntegrityError:
            messages.error(request, "This department already has a HOD.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return render(request, 'officer/create_officer_admin.html', {'form': user_form})


# ✅ Admin: Update Officer
def update_officer(request, username):
    if not request.user.groups.filter(name="admin").exists():
        messages.error(request, "Only administrators can update officers.")
        return redirect('home')

    user_instance = get_object_or_404(User, username=username, user_type='OFFICER')
    profile_instance = get_object_or_404(OfficerProfile, user=user_instance)

    form_class = OfficerAdminForm
    redirect_url = 'officer:view_officers_admin'
    template = 'officer/update_officer_admin.html'

    user_form = form_class(request.POST or None, instance=user_instance, initial={
        'department': profile_instance.department
    })

    if request.method == 'POST' and user_form.is_valid():
        try:
            user = user_form.save(commit=False)
            user.save()

            is_hod = bool(request.POST.get("is_hod"))
            profile_instance.is_hod = is_hod
            profile_instance.department = user_form.cleaned_data.get("department")
            profile_instance.save()

            group_name = 'officer_hod' if is_hod else 'officer'
            user.groups.clear()
            user.groups.add(Group.objects.get(name=group_name))

            send_mail(
                subject="Your Officer Profile has been updated",
                message=(
                    f"Dear {user.first_name},\n\n"
                    f"Your profile has been updated.\n"
                    f"Position: {'HOD' if is_hod else 'Officer'}\n"
                    f"Department: {profile_instance.department.name}\n"
                    f"Regards,\nAdmin"
                ),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False
            )

            messages.success(request, f"Officer '{user.username}' updated successfully.")
            return redirect(redirect_url)

        except IntegrityError:
            messages.error(request, 'Only one HOD allowed per department.')
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return render(request, template, {
        'form': user_form,
        'is_hod': profile_instance.is_hod,
        'officer': user_instance
    })


# ✅ Admin: Delete Officer
def delete_officer(request, username):
    if not request.user.groups.filter(name="admin").exists():
        messages.error(request, "Only administrators can delete officers.")
        return redirect('home')

    officer = get_object_or_404(User, username=username, user_type='OFFICER')
    officer.delete()
    messages.success(request, "Officer deleted successfully.")
    return redirect('officer:view_officers_admin')


# ✅ Admin: View All Officers
def view_officers_admin(request):
    if not request.user.groups.filter(name="admin").exists():
        messages.error(request, "Permission denied.")
        return redirect('home')

    officers = OfficerProfile.objects.select_related('user', 'department')
    return render(request, 'officer/view_officers_admin.html', {'officers': officers})


# ✅ Collector: View Officers from Own District Only
def view_officers_collector(request):
    collector_district = request.user.collector_profile.district
    officers = OfficerProfile.objects.filter(
        department__district=collector_district
    ).select_related('user', 'department')
    return render(request, 'officer/view_officers_collector.html', {'officers': officers})
