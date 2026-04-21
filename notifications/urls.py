from django.urls import path
from . import views

urlpatterns = [

    path('notifications/', views.notifications_view, name='notifications'),

    # 🔔 API for sound
    path('notifications/latest/', views.latest_notification, name='latest_notification'),
    # ⭐ NEW
    path('notifications/count/', views.notification_count, name='notification_count'),


]