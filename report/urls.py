from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports, name='reports'),   # ✅ FIXED

    path('list/', views.report_list, name='report_list'),
    path('pdf/<int:report_id>/', views.generate_pdf, name='generate_pdf'),
    path('download-all/', views.download_all_reports, name='download_all_reports'),

    path('ai-suggestions/', views.ai_suggestions, name='ai_suggestions'),
]