from django.urls import path
from . import views

app_name = "district_officer"

urlpatterns = [
    path("create/",                 views.create_district_officer,  name="create_district_officer"),
    path("list/",                   views.view_district_officers,   name="view_district_officers"),
    path("edit/<str:officer_id>/",  views.update_district_officer,  name="update_district_officer"),
    path("delete/<str:officer_id>/",views.delete_district_officer,  name="delete_district_officer"),
]
