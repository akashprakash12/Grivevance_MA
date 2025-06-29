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
app_name = 'public_user'  # Important for namespacing

urlpatterns = [
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', views.user_dashboard, name='user_dashboard'),
    path(('view/'), view_grievances, name='view_grievances'),
    path(('update/<str:username>/'), views.update_public_user, name='update_public_user'),
    path(('delete/<str:username>/'), views.delete_public_user, name='delete_public_user'),
    path(('submit-complaint/'), create_grievance, name='submit_complaint'),
    path(('help/'), views.help, name='help'),
    path(('account_settings/'), views.account_settings, name='account_settings'),
    path('ajax/load-departments/', load_departments, name='ajax_load_departments'),
    
    # Grievance-related URLs
    path(('grievance/<str:grievance_id>/'), detail_grievance, name='detail_grievance'),
    path(('grievance/<str:grievance_id>/edit/'), update_grievance, name='update_grievance'),
    path(('grievance/<str:grievance_id>/delete/'), delete_grievance, name='delete_grievance'),
    
    path(('account_settings/verify-2fa/'), views.verify_2fa, name='verify_2fa'),
    path(('account_settings/disable-2fa/'), views.disable_2fa, name='disable_2fa'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)