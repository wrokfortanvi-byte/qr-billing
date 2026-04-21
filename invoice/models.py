from django.db import models
from django.conf import settings
from products.models import Product
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# ✅ ADD THIS IMPORT
from subscriptions.models import Subscription


class Invoice(models.Model):

    PAYMENT_STATUS = [
        ('PAID', 'Paid'),
        ('PENDING', 'Pending'),
        ('OVERDUE', 'Overdue'),
    ]

    INVOICE_TYPE = [
        ("PRODUCT", "Product"),
        ("SUBSCRIPTION", "Subscription"),
    ]

    invoice_number = models.CharField(max_length=20, unique=True, blank=True)

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    # ✅ NEW FIELD (LINK SUBSCRIPTION)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    # ✅ NEW FIELD (TYPE)
    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPE,
        default="PRODUCT"
    )

    date = models.DateTimeField(auto_now_add=True)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='PENDING'
    )

    razorpay_order_id = models.CharField(max_length=200, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=200, blank=True, null=True)

    # =====================================
    # 🔢 AUTO INVOICE NUMBER
    # =====================================
    def save(self, *args, **kwargs):

        if not self.invoice_number:
            last_invoice = Invoice.objects.order_by('-id').first()

            if last_invoice and last_invoice.invoice_number:
                try:
                    last_number = int(last_invoice.invoice_number.replace('INV', ''))
                except:
                    last_number = 0
                new_number = last_number + 1
            else:
                new_number = 1

            self.invoice_number = f"INV{new_number:03d}"

        super().save(*args, **kwargs)

    # =====================================
    # ⏰ OVERDUE CHECK
    # =====================================
    def check_overdue(self):
        if self.payment_status == "PENDING":
            if self.date and self.date + timedelta(days=2) < timezone.now():
                self.payment_status = "OVERDUE"
                self.save()

    def __str__(self):
        return self.invoice_number


# =========================================
# ✅ INVOICE ITEM
# =========================================

class InvoiceItem(models.Model):

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField()

    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):

        is_new = self.pk is None

        price = Decimal(self.product.price)
        gst_rate = Decimal(self.product.gst_rate)
        qty = Decimal(self.quantity)

        # =========================
        # 💰 CALCULATIONS
        # =========================
        base_total = price * qty

        discount_percent = Decimal(self.discount) / Decimal(100)
        discount_amount = base_total * discount_percent

        after_discount = base_total - discount_amount

        gst = after_discount * (gst_rate / Decimal(100))
        self.gst_amount = gst

        self.subtotal = after_discount + gst

        # =========================
        # ❌ STOCK CHECK
        # =========================
        if is_new:
            if self.product.stock < int(self.quantity):
                raise ValueError(f"{self.product.name} is out of stock")

        super().save(*args, **kwargs)

        # =========================
        # 🔥 STOCK REDUCE
        # =========================
        if is_new:
            product = self.product
            product.stock = product.stock - int(self.quantity)
            product.save()

        # =========================
        # 🧾 UPDATE INVOICE TOTAL
        # =========================
        total = self.invoice.items.aggregate(
            total=models.Sum("subtotal")
        )["total"] or 0

        self.invoice.total_amount = total
        self.invoice.save(update_fields=["total_amount"])

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
