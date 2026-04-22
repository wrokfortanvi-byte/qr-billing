from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse, HttpResponse

import razorpay
import json
import os
import random

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import Subscription
from products.models import Product
from invoice.models import Invoice
from notifications.models import Notification
import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)



User = get_user_model()


# ==========================================
# ✅ COMMON HELPER (🔥 NAME FIX)
# ==========================================
def get_customer_name(user):
    # अगर profile hai
    if hasattr(user, "customer_profile"):
        return user.customer_profile.full_name

    # fallback
    name = f"{user.first_name} {user.last_name}".strip()
    return name if name else user.username


# ==========================================
# NOTIFICATION FUNCTION
# ==========================================
def create_notification(user, title, message, type):
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=type,
        is_read=False
    )


# ==========================================
# ADMIN SUBSCRIPTION PAGE
# ==========================================
@login_required
def subscription_page(request):

    customers = User.objects.filter(is_superuser=False)

    if request.method == "POST":

        product_id = request.POST.get("product")
        plan = request.POST.get("plan")
        qty = int(request.POST.get("quantity") or 1)
        user_id = request.POST.get("user")

        product = get_object_or_404(Product, id=product_id)
        user = get_object_or_404(User, id=user_id)

        subscription = Subscription.objects.create(
            user=user,
            product=product,
            quantity=qty,
            plan_type=plan,
            start_date=timezone.localdate(),
            status="ACTIVE"   # ✅ FIX (PENDING हटाया)
        )

        # 🔔 CUSTOMER
        create_notification(
            subscription.user,
            "Subscription Payment Pending",
            "Your subscription payment is pending.",
            "warning"
        )

        # 🔔 ADMIN
        admins = User.objects.filter(is_staff=True)

        for admin in admins:
            create_notification(
                admin,
                "Subscription Pending",
                f"{get_customer_name(subscription.user)} has pending subscription payment.",
                "warning"
            )

        return redirect("subscription_page")

    subscriptions = Subscription.objects.select_related("user", "product").order_by("-id")

    return render(request, "dashboard/subscriptions.html", {
        "subscriptions": subscriptions,
        "products": Product.objects.all(),
        "users": customers,
        "page_title": "Subscriptions",
        "page_subtitle": "Manage customer subscriptions and recurring orders",
    })


# ==========================================
# CUSTOMER SUBSCRIPTIONS
# ==========================================
@login_required
def customer_subscriptions(request):

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    subscriptions = Subscription.objects.filter(user=request.user)\
        .select_related("product")\
        .order_by("-id")

    data = []

    for sub in subscriptions:

        # ==============================
        # 💳 CREATE ORDER (SAFE)
        # ==============================
        if not sub.is_paid and not sub.razorpay_order_id:
            try:
                payment = client.order.create({
                    "amount": int(sub.total_amount * 100),
                    "currency": "INR",
                    "payment_capture": 1,
                    "notes": {
                        "subscription_id": str(sub.id)
                    }
                })

                sub.razorpay_order_id = payment["id"]
                sub.save()

            except Exception as e:
                print("Razorpay Error:", e)

        invoice = Invoice.objects.filter(subscription=sub).first()

        # ==============================
        # 🤖 AI VARIABLES
        # ==============================
        ai_msg = ""
        upgrade_msg = ""

        # ==============================
        # ⏳ DAYS LEFT SAFE
        # ==============================
        try:
            days_left = sub.remaining_days()
        except:
            days_left = 0

        # ==============================
        # 🔔 EXPIRY MESSAGE (NO SPAM)
        # ==============================
        if 0 < days_left <= 2:

            # check notification already exists
            already_sent = Notification.objects.filter(
                user=sub.user,
                title="Expiry Alert",
                message__icontains=sub.product.name
            ).exists()

            if not already_sent:
                ai_msg = generate_ai_expiry_message(sub)

                create_notification(
                    sub.user,
                    "Expiry Alert",
                    ai_msg,
                    "warning"
                )
            else:
                ai_msg = "Your subscription is ending soon."

        # ==============================
        # 🚀 UPGRADE SUGGESTION
        # ==============================
        if sub.status == "ACTIVE":

            try:
                upgrade_msg = generate_ai_upgrade_suggestion(sub)
            except:
                upgrade_msg = "Upgrade to a better plan and save more."

        # ==============================
        # 📦 FINAL DATA
        # ==============================
        data.append({
            "sub": sub,
            "invoice": invoice,
            "ai_msg": ai_msg,
            "upgrade_msg": upgrade_msg
        })

    return render(request, "dashboard/customer_subscriptions.html", {
        "data": data,
        "RAZORPAY_KEY_ID": settings.RAZORPAY_KEY_ID,
    })
import razorpay

# ==========================================
# PAUSE / RESUME / CANCEL
# ==========================================
@login_required
def pause_subscription(request, id):
    sub = get_object_or_404(Subscription, id=id)
    sub.status = "PAUSED"
    sub.save()
    return redirect("subscription_page")


@login_required
def resume_subscription(request, id):
    sub = get_object_or_404(Subscription, id=id)
    sub.status = "ACTIVE"
    sub.save()
    return redirect("subscription_page")


@login_required
def cancel_subscription(request, id):
    sub = get_object_or_404(Subscription, id=id)
    sub.status = "CANCELLED"
    sub.save()
    return redirect("subscription_page")
@login_required
def download_subscription_pdf(request, id):

    sub = get_object_or_404(Subscription, id=id, user=request.user)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="subscription_{sub.id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os

    font_path = os.path.join(settings.BASE_DIR, "invoice", "font", "DejaVuSans.ttf")
    pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))

    width, height = A4
    rupee = u"\u20B9"

    # ================= OUTER BOX =================
    p.setStrokeColor(colors.grey)
    p.rect(40, 40, width - 80, height - 80)

    y = height - 70

    # ================= HEADER =================
    p.setFont("DejaVuSans", 18)
    p.drawString(60, y, "QR Billing Assistant")

    p.setFont("DejaVuSans", 10)
    p.drawRightString(width - 60, y, f"Subscription: {sub.id}")

    y -= 18

    from django.utils import timezone
    local_date = timezone.localtime()
    p.drawRightString(width - 60, y, f"Date: {local_date.strftime('%d %b %Y')}")

    y -= 35

    # ================= STATUS =================
    if not sub.is_paid:
        p.setFillColorRGB(1, 0, 0)
        p.setFont("DejaVuSans", 12)
        p.drawString(60, y, "⚠ PAYMENT PENDING")

        y -= 18
        p.setFont("DejaVuSans", 9)
        p.drawString(60, y, "Please complete your payment to activate subscription.")

        p.setFillColorRGB(0, 0, 0)
        y -= 30
    else:
        p.setFillColorRGB(0, 0.6, 0)
        p.setFont("DejaVuSans", 12)
        p.drawString(60, y, "✔ ACTIVE / PAID")
        p.setFillColorRGB(0, 0, 0)
        y -= 30

    # ================= CUSTOMER =================
    p.setFont("DejaVuSans", 11)
    p.drawString(60, y, "Bill To:")
    y -= 15

    p.setFont("DejaVuSans", 10)
    p.drawString(60, y, sub.get_customer_name())

    y -= 25

    # ================= PLAN INFO =================
    p.setFont("DejaVuSans", 10)
    p.drawString(60, y, f"Plan: {sub.plan_type}")
    y -= 15
    p.drawString(60, y, f"{sub.start_date} → {sub.end_date}")

    y -= 30

    # ================= TABLE HEADER =================
    p.setFillColor(colors.lightgrey)
    p.rect(60, y, width - 120, 22, fill=1)

    p.setFillColor(colors.black)
    p.setFont("DejaVuSans", 10)

    # Proper column alignment
    p.drawString(65, y + 6, "Product")
    p.drawString(300, y + 6, "Qty")
    p.drawString(440, y + 6, "Total")

    y -= 30

    # ================= DATA ROW =================
    name = sub.product.name
    if len(name) > 30:
        name = name[:27] + "..."

    p.drawString(65, y, name)
    p.drawString(300, y, str(sub.quantity))
    
    p.drawRightString(width - 70, y, f"{rupee}{sub.total_amount}")

    y -= 15

    p.setStrokeColor(colors.lightgrey)
    p.line(60, y, width - 60, y)

    y -= 35

    # ================= SUMMARY BOX =================
    p.setFillColor(colors.lightgrey)
    p.rect(width - 260, y, 200, 65, fill=1)

    p.setFillColor(colors.black)
    p.setFont("DejaVuSans", 10)

    p.drawString(width - 250, y + 45, "Subtotal")
    p.drawRightString(width - 70, y + 45, f"{rupee}{sub.subtotal}")

    p.drawString(width - 250, y + 30, "Discount")
    p.drawRightString(width - 70, y + 30, f"-{rupee}{sub.discount}")

    p.setFont("DejaVuSans", 12)
    p.drawString(width - 250, y + 12, "Total")
    p.drawRightString(width - 70, y + 12, f"{rupee}{sub.total_amount}")

    y -= 90

    # ================= WATERMARK =================
    if not sub.is_paid:
        p.saveState()
        p.setFont("DejaVuSans", 50)
        p.setFillColorRGB(1, 0.8, 0.8)
        p.translate(300, 420)
        p.rotate(45)
        p.drawCentredString(0, 0, "PENDING")
        p.restoreState()

    # ================= FOOTER =================
    p.setFont("DejaVuSans", 9)
    p.drawCentredString(width / 2, 60, "Thank you for your subscription!")

    p.save()
    return response

def generate_ai_expiry_message(sub):
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
        Write a short friendly reminder.

        Subscription expires in {sub.remaining_days()} days.
        Plan: {sub.plan_type}
        Product: {sub.product.name}

        Keep it short and polite.
        """

        response = model.generate_content(prompt)

        if response and hasattr(response, "text"):
            return response.text.strip()
        else:
            return "Your subscription is ending soon. Please renew."

    except Exception as e:
        print("AI EXPIRY ERROR:", e)
        return "Your subscription is ending soon. Please renew."
def generate_ai_upgrade_suggestion(sub):
    """
    Generate a product-specific, catchy AI upgrade suggestion.
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        # 🔥 QUICK LOGIC FIRST
        if sub.plan_type.upper() == "WEEKLY":
            return f"Switch {sub.product.name} to a Monthly plan & save more money!"
        if sub.quantity <= 1:
            return f"Increase your {sub.product.name} quantity for better convenience!"

        # 🤖 AI PROMPT
        prompt = f"""
        You are a top-notch sales assistant.

        Create a **unique, catchy upgrade suggestion** for this user:

        Product: {sub.product.name}
        Current Plan: {sub.plan_type}
        Quantity: {sub.quantity}

        Rules:
        - Suggest a better plan or higher quantity if applicable
        - Include benefits like saving money or convenience
        - Keep it one line, friendly and persuasive
        - Make it unique for this product
        """

        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.85, "max_output_tokens": 60}
        )

        # ✅ Validate AI response
        if response and hasattr(response, "text") and response.text.strip():
            text = response.text.strip()
            if len(text.split()) >= 6:
                return text

        # 🔥 FALLBACKS
        fallbacks = [
            f"Upgrade your {sub.product.name} plan for better savings and convenience!",
            f"Boost your {sub.product.name} subscription and enjoy extra benefits!",
            f"Switch to a higher plan of {sub.product.name} and save more!"
        ]
        return random.choice(fallbacks)

    except Exception as e:
        print("AI UPGRADE ERROR:", e)
        return f"Upgrade your {sub.product.name} plan for better savings."

