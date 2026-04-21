from django.db import models
from django.conf import settings
from products.models import Product
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class Subscription(models.Model):

    PLAN_CHOICES = [
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('PAUSED', 'Paused'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES)
    start_date = models.DateField(default=timezone.localdate)

    duration_days = models.PositiveIntegerField(default=0)
    end_date = models.DateField(null=True, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    next_delivery_date = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    # =========================
    # PAYMENT FIELDS
    # =========================
    is_paid = models.BooleanField(default=False)
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)

    # =========================
    # SAVE METHOD
    # =========================
    def save(self, *args, **kwargs):

        # PLAN LOGIC
        if self.plan_type == "WEEKLY":
            self.duration_days = 7
            discount_percent = Decimal("5")
        else:
            self.duration_days = 30
            discount_percent = Decimal("10")

        # PRICE CALCULATION
        self.subtotal = self.product.price * self.quantity * self.duration_days
        self.discount = (self.subtotal * discount_percent) / Decimal("100")
        self.total_amount = self.subtotal - self.discount

        # DATE CALCULATION
        self.end_date = self.start_date + timedelta(days=self.duration_days - 1)

        is_new = self.pk is None

        super().save(*args, **kwargs)

        # CREATE DELIVERY ONLY FIRST TIME
        if is_new:
            self.create_deliveries()

    # =========================
    # CREATE DELIVERIES
    # =========================
    def create_deliveries(self):
        for i in range(self.duration_days):
            Delivery.objects.create(
                subscription=self,
                delivery_date=self.start_date + timedelta(days=i)
            )

        self.next_delivery_date = self.start_date
        super().save(update_fields=['next_delivery_date'])

    # =========================
    # UPDATE NEXT DELIVERY
    # =========================
    def update_next_delivery(self):
        next_delivery = self.deliveries.filter(
            is_delivered=False
        ).order_by("delivery_date").first()

        if next_delivery:
            self.next_delivery_date = next_delivery.delivery_date
        else:
            self.next_delivery_date = None

        self.save(update_fields=['next_delivery_date'])

    # =========================
    # REMAINING DAYS
    # =========================
    def remaining_days(self):
        if self.end_date:
            return (self.end_date - timezone.localdate()).days
        return 0

    # =========================
    # ✅ PAYMENT STATUS FIX
    # =========================
    @property
    def payment_status(self):
        return "PAID" if self.is_paid else "PENDING"

    # =========================
    # ✅ CUSTOMER NAME FIX
    # =========================
    def get_customer_name(self):
        # If customer_profile exists
        if hasattr(self.user, "customer_profile"):
            return self.user.customer_profile.full_name

        # fallback
        name = f"{self.user.first_name} {self.user.last_name}".strip()
        return name if name else self.user.username

    # =========================
    # STRING DISPLAY
    # =========================
    def __str__(self):
        return f"{self.get_customer_name()} - {self.product.name}"


# ==========================================
# DELIVERY MODEL
# ==========================================
class Delivery(models.Model):

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="deliveries"
    )

    delivery_date = models.DateField()
    is_delivered = models.BooleanField(default=False)

    invoice_created = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.subscription.get_customer_name()} - {self.delivery_date}"