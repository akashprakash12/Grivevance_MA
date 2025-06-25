from django.urls import path
from . import views
from grievance_app.views import create_grievance ,load_departments # Ensure this import is correct
from django.conf import settings
from django.conf.urls.static import static

app_name = 'public_user'  # <--- VERY IMPORTANT

urlpatterns = [
    path('create/', views.create_public_user, name='user_dashboard'),  # Fixed typo in name
    path('view/', views.view_public_users, name='view_public_users'),
    path('update/<str:username>/', views.update_public_user, name='update_public_user'),
    path('delete/<str:username>/', views.delete_public_user, name='delete_public_user'),
    path('submit-complaint/', create_grievance, name='submit_complaint'),
    path('help/', views.help, name='help'),
    path('account_settings/', views.account_settings, name='account_settings'),  # Removed extra space
    # grievance_app/urls.py
    path('ajax/load-departments/', load_departments, name='ajax_load_departments'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)