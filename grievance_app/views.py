from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import timedelta
import random

from .forms import GrievanceForm
from .models import Grievance


# ---------- Generate Unique Grievance ID ----------
def auto_grievance_id():
    today_str = timezone.now().strftime('%Y%m%d')
    while True:
        random_number = random.randint(1000, 9999)
        grievance_id = f"GRI{today_str}{random_number}"
        if not Grievance.objects.filter(grievance_id=grievance_id).exists():
            return grievance_id


# ---------- CREATE ----------
def create_grievance(request):
    form = GrievanceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        grievance = form.save(commit=False)
        grievance.grievance_id = auto_grievance_id()
        grievance.date_filed = timezone.now()
        grievance.last_update = timezone.now()
        grievance.source = 'Website'
        grievance.status = 'Pending'
        grievance.priority = 'Medium'
        grievance.due_date = timezone.now() + timedelta(days=30)
        grievance.save()
        return redirect('grievance_list')
    return render(request, 'grievance/create_grievance.html', {'form': form})


# ---------- READ (List) ----------
def view_grievances(request):
    grievances = Grievance.objects.all().order_by('-date_filed')
    return render(request, 'grievance/view_grievances.html', {'grievances': grievances})


# ---------- READ (Detail) ----------
def detail_grievance(request, grievance_id):
    grievance = get_object_or_404(Grievance, grievance_id=grievance_id)
    return render(request, 'grievance/detail_grievance.html', {'grievance': grievance})


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



