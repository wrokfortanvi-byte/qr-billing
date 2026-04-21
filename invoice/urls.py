from django.urls import path
from . import views

urlpatterns = [

    path("", views.billing_list, name="invoice_list"),

    # ❌ REMOVE THIS (error wali line)
    # path("paid/<int:invoice_id>/", views.mark_invoice_paid, name="invoice_paid"),

    path("payment-success/", views.payment_success, name="payment_success"),
    path("invoice/view/<int:invoice_id>/", views.view_invoice, name="view_invoice"),
    path("invoice/download/<int:invoice_id>/", views.download_invoice, name="download_invoice"),
    path("my-invoices/", views.my_invoices, name="my_invoices"),
    path("downloads/", views.customer_downloads, name="customer_downloads"),
     #🔥 ADD THIS LINE


]