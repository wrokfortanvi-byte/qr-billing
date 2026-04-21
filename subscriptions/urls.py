from django.urls import path
from . import views

urlpatterns = [

    # 👨‍💼 ADMIN
    path("admin/subscriptions/", views.subscription_page, name="subscription_page"),

    # 👤 CUSTOMER
    path("my-subscriptions/", views.customer_subscriptions, name="customer_subscriptions"),

    # 🔁 ACTIONS (Better naming)
    path("subscription/<int:id>/pause/", views.pause_subscription, name="pause_subscription"),
    path("subscription/<int:id>/resume/", views.resume_subscription, name="resume_subscription"),
    path("subscription/<int:id>/cancel/", views.cancel_subscription, name="cancel_subscription"),
    path('subscription/pdf/<int:id>/', views.download_subscription_pdf, name='subscription_pdf'),
    
]