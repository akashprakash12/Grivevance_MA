from django.urls import path
from . import views

app_name = 'public_user'  # <--- VERY IMPORTANT

urlpatterns = [
    path('create/', views.create_public_user, name='create_public_user'),
    path('view/', views.view_public_users, name='view_public_users'),
    path('update/<str:username>/', views.update_public_user, name='update_public_user'),
    path('delete/<str:username>/', views.delete_public_user, name='delete_public_user'),
]
