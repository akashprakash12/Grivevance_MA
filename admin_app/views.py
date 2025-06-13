from django.shortcuts import render
from core_app.models import Department, District
from grievance_app.models import Grievance
from collector.models import CollectorProfile
from officer.models import OfficerProfile
from user.models import PublicUserProfile

def admin_dashboard(request):
    context = {
        'departments': Department.objects.all(),
        'districts': District.objects.all(),
        'collectors': CollectorProfile.objects.select_related('user', 'district'),
        'officers': OfficerProfile.objects.select_related('user', 'department'),
        'public_users': PublicUserProfile.objects.select_related('user'),
        # 'grievances': Grievance.objects.select_related('user'),
    }
    return render(request, 'admin_app/admin_dashboard.html', context)
