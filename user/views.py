# user/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.utils import IntegrityError
from user.models import User, PublicUserProfile
from user.forms import PublicUserForm, PublicUserProfileForm

def create_public_user(request):
    user_form = PublicUserForm(request.POST or None)
    profile_form = PublicUserProfileForm(request.POST or None)

    if request.method == 'POST':
        if user_form.is_valid() and profile_form.is_valid():
            try:
                password = user_form.cleaned_data['password']
                user_instance = user_form.save(commit=False)
                user_instance.set_password(password)
                user_instance.user_type = 'PUBLIC'
                user_instance.is_active = True
                user_instance.date_joined = timezone.now()
                user_instance.save()  # Username will be set inside model's save()

                profile_instance = profile_form.save(commit=False)
                profile_instance.user = user_instance
                profile_instance.save()

                messages.success(request, f"Public user with ID '{user_instance.username}' created successfully.")
                return redirect('public_user:view_public_users')

            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

    return render(request, 'user/create_public_user.html', {
        'user': user_form,
        'user_profile': profile_form
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
