from django.shortcuts import render
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Prefetch
from django.http import HttpResponseForbidden
from django.urls import reverse
from datetime import datetime
from django.contrib import messages
from user.models import User
from django.db.models import Prefetch
from grievance_app.models import Grievance
from officer.models import OfficerProfile,GrievanceAssignment,GrievanceStatusLog
from core_app.models import Department

def is_hod(user):
    # Check if the user is a HOD (head of department)
    return hasattr(user, 'officerprofile') and user.officerprofile.is_hod

@login_required
# @user_passes_test(is_hod)
def assign_grievance(request):
    """
    1. Assign grievance to officers under HOD's department.
    """
    user = request.user  # Get the currently logged-in user
    profile = OfficerProfile.objects.get(user=user)  # Get the OfficerProfile for the logged-in user
    hod_department = profile.department  # Get the department of the HOD
    print(hod_department)

    # Get grievances that belong to HOD's dept and are pending unassigned or assignable
    unassigned_grievances = Grievance.objects.filter(
        department=hod_department
    ).exclude(
        id__in=GrievanceAssignment.objects.values_list('grievance_id', flat=True)  # Exclude grievances that have assignments
    )

    # Officers in the HOD department (non-HOD)
    officers = OfficerProfile.objects.filter(department=hod_department, is_hod=False, user__is_active=True)

    if request.method == "POST":
        grievance_id = request.POST.get('grievance_id')
        officer_id = request.POST.get('officer_id')

        # Get the grievance and officer instances
        grievance = get_object_or_404(unassigned_grievances, id=grievance_id)
        officer = get_object_or_404(officers, id=officer_id)  # Use id to get the OfficerProfile instance

        print(officer)
        print(officer.user)  # This prints the associated User instance
        existing_assignment = GrievanceAssignment.objects.filter(grievance=grievance).first()
        if existing_assignment:
            messages.warning(request, "This grievance is already assigned.")
        else:
            GrievanceAssignment.objects.create(
            grievance=grievance,
            officer=officer,
            assigned_by=user
        )

        # Create or update assignment
        #assignment, created = GrievanceAssignment.objects.update_or_create(
            #grievance=grievance,
            #defaults={
             #   'officer': officer,  # Assign the OfficerProfile instance
              #  'assigned_by': user  # Use the User instance directly
            #}
        #)

        # Optionally update grievance status to assigned or in progress
        #grievance.status = 'In Progress'  # Update the status if needed
        grievance.save()
        #Send a assigning successful message to hod
        context = {
        'unassigned_grievances': unassigned_grievances,
        'officers': officers,
        }
        # Redirect or render the response
        return render(request, 'hod/assign_grievance.html', context)
    context = {
        'unassigned_grievances': unassigned_grievances,
        'officers': officers,
        }
        # 
    
    return render(request, 'hod/assign_grievance.html', context)

@login_required
# @user_passes_test(is_hod)
def check_grievance_progress(request):
    """
    2. Check progress of each grievance under HOD's department
    """
    user = request.user  # Get the currently logged-in user
    profile = OfficerProfile.objects.get(user=user)  # Get the OfficerProfile for the logged-in user
    hod_department = profile.department 

    # Get all grievances in this department
    grievances = Grievance.objects.filter(department=hod_department).order_by('-last_updated')
    officers = OfficerProfile.objects.filter(department=hod_department, is_hod=False, user__is_active=True)

    context = {
        'grievances': grievances,
    }
    return render(request, 'hod/check_progress.html', context)

@login_required
# @user_passes_test(is_hod)
def verify_officer_actions(request, grievance_id):
    """
    3. Verification of each action taken by officers on a grievance. Show action logs
    """
    hod_profile = request.user.officerprofile
    hod_department = hod_profile.department

    grievance = get_object_or_404(Grievance, id=grievance_id, department=hod_department)

    # Get grievance status logs (actions) related to this grievance
    action_logs = GrievanceStatusLog.objects.filter(grievance=grievance).order_by('timestamp')

    context = {
        'grievance': grievance,
        'action_logs': action_logs,
    }
    return render(request, 'hod/verify_actions.html', context)

@login_required
# @user_passes_test(is_hod)
def approve_date_extension_requests(request):
    """
    4. Approval of date extension requests made by each officer.
    Assume grievances have a related field or model for date extension requests (e.g. a boolean or a separate model).
    Here we mock with a "is_extension_requested" boolean and "extension_requested_date" fields.
    """
    hod_profile = request.user.officerprofile
    hod_department = hod_profile.department

    # Grievances that have requested date extension and belong to department
    extension_requests = Grievance.objects.filter(
        department=hod_department,
        is_extension_requested=True,
        extension_approved=False
    ).order_by('due_date')

    if request.method == "POST":
        grievance_id = request.POST.get('grievance_id')
        action = request.POST.get('action')  # approve or deny

        grievance = get_object_or_404(extension_requests, id=grievance_id)

        if action == 'approve':
            grievance.due_date = grievance.extension_requested_date
            grievance.extension_approved = True
            grievance.is_extension_requested = False
            grievance.save()
        elif action == 'deny':
            grievance.is_extension_requested = False
            grievance.save()

        return redirect('hod:approve_extension_requests')

    context = {
        'extension_requests': extension_requests,
    }
    return render(request, 'hod/approve_requests.html', context)

@login_required
# @user_passes_test(is_hod)
def search_grievance(request):
    """
    5. Search to show each grievance by various criteria under HOD's department
    """
    hod_profile = request.user.officerprofile
    hod_department = hod_profile.department

    query = request.GET.get('q', '').strip()

    grievances = Grievance.objects.filter(department=hod_department)

    if query:
        grievances = grievances.filter(
            Q(grievance_id__icontains=query)
            | Q(subject__icontains=query)
            | Q(description__icontains=query)
            | Q(applicant_name__icontains=query)
            | Q(status__icontains=query)
            | Q(priority__icontains=query)
        )

    context = {
        'grievances': grievances.order_by('-date_filed'),
        'query': query,
    }
    return render(request, 'hod/search_grievance.html', context)



@login_required
def officers_assigned_grievances(request):
    hod_profile = request.user.officerprofile
    hod_department = hod_profile.department

    grievance_logs_prefetch = Prefetch(
        'grievance__officer_status_logs',
        queryset=GrievanceStatusLog.objects.select_related('officer', 'officer__user').order_by('-timestamp'),
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
    return render(request, 'hod/officers_assigned_grievances.html', context)


@login_required
def hod_dashboard(request):
    user = request.user
    print(f"HOD Dashboard accessed by: {user.first_name}")
    print(f"HOD Dashboard accessed by: {user.username}, Is HOD: {is_hod(user)}")
    try:
        # Get the HOD's profile
        profile = OfficerProfile.objects.get(user=user)
        
        # Fetch relevant data for the HOD
        grievances = Grievance.objects.filter(department=profile.department)  # Grievances linked to the HOD's department
        officers = OfficerProfile.objects.filter(department=profile.department)  # Officers in the same department
        context = {
            'profile': profile,
            'grievances': grievances,
            'officers': officers,
        }
        return render(request, 'hod/hod_dashboard.html', context)

    except OfficerProfile.DoesNotExist:
        messages.error(request, "HOD profile not found.")
        print(f"Officer profile not found")
        return redirect('accounts:login')

# Create your views here.
