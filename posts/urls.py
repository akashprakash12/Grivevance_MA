from django.urls import path
from . import views
app_name = 'posts'  # <--- VERY IMPORTANT
urlpatterns = [
    path('', views.index, name='index'),
    path('manage/', views.manage_posts, name='manage_posts'),
    path('edit/<str:post_id>/', views.edit_post, name='edit_post'),
    path('delete/<str:post_id>/', views.delete_post, name='delete_post'),
    path('comments/<str:post_id>/', views.get_comments, name='get_comments'),
    path('download/<str:post_id>/', views.download_excel, name='download_excel'),
]