from django.contrib import admin
from .models import Subscription, Delivery


# =========================
# DELIVERY INLINE (inside subscription)
# =========================
class DeliveryInline(admin.TabularInline):
    model = Delivery
    extra = 0
    readonly_fields = ("delivery_date", "is_delivered")
    can_delete = False


# =========================
# SUBSCRIPTION ADMIN
# =========================
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "product",
        "plan_type",
        "quantity",
        "duration_days",
        "subtotal",
        "discount",
        "total_amount",
        "status",
        "start_date",
        "end_date",
    )

    list_filter = ("plan_type", "status", "start_date")
    search_fields = ("user__username", "product__name")

    readonly_fields = (
        "duration_days",
        "subtotal",
        "discount",
        "total_amount",
        "end_date",
        "next_delivery_date",
    )

    inlines = [DeliveryInline]

    ordering = ("-id",)


# =========================
# DELIVERY ADMIN
# =========================
@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "subscription",
        "delivery_date",
        "is_delivered",
    )

    list_filter = ("is_delivered", "delivery_date")
    search_fields = ("subscription__user__username",)

    ordering = ("-delivery_date",)