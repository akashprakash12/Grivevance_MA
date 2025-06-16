from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('comments-status/', views.get_comments_status, name='comments_status'),
]