from django.urls import path
from . import views
from grievance_app.views import create_grievance ,load_departments,view_grievances,detail_grievance# Ensure this import is correct
from django.conf import settings
from django.conf.urls.static import static

app_name = 'public_user'  # <--- VERY IMPORTANT

urlpatterns = [
    path('create/', views.user_dashboard, name='user_dashboard'),  # Fixed typo in name
    path('view/', view_grievances, name='view_grievances'),
    path('update/<str:username>/', views.update_public_user, name='update_public_user'),
    path('delete/<str:username>/', views.delete_public_user, name='delete_public_user'),
    path('submit-complaint/', create_grievance, name='submit_complaint'),
    path('help/', views.help, name='help'),
    path('account_settings/', views.account_settings, name='account_settings'),  # Removed extra space
    path('ajax/load-departments/', load_departments, name='ajax_load_departments'),
    path('grievance/<str:grievance_id>/', detail_grievance, name='detail_grievance'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)