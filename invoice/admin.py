from django.contrib import admin
from .models import Invoice, InvoiceItem


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):

    list_display = (
        'invoice_number',
        'customer',
        'total_amount',
        'payment_status',
        'date'
    )

    list_filter = (
        'payment_status',
        'date'
    )

    search_fields = (
        'invoice_number',
        'customer__username'
    )

    ordering = ('-date',)

    list_per_page = 10


# 👇 Inline items (🔥 powerful feature)
class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):

    list_display = (
        'invoice',
        'product',
        'quantity',
        'subtotal'
    )

    search_fields = (
        'product__name',
    )