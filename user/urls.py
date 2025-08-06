from django.urls import path
from . import views
from grievance_app.views import (
    create_grievance,
    load_departments,
    view_grievances,
    detail_grievance,
    update_grievance,
    delete_grievance
)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
app_name = 'public_user'

urlpatterns = [
    path('api/districts/', views.get_districts, name='api_districts'),
    path('api/taluks/<str:district_name>/', views.get_taluks, name='api_taluks'),
    path('api/villages/<str:taluk_name>/', views.get_villages, name='api_villages'),
    
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', views.user_dashboard, name='user_dashboard'),
    path(('view/'), view_grievances, name='view_grievances'),
    path(('update/<str:username>/'), views.update_public_user, name='update_public_user'),
    path(('delete/<str:username>/'), views.delete_public_user, name='delete_public_user'),
    path(('submit-complaint/'), create_grievance, name='submit_complaint'),
    path(('help/'), views.help, name='help'),
    path(('account_settings/'), views.account_settings, name='account_settings'),
    path('ajax/load-departments/', load_departments, name='ajax_load_departments'),
    path(('delete/'), views.delete_public_user_by_public, name='delete_public_user_by_public'),
    path('create/', views.create_public_user, name='create_public_user'),
    # Grievance-related URLs
    path(('grievance/<str:grievance_id>/'), detail_grievance, name='detail_grievance'),
    path(('grievance/<str:grievance_id>/edit/'), update_grievance, name='update_grievance'),
    path(('grievance/<str:grievance_id>/delete/'), delete_grievance, name='delete_grievance'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)