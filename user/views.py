# user/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.utils import IntegrityError
from user.models import User, PublicUserProfile
from user.forms import PublicUserForm, PublicUserProfileForm
# user/views.py
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from .forms import PublicUserForm, PublicUserProfileForm
from grievance_app.forms import GrievanceForm



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
def submit_complaint(request):
    if request.method == 'POST':
        form = GrievanceForm(request.POST, request.FILES)
        if form.is_valid():
            grievance = form.save(commit=False)
            grievance.source = 'WEB'  # Website source
            grievance.status = 'PENDING'
            grievance.priority = 'MEDIUM'
            
            # If user is logged in, associate with user
            if request.user.is_authenticated:
                grievance.user = request.user
                grievance.applicant_name = request.user.get_full_name()
                grievance.email = request.user.email
            
            grievance.save()
            messages.success(request, "Your complaint has been submitted successfully!")
            return redirect('public_user:user_dashboard')  # Redirect to dashboard
            
    else:
        # Pre-fill user data if logged in
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'applicant_name': request.user.get_full_name(),
                'email': request.user.email,
                # Add other fields from user profile if available
            }
        form = GrievanceForm(request.POST or None)


    
    return render(request, 'user/complaint_submission.html', {'form': form})
    
    # OR if you need public_users data:
    # public_users = PublicUserProfile.objects.select_related('user')
    # return render(request, 'user/complaint_submission.html', {'public_users': public_users})

def help(request):
    # If you don't need public_users data in the template:
    return render(request, 'user/help_system.html')
    
    # OR if you need public_users data:
    # public_users = PublicUserProfile.objects.select_related('user')
    # return render(request, 'user/help_system.html', {'public_users': public_users})

def account_settings(request):
    # For account settings, you probably want the current user's data
    if request.user.is_authenticated:
        user_profile = PublicUserProfile.objects.get(user=request.user)
        return render(request, 'user/account_settings.html', {'user_profile': user_profile})
    else:
        return redirect('login')  # or handle unauthenticated users appropriately