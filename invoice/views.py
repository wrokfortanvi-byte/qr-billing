from os import name

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from subscriptions.models import Subscription
import razorpay
from twilio.rest import Client



from .models import Invoice, InvoiceItem
from products.models import Product
from notifications.models import Notification
from integrations.models import Integration   # 🔥 NEW IMPORT

User = get_user_model()


# =========================
# ✅ WHATSAPP FUNCTION
# =========================
def send_whatsapp_message(phone, message):
    try:
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )

        client.messages.create(
            body=message,
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to="whatsapp:" + phone
        )

        print("✅ WhatsApp Sent")

    except Exception as e:
        print("❌ WhatsApp Error:", str(e))


# ========================
# ✅ NOTIFICATION FUNCTION
# =========================
def create_notification(user, title, message, type):
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=type,
        is_read=False
    )
@login_required
def billing_list(request):

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    # =====================================================
    # POST → CREATE INVOICE
    # =====================================================
    if request.method == "POST":

        customer_id = request.POST.get("customer")
        product_ids = request.POST.getlist("product[]")
        quantities = request.POST.getlist("quantity[]")
        discounts = request.POST.getlist("discount[]")

        if not any(product_ids):
            return redirect("invoice_list")

        try:
            customer = User.objects.get(id=customer_id)

            with transaction.atomic():

                # =========================
                # CREATE INVOICE
                # =========================
                invoice = Invoice.objects.create(customer=customer)

                for product_id, qty, disc in zip(product_ids, quantities, discounts):
                    if product_id:
                        product = Product.objects.get(id=product_id)

                        InvoiceItem.objects.create(
                            invoice=invoice,
                            product=product,
                            quantity=int(qty or 1),
                            discount=Decimal(disc or 0)
                        )

                invoice.refresh_from_db()

                # =========================
                # RAZORPAY ORDER
                # =========================
                try:
                    payment = client.order.create({
                        "amount": int(invoice.total_amount * 100),
                        "currency": "INR",
                        "payment_capture": 1,
                        "notes": {
                            "invoice_id": str(invoice.id)   # 🔥 IMPORTANT FIX
                        }
                    })

                    invoice.razorpay_order_id = payment["id"]
                    invoice.save()
                except Exception as rzp_e:
                    print("❌ Razorpay Order Creation Error:", str(rzp_e))
                    # Allow invoice creation to proceed even if Razorpay credentials fail

                # =========================
                # NOTIFICATIONS - CUSTOMER
                # =========================
                create_notification(
                    customer,
                    "Invoice Generated",
                    f"Invoice {invoice.invoice_number} created (₹{invoice.total_amount})",
                    "info"
                )

                create_notification(
                    customer,
                    "Payment Pending",
                    f"Please pay invoice {invoice.invoice_number}",
                    "warning"
                )

                # =========================
                # NOTIFICATIONS - ADMINS
                # =========================
                admins = User.objects.filter(is_staff=True)

                for admin in admins:
                    create_notification(
                        admin,
                        "Invoice Created",
                        f"Invoice {invoice.invoice_number} for {customer.username}",
                        "success"
                    )

                # =========================
                # WHATSAPP (SAFE FIX)
                # =========================
                try:
                    phone = getattr(customer, "phone", None)

                    if not phone:
                        print("❌ Phone not found for:", customer.username)
                    else:
                        phone = str(phone).strip().replace(" ", "")

                        if phone.startswith("+91"):
                            phone = phone[3:]
                        elif phone.startswith("91"):
                            phone = phone[2:]

                        phone = "+91" + phone

                        
                        message = (
    f"🧾 *INVOICE GENERATED*\n"
    f"━━━━━━━━━━━━━━━━━━━━\n"
    f"👤 *Customer:* {customer.username}\n"
    f"📄 *Invoice No:* {invoice.invoice_number}\n"
    f"💰 *Amount:* ₹{invoice.total_amount}\n"
    f"📌 *Status:* Pending\n"
    f"━━━━━━━━━━━━━━━━━━━━\n"
    f"🙏 Thank you for your business!\n"
    f"🏢 *QR Billing Assistant*"
)
                        send_whatsapp_message(phone, message)

                except Exception as e:
                    print("❌ WhatsApp Error:", str(e))

                return redirect("invoice_list")

        except User.DoesNotExist:
            print("❌ Customer not found")
            return JsonResponse({"error": "Customer not found"})

        except Exception as e:
            print("❌ ERROR:", str(e))
            return JsonResponse({"error": str(e)})

    # =====================================================
    # GET → SHOW INVOICES
    # =====================================================
    search_query = request.GET.get("search")
    invoices = Invoice.objects.all().order_by("-date")

    today = timezone.now().date()

    # AUTO OVERDUE UPDATE
    for invoice in invoices:
        if invoice.payment_status == "PENDING":
            if today > invoice.date.date() + timedelta(days=2):
                invoice.payment_status = "OVERDUE"
                invoice.save()

    # SEARCH FILTER
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(customer__username__icontains=search_query)
        )

    return render(request, "dashboard/billing.html", {
        "invoices": invoices,
        "customers": User.objects.filter(is_staff=False),
        "products": Product.objects.all(),
        "RAZORPAY_KEY_ID": settings.RAZORPAY_KEY_ID,
        "page_title": "Billing",
        "page_subtitle": "Manage your invoices",
    })
@csrf_exempt
def payment_success(request):

    # =========================
    # ONLY POST ALLOWED
    # =========================
    if request.method != "POST":
        return JsonResponse({
            "status": "error",
            "msg": "Invalid request method"
        })

    try:
        import json, logging, traceback
        from django.utils import timezone

        logger = logging.getLogger(__name__)

        data = json.loads(request.body)
        
        # 📝 TEMPORARY DEBUG LOG
        with open("payment_debug.log", "a") as f:
            f.write(f"\n[{timezone.now()}] CALLBACK RECEIVED: {data}\n")

        logger.info(f"PAYMENT CALLBACK DATA: {data}")

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        # =========================
        # VERIFY SIGNATURE
        # =========================
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_signature = data.get("razorpay_signature")

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            logger.error("Missing payment data in callback")
            return JsonResponse({"status": "error", "msg": "Missing payment details"})

        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            })
        except Exception as sig_err:
            logger.error(f"Signature Verification Failed: {str(sig_err)}")
            return JsonResponse({"status": "error", "msg": "Invalid payment signature"})

        with transaction.atomic():

            # 🔍 FETCH ORDER TO GET NOTES (IF ANY)
            try:
                order = client.order.fetch(razorpay_order_id)
                notes = order.get("notes") or {}
            except Exception as e:
                logger.warning(f"Could not fetch order notes: {str(e)}")
                notes = {}

            invoice_id = notes.get("invoice_id")
            subscription_id = notes.get("subscription_id")

            invoice = None
            subscription = None

            # =====================================================
            # 🧾 1. FIND INVOICE (By ID or Order ID)
            # =====================================================
            if invoice_id:
                invoice = Invoice.objects.select_for_update().filter(id=int(invoice_id)).first()
            
            if not invoice:
                invoice = Invoice.objects.select_for_update().filter(razorpay_order_id=razorpay_order_id).first()

            if invoice:
                if invoice.payment_status == "PAID":
                    return JsonResponse({"status": "success", "type": "invoice", "msg": "Already paid"})

                invoice.payment_status = "PAID"
                invoice.razorpay_payment_id = razorpay_payment_id
                invoice.save()

                create_notification(
                    invoice.customer,
                    "Payment Successful",
                    f"Payment received for invoice {invoice.invoice_number} (₹{invoice.total_amount})",
                    "success"
                )

                # WhatsApp Notification
                try:
                    phone = getattr(invoice.customer, "phone", None)
                    if phone:
                        phone = str(phone).strip().replace(" ", "")
                        if phone.startswith("+91"): phone = phone[3:]
                        elif phone.startswith("91"): phone = phone[2:]
                        phone = "+91" + phone

                        message = (
                            f"✅ *PAYMENT SUCCESSFUL*\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 *Customer:* {invoice.customer.username}\n"
                            f"📄 *Invoice No:* {invoice.invoice_number}\n"
                            f"💰 *Paid Amount:* ₹{invoice.total_amount}\n"
                            f"🧾 *Payment ID:* {razorpay_payment_id}\n"
                            f"📅 *Date:* {timezone.localtime().strftime('%d %b %Y')}\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🎉 Your payment has been received successfully!\n"
                            f"🙏 Thank you for your business!\n"
                            f"🏢 *QR Billing Assistant*"
                        )
                        send_whatsapp_message(phone, message)
                except Exception as ws_e:
                    logger.error(f"WhatsApp Success Error: {str(ws_e)}")

                # Admin Notification
                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    create_notification(admin, "Payment Received", f"{invoice.customer.username} paid invoice {invoice.invoice_number}", "success")

                return JsonResponse({"status": "success", "type": "invoice"})

            # =====================================================
            # 📦 2. FIND SUBSCRIPTION (By ID or Order ID)
            # =====================================================
            if subscription_id:
                subscription = Subscription.objects.select_for_update().filter(id=int(subscription_id)).first()

            if not subscription:
                subscription = Subscription.objects.select_for_update().filter(razorpay_order_id=razorpay_order_id).first()

            if subscription:
                if subscription.is_paid:
                    return JsonResponse({"status": "success", "type": "subscription", "msg": "Already active"})

                subscription.status = "ACTIVE"
                subscription.is_paid = True
                subscription.razorpay_payment_id = razorpay_payment_id
                subscription.save()

                create_notification(
                    subscription.user,
                    "Subscription Activated",
                    "Your subscription is active 🎉",
                    "success"
                )

                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    create_notification(admin, "Subscription Activated", f"{subscription.user.username} activated subscription", "success")

                return JsonResponse({"status": "success", "type": "subscription"})

            # =========================
            # NO DATA FOUND
            # =========================
            logger.error(f"Payment verified but no invoice/subscription found for Order ID: {razorpay_order_id}")
            return JsonResponse({
                "status": "error",
                "msg": "Order verification failed: No matching invoice or subscription found."
            })

    except Exception as e:
        logger.error(f"PAYMENT SUCCESS ERROR: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            "status": "error",
            "msg": "Internal server error during payment verification"
        })

@login_required
def view_invoice(request, invoice_id):
    invoice = get_object_or_404(
        Invoice,
        id=invoice_id,
        customer=request.user
    )
    return render(request, "dashboard/view_invoice.html", {"invoice": invoice})




# =========================
# DOWNLOAD PDF
# =========================
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

@login_required
def download_invoice(request, invoice_id):

    invoice = get_object_or_404(
        Invoice,
        id=invoice_id,
        customer=request.user
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os

    font_path = os.path.join(os.path.dirname(__file__), "font", "DejaVuSans.ttf")
    pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))

    width, height = A4
    rupee = u"\u20B9"

    # ================= OUTER BOX =================
    p.setStrokeColor(colors.grey)
    p.rect(40, 40, width-80, height-80)

    y = height - 80

    # ================= HEADER =================
    p.setFont("DejaVuSans", 18)
    p.drawString(50, y, "QR Billing Assistant")

    p.setFont("DejaVuSans", 10)
    p.drawRightString(width-50, y, f"Invoice: {invoice.invoice_number}")

    y -= 20
    from django.utils import timezone

# DATE
    local_date = timezone.localtime(invoice.date)

    p.drawRightString(width-50, y, f"Date: {local_date.strftime('%d %b %Y')}")
    y -= 30

    # ================= PAYMENT STATUS =================
    if invoice.payment_status != "PAID":
        p.setFillColorRGB(1, 0, 0)  # red
        p.setFont("DejaVuSans", 12)
        p.drawString(50, y, "⚠ PAYMENT PENDING")

        y -= 15
        p.setFont("DejaVuSans", 9)
        p.drawString(50, y, "Please complete your payment to validate this invoice.")

        p.setFillColorRGB(0, 0, 0)
        y -= 25
    else:
        p.setFillColorRGB(0, 0.6, 0)  # green
        p.setFont("DejaVuSans", 12)
        p.drawString(50, y, "✔ PAID")

        p.setFillColorRGB(0, 0, 0)
        y -= 25

    # ================= CUSTOMER =================
    p.setFont("DejaVuSans", 11)
    p.drawString(50, y, "Bill To:")
    y -= 15

    p.setFont("DejaVuSans", 10)
    p.drawString(50, y, invoice.customer.username)

    y -= 30

    # ================= TABLE HEADER =================
    p.setFillColor(colors.lightgrey)
    p.rect(50, y, width-100, 25, fill=1)

    p.setFillColor(colors.black)
    p.setFont("DejaVuSans", 10)

    p.drawString(55, y+8, "Product")
    p.drawString(270, y+8, "Qty")
    p.drawString(330, y+8, "Price")
    p.drawString(420, y+8, "Subtotal")

    y -= 25

    # ================= ITEMS =================
    for item in invoice.items.all():

        p.drawString(55, y, item.product.name[:25])
        p.drawString(280, y, str(item.quantity))
        p.drawString(330, y, f"{rupee}{item.product.price}")
        p.drawString(420, y, f"{rupee}{item.subtotal}")

        y -= 20

        p.setStrokeColor(colors.lightgrey)
        p.line(50, y+5, width-50, y+5)

        if y < 120:
            p.showPage()
            p.setFont("DejaVuSans", 10)
            y = height - 80

    # ================= TOTAL =================
    y -= 20

    p.setFillColor(colors.lightgrey)
    p.rect(300, y, 200, 35, fill=1)

    p.setFillColor(colors.black)
    p.setFont("DejaVuSans", 12)
    p.drawString(310, y+12, "Total")

    p.setFont("DejaVuSans", 13)
    p.drawRightString(490, y+12, f"{rupee}{invoice.total_amount}")

    # ================= WATERMARK =================
    if invoice.payment_status != "PAID":
        p.saveState()
        p.setFont("DejaVuSans", 50)
        p.setFillColorRGB(1, 0.8, 0.8)
        p.translate(300, 400)
        p.rotate(45)
        p.drawCentredString(0, 0, "UNPAID")
        p.restoreState()

    # ================= FOOTER =================
    y -= 60
    p.setFont("DejaVuSans", 9)
    p.drawCentredString(width/2, y, "Thank you for your business!")

    p.save()
    return response


# =========================
# CUSTOMER INVOICES
# =========================
@login_required
def my_invoices(request):

    invoices = Invoice.objects.filter(
        customer=request.user
    ).order_by("-date")

    return render(request, "dashboard/my_invoices.html", {
        "invoices": invoices,
        "RAZORPAY_KEY_ID": settings.RAZORPAY_KEY_ID
    })


# =========================
# CUSTOMER DOWNLOADS
# =========================
@login_required
def customer_downloads(request):

    invoices = Invoice.objects.filter(
        customer=request.user,
        payment_status="PAID"
    ).order_by("-date")

    return render(request, "dashboard/customer_downloads.html", {
        "invoices": invoices
    })












