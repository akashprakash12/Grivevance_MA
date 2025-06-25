from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import timedelta
import random
from django.contrib.auth.decorators import login_required
from .forms import GrievanceForm
from .models import Grievance, GrievanceDocument
from django.http import JsonResponse
from core_app.models import Department
from django.urls import reverse

# ---------- Generate Unique Grievance ID ----------

def auto_grievance_id():
    today_str = timezone.now().strftime('%Y%m%d')
    while True:
        random_number = random.randint(1000, 9999)
        grievance_id = f"GRI{today_str}{random_number}"
        if not Grievance.objects.filter(grievance_id=grievance_id).exists():
            return grievance_id

@login_required
def create_grievance(request):
    if request.method == 'POST':
        form = GrievanceForm(request.POST, request.FILES)
        if form.is_valid():
            grievance = form.save(commit=False)
            grievance.created_by = request.user
            grievance.grievance_id = auto_grievance_id()
            grievance.source = 'WEB'
            grievance.status = 'PENDING'
            grievance.created_by = request.user
            grievance.save()

            # Handle file uploads
            for file in request.FILES.getlist('documents'):
                GrievanceDocument.objects.create(grievance=grievance, file=file)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'grievance_id': grievance.grievance_id,
                    'redirect_url': reverse('public_user:user_dashboard')
                })
            return redirect('public_user:user_dashboard')
        
        # Return detailed errors for AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': {f: [str(e) for e in errors] for f, errors in form.errors.items()}
            }, status=400)
        
        return render(request, 'user/complaint_submission.html', {'form': form})
    
    # GET request
    form = GrievanceForm()
    return render(request, 'user/complaint_submission.html', {'form': form})

# AJAX view
def load_departments(request):
    district_code = request.GET.get('district')
    print(f"Received district code: {district_code}")  # Debugging
    
    if not district_code:
        print("No district code provided")
        return JsonResponse([], safe=False)
    
    try:
        departments = Department.objects.filter(district__code=district_code).values('code', 'name')
        print(f"Found departments: {list(departments)}")  # Debugging
        return JsonResponse(list(departments), safe=False)
    except Exception as e:
        print(f"Error: {str(e)}")  # Debugging
        return JsonResponse({'error': str(e)}, status=400)
# ---------- READ (List) ----------
# views.py (updated view_grievances function)
@login_required
def view_grievances(request):
    # Get only grievances submitted by the current user
    grievances = Grievance.objects.filter(created_by=request.user).order_by('-date_filed')

    # Prepare status counts for the stats cards
    status_counts = {
        'total': grievances.count(),
        'pending': grievances.filter(status='PENDING').count(),
        'in_progress': grievances.filter(status='IN_PROGRESS').count(),
        'resolved': grievances.filter(status='RESOLVED').count(),
        'rejected': grievances.filter(status='REJECTED').count(),
    }
    
    return render(request, 'user/view_grievances.html', {
        'grievances': grievances,
        'status_counts': status_counts
    })
# ---------- READ (Detail) ----------
def detail_grievance(request, grievance_id):
    grievance = get_object_or_404(Grievance, grievance_id=grievance_id)
    documents = grievance.documents.all()
    
    return JsonResponse({
        'grievance_id': grievance.grievance_id,
        'subject': grievance.subject,
        'description': grievance.description,
        'status': grievance.get_status_display(),
        'date_filed': grievance.date_filed.strftime("%d %b %Y"),
        'last_updated': grievance.last_updated.strftime("%d %b %Y"),
        'department': grievance.department.name,
        'district': grievance.district.name,
        'documents': [
            {
                'name': doc.file.name.split('/')[-1],
                'url': doc.file.url,
                'type': doc.file.name.split('.')[-1].lower()
            } for doc in documents
        ],
        'applicant_name': grievance.applicant_name,
        'contact_number': grievance.contact_number,
        'email': grievance.email,
        'applicant_address': grievance.applicant_address
    })
# ---------- UPDATE ----------
def update_grievance(request, grievance_id):
    grievance = get_object_or_404(Grievance, grievance_id=grievance_id)
    form = GrievanceForm(request.POST or None, instance=grievance)
    if request.method == 'POST' and form.is_valid():
        updated_grievance = form.save(commit=False)
        updated_grievance.last_update = timezone.now()
        updated_grievance.save()
        return redirect('grievance_list')
    return render(request, 'grievance/update_grievance.html', {'form': form, 'grievance': grievance})


# ---------- DELETE ----------
def delete_grievance(request, grievance_id):
    grievance = get_object_or_404(Grievance, grievance_id=grievance_id)
    if request.method == 'POST':
        grievance.delete()
        return redirect('grievance_list')
    return render(request, 'grievance/delete_grievance.html', {'grievance': grievance})



