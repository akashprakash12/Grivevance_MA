from django.urls import path
from . import views
app_name = 'collector'

urlpatterns = [
    path('create/', views.create_collector, name='create_collector'),
    path('view/', views.view_collector, name='view_collector'),
    path('update/<str:username>/', views.update_collector, name='update_collector'),
    path('delete/<str:username>/', views.delete_collector, name='delete_collector'),
    path('dashboard/', views.collector_dashboard, name='collector_dashboard'),
    path('collector_profile/', views.collector_profile_view, name='collector_profile'),
    path('officer_details/', views.officer_details, name='officer_details'),
    # path('search_grievance_by_id/', views.search_grievance_by_id, name='search_grievance_by_id'),


       path("send-mail/<str:officer_email>/", views.send_email_redirect, name="send_mail"),

    path("collector/dashboard/grievance-report/", views.grievance_report_view, name="grievance_report"),
    path("dashboard/grievance-report/export/excel/", views.export_grievance_excel, name="export_excel"),
    path("dashboard/grievance-report/export/pdf/", views.export_grievance_pdf, name="export_pdf"),
    path("download/<str:grievance_id>/", views.details_download, name="details_download"),


    path("collector/dashboard/department-report/", views.department_report_view, name="get_department_report_data"),


]
