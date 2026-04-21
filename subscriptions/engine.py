from django.utils import timezone
from .models import Subscription
from invoice.models import Invoice, InvoiceItem


def run_subscription_engine():

    today = timezone.localdate()

    subs = Subscription.objects.filter(
        status="ACTIVE",
        next_delivery_date=today
    )

    for sub in subs:

        delivery = sub.deliveries.filter(
            delivery_date=today,
            is_delivered=False
        ).first()

        if not delivery:
            continue

        # ✅ SAFE CHECK (duplicate avoid)
        if delivery.invoice_created:
            continue

        # ✅ CREATE INVOICE
        invoice = Invoice.objects.create(
            customer=sub.user,
            total_amount=sub.product.price * sub.quantity
        )

        InvoiceItem.objects.create(
            invoice=invoice,
            product=sub.product,
            quantity=sub.quantity
        )

        # ✅ UPDATE DELIVERY
        delivery.invoice_created = True
        delivery.is_delivered = True
        delivery.delivered_at = timezone.now()   # 🔥 IMPORTANT
        delivery.save()

        # ✅ NEXT DELIVERY UPDATE
        sub.update_next_delivery()