from django.urls import path
from hod import views

app_name = 'hod'

urlpatterns = [
    path('assign/', views.assign_grievance, name='assign_grievance'),
    path('progress/', views.check_grievance_progress, name='check_progress'),
    path('verify/<int:grievance_id>/', views.verify_officer_actions, name='verify_actions'),
    path('extensions/approve/', views.approve_date_extension_requests, name='approve_extension_requests'),
    path('search/', views.search_grievance, name='search_grievance'),
    path('officers/', views.officers_assigned_grievances, name='officers_assigned_grievances'),
    path('hod_dashboard/', views.hod_dashboard, name='hod_dashboard'),
    path('profile/', views.hod_profile, name='hod_profile'),
    path('update/<int:hod_id>/', views.update_hod, name='update_hod'),
    path('delete/<int:hod_id>/', views.delete_hod, name='delete_hod'),
]
