from django.urls import path
from .views import (
    admin_dashboard,
    customer_dashboard,
    admin_customers,
    add_customer,
    get_notifications,
    mark_notifications_read,
    global_search,
    customer_notifications,
    notification_count,
    customer_search   # ✅ ADD THIS
)

urlpatterns = [

    path('dashboard/', admin_dashboard, name='admin_dashboard'),

    path('customer-dashboard/', customer_dashboard, name='customer_dashboard'),

    path('customers/', admin_customers, name='admin_customers'),

    path('customers/add/', add_customer, name='add_customer'),

    # 🔔 Notifications API
    path('notifications/', get_notifications, name='get_notifications'),
    path('notifications/read/', mark_notifications_read, name='mark_notifications_read'),
    path('notifications/count/', notification_count, name='notification_count'),

    # 🔎 Search
    path("search/", global_search, name="global_search"),

    # 🔔 Customer notifications page
    path(
        'customer-notifications/',
        customer_notifications,
        name='customer_notifications'
    ),

    # 🔎 Customer Search
    path("customer-search/", customer_search, name="customer_search"),
    

]