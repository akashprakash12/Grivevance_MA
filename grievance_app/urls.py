from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_grievance, name='create_grievance'),
    path('list/', views.view_grievances, name='grievance_list'),
    path('detail/<str:grievance_id>/', views.detail_grievance, name='grievance_detail'),
    path('update/<str:grievance_id>/', views.update_grievance, name='update_grievance'),
    path('delete/<str:grievance_id>/', views.delete_grievance, name='delete_grievance'),
]
