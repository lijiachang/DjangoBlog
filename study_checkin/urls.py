from django.urls import path

from . import views

app_name = 'study_checkin'

urlpatterns = [
    path('', views.checkin_view, name='checkin'),
    path('summary/', views.summary_view, name='summary'),
    path('api/verify/', views.verify_password, name='api_verify'),
    path('api/start/', views.start_session, name='api_start'),
    path('api/end/', views.end_session, name='api_end'),
    path('api/today/', views.get_today_sessions, name='api_today'),
    path('api/summary-data/', views.get_summary_data, name='api_summary_data'),
]
