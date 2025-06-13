from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError

from grievance_app.models import Department, District
from admin_app.models import IDTracker
from .forms import DeptForm, DistrictForm
from admin_app.utils import generate_custom_id

# Auto ID generators
def auto_dept_id():
    return generate_custom_id(prefix="D", tracker_name="Department", digits=4)

# # Admin Dashboard View
# def admin_dashboard(request):
#     departments = Department.objects.all()
#     districts = District.objects.all()
#     context = {
#         'departments': departments,
#         'districts': districts,
#     }
#     return render(request, 'admin_dashboard.html', context)

# ────────────────────────────── DEPARTMENT VIEWS ──────────────────────────────

def department_list(request):
    departments = Department.objects.all()
    return render(request, 'core_app/department_list.html', {'departments': departments})

def department_create(request):
    form = DeptForm(request.POST or None)
    if form.is_valid():
        department = form.save(commit=False)
        department.code = auto_dept_id()
        department.save()
        return redirect('core:department_list')  # Hardcoded
    return render(request, 'core_app/department_form.html', {'form': form})

def department_update(request, code):
    department = get_object_or_404(Department, code=code)
    form = DeptForm(request.POST or None, instance=department)
    if form.is_valid():
        form.save()
        return redirect('core:department_list')  # Hardcoded
    return render(request, 'core_app/department_form.html', {'form': form})

def department_delete(request, code):
    department = get_object_or_404(Department, code=code)
    if request.method == 'POST':
        department.delete()
        return redirect('core:department_list')  # Hardcoded
    return render(request, 'core_app/department_confirm_delete.html', {'department': department})

# ────────────────────────────── DISTRICT VIEWS ──────────────────────────────

def district_list(request):
    districts = District.objects.all()
    return render(request, 'core_app/district_list.html', {'districts': districts})

def district_create(request):
    form = DistrictForm(request.POST or None)
    if form.is_valid():
        district = form.save(commit=False)
        district.save()
        return redirect('core:district_list')
    return render(request, 'core_app/district_form.html', {'form': form})

def district_update(request, code):
    district = get_object_or_404(District, code=code)
    form = DistrictForm(request.POST or None, instance=district)
    if form.is_valid():
        form.save()
        return redirect('core:department_list')  # Hardcoded
    return render(request, 'core_app/district_form.html', {'form': form})

def district_delete(request, code):
    district = get_object_or_404(District, code=code)
    if request.method == 'POST':
        district.delete()
        return redirect('core:department_list')  # Hardcoded
    return render(request, 'core_app/district_confirm_delete.html', {'district': district})
