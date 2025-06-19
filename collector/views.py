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
from django.db.models import Count, Avg, Min, F, ExpressionWrapper, DurationField
from django.utils.timezone import now
from django.core.paginator import Paginator

# Auto-generate Collector ID based on district code
def auto_collector_id(district):
    prefix = 'COLL'
    return prefix + str(district.code).upper()


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


def update_collector(request, username):
    # Get the existing user and profile
    user_instance = get_object_or_404(User, username=username, user_type='COLLECTOR')
    profile_instance = get_object_or_404(CollectorProfile, user=user_instance)

    # Use update forms (no password fields)
    user_form = CollectorUpdateUserForm(request.POST or None, instance=user_instance)
    profile_form = CollectorProfileForm(request.POST or None, request.FILES or None, instance=profile_instance)

    if request.method == 'POST':
        if user_form.is_valid() and profile_form.is_valid():
            district = profile_form.cleaned_data['district']

            # Save updated user details (without password)
            user = user_form.save(commit=False)
            user.username = auto_collector_id(district)  # Regenerate username based on new district (if changed)
            user.save()

            # Save updated profile
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.collector_id = user.username  # Keep in sync with new username
            profile.save()

            messages.success(request, f"Collector '{user.username}' updated successfully.")
            return redirect('collector:view_collector')

        else:
            print("User form errors:", user_form.errors)
            print("Profile form errors:", profile_form.errors)

    return render(request, 'collector/update_collector.html', {
        'user_form': user_form,
        'profile_form': profile_form
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
            'departments': dept_data,
            'top3_departments': top3_departments,
            'district': district,
            'collector': collector,
            'counts': {
                'total_grievances': total_all,
                'pending_grievances': pending_all,
                'rejected_grievances': rejected_all,
                'resolved_grievances': resolved_all,
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
    district   = collector.district

    departments = Department.objects.filter(district=district)

    report_data = []
    for dept in departments:
        grievances = Grievance.objects.filter(department=dept, district=district)
        total      = grievances.count()
        pending    = grievances.filter(status="PENDING").count()
        resolved   = grievances.filter(status="RESOLVED").count()
        rejected   = grievances.filter(status="REJECTED").count()
        escalated  = grievances.filter(status="ESCALATED").count()

        avg_time = grievances.filter(status="RESOLVED").annotate(
            resolution=ExpressionWrapper(F("last_updated") - F("date_filed"),
                                         output_field=DurationField())
        ).aggregate(avg=Avg("resolution"))["avg"]

        oldest = grievances.filter(status="PENDING").aggregate(
            old=Min("date_filed")
        )["old"]

        report_data.append({
            "name": dept.name,
            "total": total,
            "pending": pending,
            "resolved": resolved,
            "rejected": rejected,
            "escalated": escalated,
            "avg_resolution_time": avg_time,
            "oldest_pending": oldest,
        })

    # ── optional pagination (10 depts per page) ──────────────────────────
    paginator  = Paginator(report_data, 10)
    page_num   = request.GET.get("page")
    page_obj   = paginator.get_page(page_num)

    context = {
        "district"         : district,
        "departments"      : departments,
        "department_report": page_obj.object_list,   # the current slice
        "grievances"       : page_obj,               # for pagination links
    }

    # ✅ pass template‑name **and** context
    return render(request, "collector/department_report.html", context)