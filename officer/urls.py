from django.urls import path
from officer import views

app_name = 'officer'

urlpatterns = [
    # Collector URLs
    path('collector/create/', views.create_officer_collector, name='create_officer_collector'),
    # path('collector/view/', views.view_officers_collector, name='view_officers_collector'),

    # # Admin URLs
    # path('admin/create/', views.create_officer_admin, name='create_officer_admin'),
    # path('admin/view/', views.view_officers_admin, name='view_officers_admin'),

    # Common URLs
    # path('delete/<str:username>/', views.delete_officer, name='delete_officer'),
    path('update/<str:username>/', views.update_officer, name='update_officer'),
]
