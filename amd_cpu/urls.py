# amd_cpu/urls.py
from django.urls import path
from . import views

app_name = 'amd_cpu'

urlpatterns = [
    path('', views.amd_search_view, name='search'),
]