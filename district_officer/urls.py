from django.urls import path
from . import views
from collector.views import grievance_report_view
app_name = "district_officer"

urlpatterns = [
    path("create/",                 views.create_district_officer,  name="create_district_officer"),
     path("list/",                   views.view_district_officer_profile,   name="view_district_officers"),
    path("edit/<str:officer_id>/",  views.update_district_officer,  name="update_district_officer"),
# In your district_officer/urls.py
path('delete-do/<str:officer_id>/', views.delete_district_officer, name='delete_district_officer'),  
  path("DO_dashboard/",views.DO_dashboard,  name="DO_dashboard"),

    path("DO/dashboard/grievance-report/", grievance_report_view, name="do_grievance_report"),

]