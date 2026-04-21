"""
URL configuration for qr_billing project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import login_view   # 👈 change here

urlpatterns = [
    path('admin/', admin.site.urls),

    # 👇 Project start hote hi login page open hoga
    path('', login_view, name='home'),

   path('billing/', include('billing.urls')),

    path('accounts/', include('accounts.urls')),
     path('', include('products.urls')), 
        path('invoice/', include('invoice.urls')),
   
     path('reports/', include('report.urls')),
        path('',include('notifications.urls')),
        path('integrations/', include('integrations.urls')),
        path("subscriptions/", include("subscriptions.urls")),
       
        
]

# Media files serve (Profile images ke liye)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)