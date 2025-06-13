from django.urls import path
from . import views
app_name = 'core'

urlpatterns = [
    # Department URLs
    path('department/list/', views.department_list, name='department_list'),
    path('department/create/', views.department_create, name='create_department'),
    path('department/update/<str:code>/', views.department_update, name='department_update'),
    path('department/delete/<str:code>/', views.department_delete, name='department_delete'),

    # District URLs
    path('district/list/', views.district_list, name='district_list'),
    path('district/create/', views.district_create, name='district_create'),
    path('district/update/<str:code>/', views.district_update, name='district_update'),
    path('district/delete/<str:code>/', views.district_delete, name='district_delete'),
]
