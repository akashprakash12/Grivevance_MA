from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch
from django.contrib import messages
from grievance_app.models import Grievance
from officer.models import OfficerProfile, GrievanceAssignment, GrievanceStatusLog

@login_required
def update_hod(request, hod_id):
    hod = get_object_or_404(HOD, id=hod_id)
    # Handle form here (for now, just render a placeholder)
    return render(request, 'hod/update_hod.html', {'hod': hod})

@login_required
def delete_hod(request, hod_id):
    hod = get_object_or_404(HOD, id=hod_id)
    if request.method == "POST":
        hod.user.is_active = False
        hod.user.save()
        messages.success(request, "HOD account deactivated.")
        return redirect('hod:hod_profile')  # or wherever appropriate
    return redirect('hod:hod_profile')
    
def is_hod(user):
    return hasattr(user, 'officerprofile') and user.officerprofile.is_hod

@login_required
def hod_profile(request):
    user = request.user
    return render(request, 'hod/view_profile.html', {'user': user})

@login_required
def hod_dashboard(request):
    user = request.user
    try:
        profile = OfficerProfile.objects.get(user=user)
        grievances = Grievance.objects.filter(department=profile.department)
        officers = OfficerProfile.objects.filter(department=profile.department, is_hod=False)

        context = {
            'profile': profile,
            'grievances': grievances,
            'officers': officers,
        }
        return render(request, 'hod/hod_dashboard.html', context)

    except OfficerProfile.DoesNotExist:
        messages.error(request, "HOD profile not found.")
        return redirect('accounts:login')


@login_required
def assign_grievance(request):
    user = request.user
    profile = OfficerProfile.objects.get(user=user)
    hod_department = profile.department

    unassigned_grievances = Grievance.objects.filter(
        department=hod_department
    ).exclude(
        id__in=GrievanceAssignment.objects.values_list('grievance_id', flat=True)
    )

    officers = OfficerProfile.objects.filter(department=hod_department, is_hod=False, user__is_active=True)

    if request.method == "POST":
        grievance_id = request.POST.get('grievance_id')
        officer_id = request.POST.get('officer_id')

        grievance = get_object_or_404(unassigned_grievances, id=grievance_id)
        officer = get_object_or_404(officers, id=officer_id)

        existing_assignment = GrievanceAssignment.objects.filter(grievance=grievance).first()
        if existing_assignment:
            messages.warning(request, "This grievance is already assigned.")
        else:
            GrievanceAssignment.objects.create(
                grievance=grievance,
                officer=officer,
                assigned_by=user
            )
            grievance.save()

        return redirect('hod:assign_grievance')

    context = {
        'unassigned_grievances': unassigned_grievances,
        'officers': officers,
    }
    return render(request, 'hod/assign_grievance.html', context)


@login_required
def check_grievance_progress(request):
    user = request.user
    profile = OfficerProfile.objects.get(user=user)
    hod_department = profile.department

    grievances = Grievance.objects.filter(department=hod_department).order_by('-last_updated')

    context = {
        'grievances': grievances,
    }
    return render(request, 'hod/check_progress.html', context)


@login_required
def verify_officer_actions(request, grievance_id):
    hod_profile = request.user.officerprofile
    hod_department = hod_profile.department

    grievance = get_object_or_404(Grievance, id=grievance_id, department=hod_department)
    action_logs = GrievanceStatusLog.objects.filter(grievance=grievance).order_by('timestamp')

    context = {
        'grievance': grievance,
        'action_logs': action_logs,
    }
    return render(request, 'hod/verify_actions.html', context)


@login_required
def approve_date_extension_requests(request):
    hod_profile = request.user.officerprofile
    hod_department = hod_profile.department

    extension_requests = Grievance.objects.filter(
        department=hod_department,
        is_extension_requested=True,
        extension_approved=False
    ).order_by('due_date')

    if request.method == "POST":
        grievance_id = request.POST.get('grievance_id')
        action = request.POST.get('action')

        grievance = get_object_or_404(extension_requests, id=grievance_id)

        if action == 'approve':
            grievance.due_date = grievance.extension_requested_date
            grievance.extension_approved = True
            grievance.is_extension_requested = False
        elif action == 'deny':
            grievance.is_extension_requested = False
        grievance.save()

        return redirect('hod:approve_extension_requests')

    context = {
        'extension_requests': extension_requests,
    }
    return render(request, 'hod/approve_requests.html', context)


@login_required
def search_grievance(request):
    hod_profile = request.user.officerprofile
    hod_department = hod_profile.department

    query = request.GET.get('q', '').strip()

    # Default: All grievances in the HOD's department
    grievances = Grievance.objects.filter(department=hod_department)

    # If a query is entered, filter the results
    if query:
        grievances = grievances.filter(
            Q(grievance_id__icontains=query) |
            Q(subject__icontains=query) |
            Q(description__icontains=query) |
            Q(applicant_name__icontains=query) |
            Q(status__icontains=query) |
            Q(priority__icontains=query)
        )

    context = {
        'grievances': grievances.order_by('-date_filed'),
        'query': query,
    }
    return render(request, 'hod/search_grievances.html', context)


@login_required
def officers_assigned_grievances(request):
    hod_profile = request.user.officerprofile
    hod_department = hod_profile.department

    grievance_logs_prefetch = Prefetch(
        'grievance__grievancestatuslog_set',
        queryset=GrievanceStatusLog.objects.select_related('changed_by').order_by('-changed_at'),
        to_attr='status_logs'
    )

    assignments_prefetch = Prefetch(
        'grievanceassignment_set',
        queryset=GrievanceAssignment.objects.select_related('grievance')
            .prefetch_related(grievance_logs_prefetch)
            .order_by('-grievance__last_updated'),
        to_attr='assigned_grievances'
    )

    officers = OfficerProfile.objects.filter(
        department=hod_department,
        is_hod=False
    ).prefetch_related(assignments_prefetch)

    context = {
        'officers': officers,
    }
    return render(request, 'hod/officer_assigned_grievance.html', context)
