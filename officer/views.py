from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.utils import IntegrityError
from django.contrib.auth.models import Group
from user.models import User
from officer.models import OfficerProfile, OfficerIDTracker
from core_app.models import Department
from .forms import OfficerForm, OfficerProfileForm

def officer_auto_id(department_code):
    department = Department.objects.get(code=department_code)
    tracker, _ = OfficerIDTracker.objects.get_or_create(department=department)
    tracker.last_used += 1
    tracker.save()
    return f"{department.code}OFF{tracker.last_used:03d}"

def create_officer(request):
    user_form = OfficerForm(request.POST or None)
    profile_form = OfficerProfileForm(request.POST or None)

    if request.method == 'POST':
        if user_form.is_valid() and profile_form.is_valid():
            officer_dept = profile_form.cleaned_data['department']

            try:
                password = user_form.cleaned_data['password']
                user_instance = user_form.save(commit=False)
                user_instance.set_password(password)
                user_instance.user_type = 'OFFICER'
                user_instance.is_active = True
                user_instance.date_joined = timezone.now()
                user_instance.username = officer_auto_id(officer_dept.code)
                user_instance.save()

                profile_instance = profile_form.save(commit=False)
                profile_instance.user = user_instance
                profile_instance.save()

                group_name = 'officer_hod' if profile_instance.is_hod else 'officer'
                group = Group.objects.get(name=group_name)
                user_instance.groups.add(group)

                messages.success(request, f"Officer '{user_instance.username}' created successfully.")
                return redirect('officer:view_officers')

            except IntegrityError:
                profile_form.add_error('is_hod', 'This department already has a HOD.')
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

    return render(request, 'officer/create_officer.html', {
        'user': user_form,
        'user_profile': profile_form
    })

def view_officers(request):
    officers = OfficerProfile.objects.select_related('user', 'department')
    return render(request, 'officer/view_officer.html', {'officers': officers})

def delete_officer(request, username):
    user = get_object_or_404(User, username=username, user_type='OFFICER')
    user.delete()
    messages.success(request, "Officer deleted successfully.")
    return redirect('officer:view_officers')

def update_officer(request, username):
    user_instance = get_object_or_404(User, username=username, user_type='OFFICER')
    profile_instance = get_object_or_404(OfficerProfile, user=user_instance)

    user_form = OfficerForm(request.POST or None, instance=user_instance)
    profile_form = OfficerProfileForm(request.POST or None, instance=profile_instance)

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
                messages.success(request, f"Officer '{user.username}' updated successfully.")
                return redirect('officer:view_officers')
            except IntegrityError:
                profile_form.add_error('is_hod', 'Only one HOD allowed per department.')

    return render(request, 'officer/update_officer.html', {
        'user': user_form,
        'user_profile': profile_form
    })
