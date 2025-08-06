from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from grievance_app.models import Department, District
from collector.models import CollectorProfile
from .forms import DeptForm, DistrictForm
from admin_app.utils import generate_custom_id

DEBUG_PRINT = False  # set True if you want console logs

def auto_dept_id() -> str:
    """Return next department code, e.g. D0008."""
    return generate_custom_id(prefix="D", tracker_name="Department", digits=4)


def _is_collector(user) -> bool:
    """Safe role check—works regardless of `related_name`."""
    return CollectorProfile.objects.filter(user=user).exists()


# ───────────── department views ─────────────
@login_required
def department_list(request):
    depts = Department.objects.all()
    return render(request, "core_app/department_list.html", {"departments": depts})


@login_required
def department_create(request):
    user = request.user
    is_collector = _is_collector(user)
    if DEBUG_PRINT:
        print("CREATE →", "collector" if is_collector else "admin")

    if request.method == "POST":
        form = DeptForm(request.POST, request=request)
        if form.is_valid():
            dept = form.save(commit=False)
            dept.code = auto_dept_id()

            if is_collector:
                dept.district = user.collector_profile.district  # force district

            dept.created_by = user                           # NEW: always set creator
            dept.save()
            messages.success(request, "Department created successfully.")
            return redirect(
                "collector:collector_dashboard" if is_collector else "core:department_list"
            )
    else:
        form = DeptForm(request=request)

    template = (
        "collector/collector_dept_create.html"
        if is_collector else
        "core_app/department_form.html"
    )
    return render(request, template, {"form": form})


@login_required
def department_update(request, code):
    department = get_object_or_404(Department, code=code)
    user = request.user
    is_collector = _is_collector(user)
    if DEBUG_PRINT:
        print("UPDATE →", "collector" if is_collector else "admin")

    form = DeptForm(request.POST or None, instance=department, request=request)
    if form.is_valid():
        dept = form.save(commit=False)
        if is_collector:
            dept.district = user.collector_profile.district
        dept.save()
        messages.success(request, "Department updated.")
        return redirect(
            "collector:collector_dashboard" if is_collector else "core:department_list"
        )

    template = (
        "collector/collector_dept_create.html"
        if is_collector else
        "core_app/department_form.html"
    )
    return render(request, template, {"form": form})


@login_required
def department_delete(request, code):
    department = get_object_or_404(Department, code=code)
    if request.method == "POST":
        department.delete()
        messages.success(request, "Department deleted.")
        return redirect("core:department_list")
    return render(request, "core_app/department_confirm_delete.html", {"department": department})


# ───────────── district views ─────────────
@login_required
def district_list(request):
    return render(request, "core_app/district_list.html", {"districts": District.objects.all()})


@login_required
def district_create(request):
    form = DistrictForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "District created.")
        return redirect("core:district_list")
    return render(request, "core_app/district_form.html", {"form": form})


@login_required
def district_update(request, code):
    district = get_object_or_404(District, code=code)
    form = DistrictForm(request.POST or None, instance=district)
    if form.is_valid():
        form.save()
        messages.success(request, "District updated.")
        return redirect("core:district_list")
    return render(request, "core_app/district_form.html", {"form": form})


@login_required
def district_delete(request, code):
    district = get_object_or_404(District, code=code)
    if request.method == "POST":
        district.delete()
        messages.success(request, "District deleted.")
        return redirect("core:district_list")
    return render(request, "core_app/district_confirm_delete.html", {"district": district})
