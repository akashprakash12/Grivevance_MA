from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from grievance_app.models import Grievance  # adjust import if your app name differs
from django.db.models import Count, Q

from .forms import CollectorCreateUserForm, CollectorUpdateUserForm,CollectorProfileForm
from .models import CollectorProfile
from user.models import User
from core_app.models import Department, District
from officer.models import OfficerProfile

from django.contrib.auth.decorators import login_required
from openpyxl import Workbook
from django.http import HttpResponse,HttpResponseForbidden,FileResponse,HttpResponseRedirect
import pandas as pd
from fpdf import FPDF
import csv
import io
import os
from django.conf import settings
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# views.py
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from urllib.parse import quote
from django.utils.timezone import is_aware
from django.utils.dateparse import parse_date
import datetime
from django.db.models import (
    Count, Avg, Q, F, ExpressionWrapper, DurationField, FloatField, Case, When, Value
)
from django.utils.timezone import now
from django.core.paginator import Paginator
from django.db.models.functions import Coalesce, Cast, Round
from django.db.models import Value
import openpyxl
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password
import re


from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
# Auto-generate Collector ID based on district code
#set this to first as 49

def auto_collector_id(district):
    prefix = 'COLL'
    district_code = district.code.upper()

    # Filter collector IDs for this district
    collectors = CollectorProfile.objects.filter(district=district).values_list('collector_id', flat=True)

    max_number = 0
    pattern = re.compile(rf"{prefix}(\d+){district_code}$", re.IGNORECASE)

    for cid in collectors:
        match = pattern.match(cid)
        if match:
            num = int(match.group(1))
            if num > max_number:
                max_number = num

    next_number = max_number + 1
    return f"{prefix}{next_number}{district_code}"

# Create new collector (user + profile)
def create_collector(request):
    user_form = CollectorCreateUserForm(request.POST or None)
    profile_form = CollectorProfileForm(request.POST, request.FILES)

    if request.method == 'POST':
        if user_form.is_valid() and profile_form.is_valid():
            district = profile_form.cleaned_data['district']

            # Create user
            user = user_form.save(commit=False)
            user.username = auto_collector_id(district)
            user.password = make_password(user.password)
            user.user_type = 'COLLECTOR'
            user.is_active = True
            user.date_joined = timezone.now()
            user.save()

            # Create profile
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.collector_id = user.username
            profile.save()

            # Assign to 'collector' group
            collector_group = Group.objects.get(name='collector')
            user.groups.add(collector_group)

            messages.success(request, f"Collector '{user.username}' created successfully.")
            print("Uploaded file:", profile_form.cleaned_data['profile_picture'])

            return redirect('collector:view_collector')
        else:
            print("User form errors:", user_form.errors)
            print("Profile form errors:", profile_form.errors)

    return render(request, 'collector/create_collector.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


# View all collectors
def view_collector(request):
    collectors = CollectorProfile.objects.all()
    return render(request, 'collector/collector_list.html', {'collectors': collectors})
# ──────────────────────────────────────────────────────────








@login_required
def update_collector(request, username):
    """Handle collector profile updates"""

    # Ensure only collectors can access
    if request.user.user_type != "COLLECTOR":
        messages.error(request, "Only collectors may access this page")
        return redirect("home")

    user_obj = request.user
    profile_obj = get_object_or_404(CollectorProfile, user=user_obj)
    district = profile_obj.district

    if request.method == "POST":
        user_form = CollectorUpdateUserForm(request.POST, instance=user_obj)
        profile_form = CollectorProfileForm(request.POST, request.FILES, instance=profile_obj)

        # Force the district value if disabled in the form
        profile_form.data = profile_form.data.copy()
        profile_form.data["district"] = district.pk

        if user_form.is_valid() and profile_form.is_valid():
            # Save user
            user = user_form.save(commit=False)
            user.username = auto_collector_id(district)
            user.save()

            # Save profile
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.collector_id = user.username
            profile.district = district

            # Check if image uploaded
            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']

            profile.save()

            messages.success(request, "Profile updated successfully!")
            return redirect("collector:update_collector", username=user.username)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = CollectorUpdateUserForm(instance=user_obj)
        profile_form = CollectorProfileForm(instance=profile_obj)

    return render(request, "collector/update_collector.html", {
        "user_form": user_form,
        "profile_form": profile_form,
    })

# Delete a collector
def delete_collector(request, username):
    user = get_object_or_404(User, username=username, user_type='COLLECTOR')
    user.delete()
    messages.success(request, f"Collector '{username}' deleted successfully.")
    return redirect('collector:view_collector')


# collector dashboard view


@login_required
def collector_dashboard(request):
    try:
        collector = (
            CollectorProfile.objects
            .select_related('district')
            .get(user=request.user)
        )
        district = collector.district

        # ---------------------------------------------------------
        # 1. One DB hit: annotate each department with counts
        # ---------------------------------------------------------
        departments_qs = (
            Department.objects
            .filter(district=district)
            .annotate(
                total    = Count('grievance', filter=Q(grievance__district=district)),
                pending  = Count('grievance', filter=Q(grievance__district=district,
                                                      grievance__status='PENDING')),
                rejected = Count('grievance', filter=Q(grievance__district=district,
                                                       grievance__status='REJECTED')),
            )
            .order_by('-pending')      # highest pending first (main list)
        )

        dept_data = []
        for dept in departments_qs:
            total     = dept.total
            pending   = dept.pending
            rejected  = dept.rejected
            resolved  = total - pending - rejected

            pending_pct  = round((pending  / total) * 100, 1) if total else 0.0
            rejected_pct = round((rejected / total) * 100, 1) if total else 0.0

            badge_class = (
                'danger'  if pending_pct >= 75 else
                'warning' if pending_pct >= 25 else
                'success'
            )

            dept_data.append({
                'name'            : dept.name,
                'code'            : getattr(dept, 'code', ''),
                'total'           : total,
                'pending'         : pending,
                'rejected'        : rejected,
                'resolved'        : resolved,
                'pending_percent' : pending_pct,
                'rejected_percent': rejected_pct,
                'badge_class'     : badge_class,
            })

        # ---------------------------------------------------------
        # 2. Pick top‑3 best performers (low pending %, then rejects)
        # ---------------------------------------------------------
        candidates = [d for d in dept_data if d['total'] > 0]
        candidates.sort(key=lambda d: (d['pending_percent'], d['rejected_percent']))
        top3_departments = candidates[:3]

        # ---------------------------------------------------------
        # 3. District‑wide totals (one query)
        # ---------------------------------------------------------
        all_grievances = Grievance.objects.filter(district=district)
        total_all     = all_grievances.count()
        pending_all   = all_grievances.filter(status='PENDING').count()
        rejected_all  = all_grievances.filter(status='REJECTED').count()
        resolved_all  = total_all - pending_all - rejected_all

        context = {
            'departments'      : dept_data,        # ordered high‑pending → low
            'top3_departments' : top3_departments, # best performers list/card
            'district'         : district,
            'collector'        : collector,
            'counts' : {
                'total_grievances'    : total_all,
                'pending_grievances'  : pending_all,
                'rejected_grievances' : rejected_all,
                'resolved_grievances' : resolved_all,
            },
        }
        return render(request, 'collector/collector_dashboard.html', context)

    except CollectorProfile.DoesNotExist:
        messages.error(request, "Access denied. Collector profile not found.")
        return redirect('login')

#profile details


@login_required
def collector_profile_view(request):
    user = request.user  # Logged-in user (from User model)

    try:
        # Get the collector profile connected to this user
        profile = CollectorProfile.objects.get(user=user)
        collector_profile = {
                    'full_name': f"{user.first_name} {user.last_name}",
                    'email': user.email,
                    'username': user.username,
                    'district': profile.district.name,
                    'official_address': profile.official_address,
                    'collector_id': profile.collector_id,
                    'tenure_start': profile.tenure_start,
                    'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
                }

        return render(request, 'collector/profile.html', collector_profile)

    except CollectorProfile.DoesNotExist:
        messages.error(request, "Collector profile not found.")
        return redirect('dashboard')


@login_required
def officer_details(request):
    # Get collector and district
    collector_profile = get_object_or_404(CollectorProfile.objects.select_related('district'), user=request.user)
    district = collector_profile.district
    

    # Get HOD officers in the collector's district
    hod_officers = OfficerProfile.objects.select_related('user', 'department') \
        .filter(is_hod=True, department__district=district) \
        .only('user__first_name', 'user__last_name', 'user__email', 'user__phone', 'department__name')

    context = {
        'hod_officers': hod_officers,
        'district': district.name,
    }

    return render(request, 'collector/hod_list.html', context)




# @login_required
# def search_grievance_by_id(request):
#     collector = get_object_or_404(CollectorProfile, user=request.user)
#     district = collector.district
#     grievances = Grievance.objects.filter(district=district)

#     # Get the grievance ID from the request (can be POST or GET based on form method)
#     grievance_id = request.GET.get('grievance_id') or request.POST.get('grievance_id')

#     if grievance_id:
#         grievances = grievances.filter(grievance_id__icontains=grievance_id)

#     return render(request, 'collector/grievance_search_results.html', {
#         'grievances': grievances,
#         'departments': Department.objects.filter(district=district),
#     })



@login_required
def send_email_redirect(request, officer_email):
    collector_email = request.user.email  # Dynamic sender (logged-in user)

    # Gmail Compose URL
    compose_url = f"https://mail.google.com/mail/?view=cm&fs=1&tf=1&to={quote(officer_email)}"

    # Redirect to Gmail account chooser (if not signed in / wrong account)
    redirect_url = (
        "https://accounts.google.com/AccountChooser"
        f"?continue={quote(compose_url, safe='')}"
        f"&Email={quote(collector_email)}"
        "&service=mail"
    )

    return HttpResponseRedirect(redirect_url)

def _filtered_grievance_qs(request, district):
    """
    Return Grievances in the given district filtered by query params
    """
    # Get cleaned parameters
    status = (request.GET.get("status") or "ALL").strip().upper()
    dept_code = (request.GET.get("department") or "").strip()
    search = (request.GET.get("search") or "").strip()
    date_from = parse_date((request.GET.get("date_from") or "").strip())
    date_to = parse_date((request.GET.get("date_to") or "").strip())

    # Base queryset
    qs = (
        Grievance.objects
        .filter(district=district)
        .select_related("department", "district")
        .order_by("-date_filed")
    )

    # Status filter
    if status != "ALL":
        qs = qs.filter(status__iexact=status)

    # Department filter - using code field
    if dept_code:
        qs = qs.filter(department__code__iexact=dept_code)  # ✅ Lowercase "department"

    # Search filter
    if search:
        search_q = Q()
        for term in search.split():
            search_q |= (
                Q(grievance_id__icontains=term) |
                Q(contact_number__icontains=term) |
                Q(email__icontains=term) |
                Q(applicant_name__icontains=term)
            )
        qs = qs.filter(search_q)

    # Date range filter
    date_filter = Q()
    if date_from:
        date_filter &= Q(date_filed__date__gte=date_from)
    if date_to:
        date_filter &= Q(date_filed__date__lte=date_to)
    if date_filter:
        qs = qs.filter(date_filter)

    return qs
@login_required
def grievance_report_view(request):
    collector = get_object_or_404(CollectorProfile, user=request.user)
    district = collector.district
    departments = Department.objects.filter(district=district)

    grievances = _filtered_grievance_qs(request, district)

    return render(request, "collector/grievance_report.html", {
        "grievances": grievances,
        "departments": departments,
        "request": request,
        "district":district
    })

def export_grievance_excel(request):
    collector = get_object_or_404(CollectorProfile, user=request.user)
    district = collector.district

    # Include all fields in the values() call
    qs = _filtered_grievance_qs(request, district).values(
        'grievance_id',
        'date_filed',
        'last_updated',
        'subject',
        'description',
        'source',
        'status',
        'priority',
        'due_date',
        'applicant_name',
        'applicant_address',
        'contact_number',
        'email',
        'department__name',
        'district__name'
    )

    # Convert timezone-aware datetimes to naive and format dates
    for row in qs:
        for date_field in ['date_filed', 'last_updated', 'due_date']:
            field_value = row.get(date_field)
            if field_value:
                if isinstance(field_value, datetime.datetime):
                    # Handle datetime objects
                    if is_aware(field_value):
                        row[date_field] = field_value.replace(tzinfo=None)
                    # Format as string for Excel
                    row[date_field] = field_value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(field_value, datetime.date):
                    # Handle date objects (convert to string)
                    row[date_field] = field_value.strftime('%Y-%m-%d')

    # Create DataFrame with all fields
    df = pd.DataFrame(qs)
    
    # Rename columns for better Excel headers
    df.columns = [
        'Grievance ID',
        'Date Filed',
        'Last Updated',
        'Subject',
        'Description',
        'Source',
        'Status',
        'Priority',
        'Due Date',
        'Applicant Name',
        'Applicant Address',
        'Contact Number',
        'Email',
        'Department',
        'District'
    ]

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # Export data to Excel
        df.to_excel(writer, sheet_name="Grievances", index=False)
        
        # Get workbook and worksheet objects for formatting
        workbook = writer.book
        worksheet = writer.sheets['Grievances']
        
        # Set column widths (adjust as needed)
        column_widths = {
            'A': 15,  # Grievance ID
            'B': 20,  # Date Filed
            'C': 20,  # Last Updated
            'D': 30,  # Subject
            'E': 50,  # Description
            'F': 15,  # Source
            'G': 15,  # Status
            'H': 10,  # Priority
            'I': 20,  # Due Date
            'J': 25,  # Applicant Name
            'K': 40,  # Applicant Address
            'L': 15,  # Contact Number
            'M': 25,  # Email
            'N': 25,  # Department
            'O': 20   # District
        }
        
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width
        
        # Freeze header row
        worksheet.freeze_panes = 'A2'
        
        # Add auto-filter
        worksheet.auto_filter.ref = worksheet.dimensions

    buffer.seek(0)

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"{district.code.lower()}_grievance_report.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
@login_required
def export_grievance_pdf(request):
    try:
        # ---------- DATA PREPARATION ----------
        collector = get_object_or_404(CollectorProfile, user=request.user)
        district = collector.district
        
        # Get filtered data with all needed columns
        cols = [
            "grievance_id", "date_filed", "last_updated", "subject", 
            "description", "source", "status", "priority", "due_date",
            "applicant_name", "applicant_address", "contact_number", "email",
            "department__name", "district__name",
        ]
        rows = _filtered_grievance_qs(request, district).values(*cols)
        
        # ---------- PDF SETUP ----------
        pdf = FPDF("L", "mm", "A4")
        margin = 15
        pdf.set_auto_page_break(auto=True, margin=margin)
        pdf.set_margins(left=margin, top=margin, right=margin)
        pdf.add_page()
        
        # ---------- FONTS ----------
        try:
            font_dir = Path(settings.BASE_DIR) / "fonts"
            pdf.add_font("DV", "", str(font_dir / "DejaVuSans.ttf"), uni=True)
            pdf.add_font("DV", "B", str(font_dir / "DejaVuSans-Bold.ttf"), uni=True)
            font_family = "DV"
        except:
            font_family = "Arial"  # Fallback to built-in font
        
        # ---------- TITLE SECTION ----------
        pdf.set_font(font_family, "B", 16)
        pdf.cell(0, 12, f"{district.name} - Grievance Report", ln=True, align="C")
        pdf.ln(6)
        
        # ---------- TABLE CONFIG ----------
        printable_width = pdf.w - 2 * margin
        col_widths = [
            22,  # ID
            20,  # Filed
            22,  # Updated
            36,  # Subject
            40,  # Description
            18,  # Source
            18,  # Status
            15,  # Priority
            20,  # Due
            28,  # Name
            35,  # Address
            22,  # Contact
            30,  # Email
            25,  # Dept
            25   # Dist
        ]
        
        headers = [
            "ID", "Filed", "Updated", "Subject", "Description", "Source",
            "Status", "Pri", "Due", "Name", "Address", "Contact", "Email",
            "Dept", "Dist"
        ]
        
        # ---------- TABLE HEADER ----------
        pdf.set_font(font_family, "B", 10)
        pdf.set_fill_color(200, 220, 255)  # Light blue background
        for header, width in zip(headers, col_widths):
            pdf.cell(width, 8, header, border=1, align="C", fill=True)
        pdf.ln()
        
        # ---------- TABLE BODY ----------
        pdf.set_font(font_family, "", 9)
        
        # Helper function to calculate lines needed for text
        def calculate_lines(text, width):
            if not text:
                return 1
            return len(pdf.multi_cell(width, 6, str(text), split_only=True))
        
        for row in rows:
            # Calculate maximum lines needed for this row
            line_counts = []
            for i, (key, width) in enumerate(zip(cols, col_widths)):
                text = row.get(key, "")
                if key in ["date_filed", "last_updated", "due_date"] and text:
                    text = text.strftime("%Y-%m-%d") if hasattr(text, 'strftime') else text
                line_counts.append(calculate_lines(text, width))
            
            max_lines = max(line_counts) if line_counts else 1
            row_height = 6 * max_lines  # 6mm per line
            
            # Check for page break
            if pdf.get_y() + row_height > pdf.page_break_trigger:
                pdf.add_page()
                # Redraw header on new page
                pdf.set_font(font_family, "B", 10)
                pdf.set_fill_color(200, 220, 255)
                for header, width in zip(headers, col_widths):
                    pdf.cell(width, 8, header, border=1, align="C", fill=True)
                pdf.ln()
                pdf.set_font(font_family, "", 9)
            
            # Remember starting position
            x_start = pdf.get_x()
            y_start = pdf.get_y()
            
            # Draw each cell
            for i, (key, width) in enumerate(zip(cols, col_widths)):
                text = row.get(key, "")
                if key in ["date_filed", "last_updated", "due_date"] and text:
                    text = text.strftime("%Y-%m-%d") if hasattr(text, 'strftime') else text
                
                pdf.multi_cell(
                    width, 6, str(text), 
                    border=1, align="L", 
                    max_line_height=6,
                    new_x="RIGHT", new_y="TOP"
                )
                pdf.set_xy(x_start + width, y_start)
                x_start += width
            
            # Move to next row
            pdf.ln(row_height)
        
        # Create buffer and save PDF to it
        buffer = io.BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        
        # Create response without saving to session
        response = FileResponse(
            buffer,
            as_attachment=True,
            filename=f"{district.code.lower()}_grievance_report.pdf",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        
        return response
    
    except Exception as e:
        messages.error(request, f"Failed to generate PDF: {str(e)}")
        return redirect("collector:grievance_report")
    




@login_required 
def details_download(request, grievance_id):
    try:
        collector = get_object_or_404(CollectorProfile, user=request.user)
        district = collector.district

        grievance = get_object_or_404(
            Grievance.objects.select_related("department", "district"),
            grievance_id=grievance_id,
            district=district
        )

        # PDF Setup
        pdf = FPDF("P", "mm", "A4")
        margin = 15
        pdf.set_auto_page_break(auto=True, margin=margin)
        pdf.set_margins(left=margin, top=margin, right=margin)
        pdf.add_page()
        pdf.set_line_width(0.5)
        pdf.rect(margin - 5, margin - 5, 210 - (margin - 5)*2, 297 - (margin - 5)*2)

        try:
            font_dir = Path(settings.BASE_DIR) / "fonts"
            pdf.add_font("DV", "", str(font_dir / "DejaVuSans.ttf"), uni=True)
            pdf.add_font("DV", "B", str(font_dir / "DejaVuSans-Bold.ttf"), uni=True)
            font_family = "DV"
        except:
            font_family = "Arial"

        # Title
        pdf.ln(15)
        pdf.set_font(font_family, "B", 18)
        pdf.cell(0, 10, "Grievance Report", ln=True, align="C")
        pdf.ln(6)

        # Body
        pdf.set_font(font_family, "B", 13)
        pdf.cell(0, 8, f"Grievance ID: {grievance.grievance_id}", ln=True)

        pdf.set_font(font_family, "", 12)
        pdf.cell(0, 6, f"Applicant: {grievance.applicant_name}", ln=True)
        pdf.cell(0, 6, f"Address: {grievance.applicant_address}", ln=True)
        pdf.cell(0, 6, f"Contact: {grievance.contact_number}", ln=True)
        pdf.cell(0, 6, f"Email: {grievance.email}", ln=True)
        pdf.ln(2)

        pdf.cell(0, 6, f"Subject: {grievance.subject}", ln=True)
        if grievance.description:
            pdf.multi_cell(0, 6, f"Description: {grievance.description}")

        pdf.cell(0, 6, f"Source: {grievance.source} | Status: {grievance.status} | Priority: {grievance.priority}", ln=True)
        pdf.cell(0, 6, f"Department: {grievance.department.name}", ln=True)
        pdf.cell(0, 6, "-"*50, ln=True)
        pdf.cell(0, 6, f"Filed: {grievance.date_filed:%Y-%m-%d} | Last Updated: {grievance.last_updated:%Y-%m-%d} | Due: {grievance.due_date:%Y-%m-%d}", ln=True)

        # Return PDF
        buffer = io.BytesIO()
        pdf.output(buffer)
        buffer.seek(0)

        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f"{grievance.grievance_id}_report.pdf",
            content_type="application/pdf"
        )

    except Exception as e:
        messages.error(request, f"Failed to generate PDF: {str(e)}")
        return redirect("collector:grievance_report")
   








@login_required
def department_report_view(request):
    collector = get_object_or_404(CollectorProfile, user=request.user)
    district = collector.district

    qs = Department.objects.filter(district=district)
    search = request.GET.get("search")
    sort_by = request.GET.get("sort_by")

    if search:
        qs = qs.filter(name__icontains=search)

    report_data = []
    for dept in qs:
        grievances = Grievance.objects.filter(department=dept, district=district)
        total = grievances.count()
        pending = grievances.filter(status="PENDING").count()
        resolved = grievances.filter(status="RESOLVED").count()
        rejected = grievances.filter(status="REJECTED").count()
        escalated = grievances.filter(status="ESCALATED").count()

        resolution_rate = round((resolved / total) * 100, 2) if total else 0

        report_data.append({
            "name": dept.name,
            "code": dept.code,
            "total": total,
            "pending": pending,
            "resolved": resolved,
            "rejected": rejected,
            "escalated": escalated,
            "resolution_rate": resolution_rate,
        })

    if sort_by:
        reverse = sort_by.startswith("-")
        key = sort_by.lstrip("-")
        report_data.sort(key=lambda x: x.get(key, 0), reverse=reverse)

    # ✅ Store final filtered and sorted data for export
    request.session['filtered_department_report'] = report_data

    paginator = Paginator(report_data, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    total_depts = qs.count()
    avg_resolution_rate = round(sum(d["resolution_rate"] for d in report_data) / total_depts, 2) if total_depts else 0

    context = {
        "district": district,
        "department_report": page_obj,
        "department_count": total_depts,
        "summary": {
            "total_depts": total_depts,
            "avg_resolution_rate": avg_resolution_rate,
        }
    }
    return render(request, "collector/department_report.html", context)


@login_required
def export_department_excel(request):
    collector = get_object_or_404(CollectorProfile, user=request.user)
    district = collector.district

    report_data = request.session.get("filtered_department_report")

    # Fallback: if session is missing
    if not report_data:
        qs = Department.objects.filter(district=district)
        report_data = []
        for dept in qs:
            grievances = Grievance.objects.filter(department=dept, district=district)
            total = grievances.count()
            resolved = grievances.filter(status="RESOLVED").count()
            report_data.append({
                "name": dept.name,
                "code": dept.code,
                "total": total,
                "pending": grievances.filter(status="PENDING").count(),
                "resolved": resolved,
                "rejected": grievances.filter(status="REJECTED").count(),
                "escalated": grievances.filter(status="ESCALATED").count(),
                "resolution_rate": round((resolved / total) * 100, 2) if total else 0,
            })

    df = (
        pd.DataFrame(report_data)
          .rename(columns={
              "name": "Department",
              "code": "Code",
              "total": "Total Grievances",
              "pending": "Pending",
              "resolved": "Resolved",
              "rejected": "Rejected",
              "escalated": "Escalated",
              "resolution_rate": "Resolution Rate (%)",
          })
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Department Report", index=False)
        ws = writer.sheets["Department Report"]

        widths = [25, 15, 18, 12, 12, 12, 12, 20, 25]
        for idx, width in enumerate(widths, start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = width

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

    buffer.seek(0)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"{district.name.replace(' ', '_')}_department_report.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

@login_required
def export_department_pdf(request):
    try:
        collector = get_object_or_404(CollectorProfile, user=request.user)
        district = collector.district

        report_data = request.session.get("filtered_department_report", [])

        if not report_data:
            messages.error(request, "No filtered data available to export. Please generate a report first.")
            return redirect('department_report_view')

        # --- PDF Setup ---
        pdf = FPDF('L', 'mm', 'A4')  # Landscape A4
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        try:
            font_dir = Path(settings.BASE_DIR) / "fonts"
            pdf.add_font('DejaVu', '', str(font_dir / 'DejaVuSans.ttf'), uni=True)
            pdf.add_font('DejaVu', 'B', str(font_dir / 'DejaVuSans-Bold.ttf'), uni=True)
            font = 'DejaVu'
        except:
            font = 'Arial'

        pdf.set_font(font, 'B', 16)
        pdf.cell(0, 10, f'{district.name} - Department Performance Report', 0, 1, 'C')
        pdf.ln(5)

        # --- Table Header ---
        pdf.set_fill_color(79, 129, 189)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(font, 'B', 10)

        col_widths = [60, 22, 22, 22, 22, 22, 30, 35]
        headers = [
            'Department', 'Code', 'Total', 'Pending',
            'Resolved', 'Rejected', 'Resolution %',
        ]

        for header, width in zip(headers, col_widths):
            pdf.cell(width, 8, header, border=1, align='C', fill=True)
        pdf.ln()

        # --- Table Body ---
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(font, '', 9)

        for dept in report_data:
            pdf.cell(col_widths[0], 8, dept['name'], border=1)
            pdf.cell(col_widths[1], 8, dept['code'], border=1, align='C')
            pdf.cell(col_widths[2], 8, str(dept['total']), border=1, align='C')
            pdf.cell(col_widths[3], 8, str(dept['pending']), border=1, align='C')
            pdf.cell(col_widths[4], 8, str(dept['resolved']), border=1, align='C')
            pdf.cell(col_widths[5], 8, str(dept['rejected']), border=1, align='C')
            pdf.cell(col_widths[6], 8, f"{dept['resolution_rate']}%", border=1, align='C')
            pdf.ln()

        # --- Output the PDF ---
        buffer = io.BytesIO()
        pdf.output(buffer)
        buffer.seek(0)

        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f"{district.name.replace(' ', '_')}_department_report.pdf",
            content_type='application/pdf'
        )

    except Exception as e:
        messages.error(request, f"Failed to generate PDF: {str(e)}")
        return redirect('department_report_view')







def department_card_view(request, department_id):
    # ---------- basic context ----------
    collector = get_object_or_404(
        CollectorProfile.objects.select_related('district'),
        user=request.user
    )
    district    = collector.district
    department  = get_object_or_404(Department, code=department_id)

    # ---------- filters from request ----------
    status_filter = request.GET.get("status", "ALL")
    date_from     = request.GET.get("date_from")
    date_to       = request.GET.get("date_to")
    search_query  = request.GET.get("search", "").strip()

    # ---------- start with dept + district ----------
    base_qs = Grievance.objects.filter(
        district=district,
        department=department
    )

    # ----- date range -----
    if date_from:
        base_qs = base_qs.filter(date_filed__date__gte=date_from)
    if date_to:
        base_qs = base_qs.filter(date_filed__date__lte=date_to)

    # ----- free‑text search (ID or phone) -----
    if search_query:
        base_qs = base_qs.filter(
            Q(grievance_id__icontains=search_query) |
            Q(contact_number__icontains=search_query)
        )

    # ---------- counts BEFORE status filter ----------
    counts = {
        "total":     base_qs.count(),
        "pending":   base_qs.filter(status="PENDING").count(),
        "in_progress": base_qs.filter(status="IN_PROGRESS").count(),
        "resolved":  base_qs.filter(status="RESOLVED").count(),
        "rejected":  base_qs.filter(status="REJECTED").count(),
        "escalated": base_qs.filter(status="ESCALATED").count(),
    }

    # ---------- now apply status filter for table ----------
    if status_filter != "ALL":
        grievances_qs = base_qs.filter(status=status_filter)
    else:
        grievances_qs = base_qs

    grievances_qs = grievances_qs.order_by("-date_filed")

    # ---------- pagination ----------
    paginator   = Paginator(grievances_qs, 25)
    page_number = request.GET.get("page")
    page_obj    = paginator.get_page(page_number)

    # ---------- render ----------
    context = {
        "district":       district,
        "department":     department,
        "grievances":     page_obj,
        "counts":         counts,
        "status_filter":  status_filter,
        "date_from":      date_from,
        "date_to":        date_to,
        "search_query":   search_query,
    }
    return render(request, "collector/each_dept.html", context)

@login_required
def collector_change_password(request):
    """Handle password changes"""
    if request.method == "POST":
        user = request.user
        current_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not check_password(current_password, user.password):
            messages.error(request, "Current password is incorrect")
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match")
        else:
            try:
                validate_password(new_password, user=user)
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully!")
                return redirect("collector:update_collector", username=user.username)
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)

    return render(request, "collector/password_change.html")


def update_remark(request):
    grievance_id = request.POST.get('grievance_id')
    remark = request.POST.get('remark')
    priority = request.POST.get('priority')

    grievance = get_object_or_404(Grievance, id=grievance_id)
    grievance.remark = remark
    grievance.priority = priority
    grievance.save()

    messages.success(request, f"Remark and priority updated for GRV ID: {grievance.grievance_id}")
    return redirect('collector:department_card', grievance.department.code)


@login_required
def department_grievances_download(request, department_id):
    try:
        # 1. Security/ownership checks
        collector = get_object_or_404(CollectorProfile, user=request.user)
        district = collector.district
        department = get_object_or_404(Department, code=department_id, district=district)

        # 2. Apply filters from request
        qs = (
            Grievance.objects
            .filter(district=district, department=department)
            .select_related("department")
            .order_by("-date_filed")
        )

        status = request.GET.get("status", "ALL")
        if status != "ALL":
            qs = qs.filter(status=status)

        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")
        if date_from:
            qs = qs.filter(date_filed__gte=date_from)
        if date_to:
            qs = qs.filter(date_filed__lte=date_to)

        search = request.GET.get("search")
        if search:
            qs = qs.filter(
                Q(grievance_id__icontains=search) |
                Q(contact_number__icontains=search)
            )

        # 3. PDF setup with simplified font handling
        pdf = FPDF("P", "mm", "A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Use built-in fonts to avoid font registration issues
        font_family = 'Arial'  # Default built-in font
        
        # Alternatively, if you really need DejaVu, register all variants properly:
        try:
            font_dir = Path(settings.BASE_DIR) / "fonts"
            if font_dir.exists():
                # Register all required variants
                pdf.add_font('DejaVu', '', str(font_dir / 'DejaVuSans.ttf'), uni=True)
                pdf.add_font('DejaVu', 'B', str(font_dir / 'DejaVuSans-Bold.ttf'), uni=True)
                pdf.add_font('DejaVu', 'I', str(font_dir / 'DejaVuSans-Oblique.ttf'), uni=True)
                pdf.add_font('DejaVu', 'BI', str(font_dir / 'DejaVuSans-BoldOblique.ttf'), uni=True)
                font_family = 'DejaVu'
        except Exception as font_error:
            print(f"Font loading error, falling back to Arial: {font_error}")
            font_family = 'Arial'

        # Header
        pdf.set_font(font_family, "B", 16)
        pdf.cell(0, 10, f"{district.name} District", ln=True, align="C")
        pdf.cell(0, 10, f"{department.name} - Grievance Report", ln=True, align="C")
        
        # Filters info
        pdf.set_font(font_family, "", 10)  # Note: Using regular style, not italic
        filter_text = []
        if status != "ALL":
            filter_text.append(f"Status: {status}")
        if date_from:
            filter_text.append(f"From: {date_from}")
        if date_to:
            filter_text.append(f"To: {date_to}")
        if search:
            filter_text.append(f"Search: {search}")
        
        if filter_text:
            pdf.ln(5)
            pdf.cell(0, 6, "Filters: " + " | ".join(filter_text), ln=True)
        
        pdf.ln(10)

        # Grievance list
        if qs.exists():
            pdf.set_font(font_family, "B", 11)
            for grievance in qs:
                pdf.cell(0, 8, f"GRV {grievance.grievance_id}  -  {grievance.applicant_name}", ln=True)
                
                pdf.set_font(font_family, "", 9)  # Regular style for details
                filed_date = grievance.date_filed.strftime('%Y-%m-%d %H:%M')
                due_date = grievance.due_date.strftime('%Y-%m-%d') if grievance.due_date else 'Not set'
                
                pdf.multi_cell(
                    0,
                    5,
                    (
                        f"Contact: {grievance.contact_number} | Priority: {grievance.priority} | Status: {grievance.get_status_display()}\n"
                        f"Subject: {grievance.subject or '-'}\n"
                        f"Description: {grievance.description}\n"
                        f"Filed: {filed_date} | Due: {due_date}"
                    ),
                )
                
                pdf.set_draw_color(200, 200, 200)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)
                pdf.set_font(font_family, "B", 11)
        else:
            pdf.set_font(font_family, "", 12)
            pdf.cell(0, 10, "No grievances found matching the selected filters", ln=True, align="C")

        # Footer - using regular font instead of italic to avoid issues
        pdf.set_y(-15)
        pdf.set_font(font_family, "", 8)  # Changed from "I" to ""
        pdf.cell(0, 10, f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}", 0, 0, 'C')

        # 4. Stream PDF to browser
        buffer = io.BytesIO()
        pdf.output(buffer)
        buffer.seek(0)

        file_name = f"{department.code.lower()}_grievances_{timezone.now().strftime('%Y%m%d')}.pdf"
        return FileResponse(buffer, as_attachment=True,
                          filename=file_name,
                          content_type="application/pdf")

    except Exception as e:
        print(f"Error in PDF generation: {str(e)}")
        return HttpResponse(f"An error occurred while generating the PDF: {str(e)}", status=500)