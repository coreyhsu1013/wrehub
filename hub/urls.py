from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("permits/", views.permit_list, name="permit_list2"),
    path("permits/<int:pk>/", views.permit_detail, name="permit_detail"),
    path("permits/export.csv", views.permit_export_csv, name="permit_export_csv"),
    path("compare/", views.permit_compare, name="permit_compare"),
    path("urban-renewal/", views.compare_urban_renewal, name="compare_urban_renewal"),
]