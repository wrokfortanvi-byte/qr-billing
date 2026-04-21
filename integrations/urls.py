from django.urls import path
from .views import integrations_page, toggle_integration

urlpatterns = [
    path('', integrations_page, name='integrations_page'),
    path('toggle/', toggle_integration, name='toggle_integration'),
]