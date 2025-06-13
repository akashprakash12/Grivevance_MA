from django.urls import path
from officer import views
app_name = 'officer'

urlpatterns = [
    path('create/', views.create_officer, name='create_officer'),
    path('update/<str:username>/', views.update_officer, name='update_officer'),
    path('delete/<str:username>/', views.delete_officer, name='delete_officer'),
    path('view/', views.view_officers, name='view_officers'),
]
