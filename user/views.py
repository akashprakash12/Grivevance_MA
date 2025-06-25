# user/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.utils import IntegrityError
from django.contrib.auth.decorators import login_required
from user.models import User, PublicUserProfile
from user.forms import PublicUserForm, PublicUserProfileForm
from grievance_app.forms import GrievanceForm
from grievance_app.models import Grievance

def create_public_user(request):
    return render(request, 'user/user_dashboard.html')


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
    # Get all grievances from the database
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


def account_settings(request):
    if request.user.is_authenticated:
        user_profile = PublicUserProfile.objects.get(user=request.user)
        return render(request, 'user/account_settings.html', {'user_profile': user_profile})
    else:
        return redirect('login')
