# admin_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    # No need to redefine department or district URLs here
]
