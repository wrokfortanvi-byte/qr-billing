

from django.shortcuts import render
from django.db.models import Sum
import json

from invoice.models import Invoice
from products.models import Product

from django.template.loader import get_template
# from xhtml2pdf import pisa
from django.http import HttpResponse, JsonResponse

from datetime import timedelta
from django.utils.timezone import now

import zipfile
import io
import os
from django.conf import settings
from collections import Counter
import json
from subscriptions.models import Subscription

from django.conf import settings
from django.conf import settings
import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)






def reports(request):

    invoices = Invoice.objects.all()
    subscriptions = Subscription.objects.all()

    # =========================
    # ✅ TOTAL REVENUE
    # =========================
    invoice_total = invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    subscription_total = subscriptions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    total_revenue = invoice_total + subscription_total

    # =========================
    # ✅ COLLECTED (ONLY PAID)
    # =========================
    collected_invoice = invoices.filter(
        payment_status='PAID'
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    collected_subscription = subscriptions.filter(
        status='ACTIVE'
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    collected = collected_invoice + collected_subscription

    # =========================
    # ✅ OUTSTANDING (PENDING + OVERDUE)
    # =========================
    outstanding_invoice = invoices.filter(
        payment_status__in=['PENDING', 'OVERDUE']
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    outstanding_subscription = subscriptions.filter(
        status__in=['PENDING', 'EXPIRED']
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    outstanding = outstanding_invoice + outstanding_subscription

    # =========================
    # ✅ COUNTS (INVOICE + SUBSCRIPTION)
    # =========================
    paid = (
        invoices.filter(payment_status='PAID').count() +
        subscriptions.filter(status='ACTIVE').count()
    )

    pending = (
        invoices.filter(payment_status='PENDING').count() +
        subscriptions.filter(status='PENDING').count()
    )

    overdue = (
        invoices.filter(payment_status='OVERDUE').count() +
        subscriptions.filter(status='EXPIRED').count()
    )

    # =========================
    # CATEGORY CHART
    # =========================
    from collections import Counter

    products = Product.objects.all()
    category_list = [str(p.category) for p in products]

    category_count = Counter(category_list)

    categories = list(category_count.keys())
    counts = list(category_count.values())

    context = {
        "total_revenue": total_revenue,
        "collected": collected,
        "outstanding": outstanding,

        "paid": paid,
        "pending": pending,
        "overdue": overdue,

        "categories": json.dumps(categories),
        "counts": json.dumps(counts),

        "page_title": "Reports Dashboard",
        "page_subtitle": "Overview of your business analytics & performance",
    }

    return render(request, "dashboard/reports.html", context)
# =========================
# REPORT LIST
# =========================
def report_list(request):

    reports = [
        {"id": 1, "name": "Last 2 Days"},
        {"id": 2, "name": "Last 7 Days"},
        {"id": 3, "name": "1 Month"},
        {"id": 4, "name": "6 Months"},
        {"id": 5, "name": "12 Months"},
        {"id": 6, "name": "Paid Invoices"},
        {"id": 7, "name": "Pending Invoices"},
        {"id": 8, "name": "Overdue Invoices"},
        {"id": 9, "name": "Top Product"},
        {"id": 10, "name": "Lowest Product"},
        {"id": 11, "name": "Download All (ZIP)"},
    ]

    # ✅ CONTEXT ALAG BANANA HAI
    context = {
        "reports": reports,

        # 🔥 TITLE
        "page_title": "Reports",
        "page_subtitle": "Generate and download business reports easily"
    }

    return render(request, "dashboard/report_list.html", context)


# =========================
# REPORT DATA LOGIC (FIXED)
# =========================
def get_report_data(report_id):

    invoices = Invoice.objects.all().order_by('-date')
    subscriptions = Subscription.objects.all()

    today = now().date()

    # =========================
    # COMMON FUNCTIONS
    # =========================
    def filter_invoices(days):
        return invoices.filter(date__gte=today - timedelta(days=days))

    def filter_subscriptions(days):
        return subscriptions.filter(start_date__gte=today - timedelta(days=days))

    def get_products(inv):
        return ", ".join([item.product.name for item in inv.items.all()])

    def add_invoice_data(queryset):
        data = []
        total = 0

        for i in queryset:
            data.append({
                "invoice": f"INV-{i.id}",
                "customer": str(i.customer),
                "product": get_products(i),
                "amount": float(i.total_amount),
                "status": i.payment_status
            })
            total += float(i.total_amount)

        return data, total

    def add_subscription_data(queryset):
        data = []
        total = 0

        for s in queryset:
            data.append({
                "invoice": f"SUB-{s.id}",
                "customer": str(s.user),
                "product": str(s.product),
                "amount": float(s.total_amount),   # ✅ make sure field exists
                "status": s.status
            })
            total += float(s.total_amount)

        return data, total

    # =========================
    # DATE BASED REPORTS
    # =========================
    if report_id == 1:
        inv, t1 = add_invoice_data(filter_invoices(2))
        sub, t2 = add_subscription_data(filter_subscriptions(2))
        return inv + sub, t1 + t2, "Last 2 Days Report"

    elif report_id == 2:
        inv, t1 = add_invoice_data(filter_invoices(7))
        sub, t2 = add_subscription_data(filter_subscriptions(7))
        return inv + sub, t1 + t2, "Last 7 Days Report"

    elif report_id == 3:
        inv, t1 = add_invoice_data(filter_invoices(30))
        sub, t2 = add_subscription_data(filter_subscriptions(30))
        return inv + sub, t1 + t2, "1 Month Report"

    elif report_id == 4:
        inv, t1 = add_invoice_data(filter_invoices(180))
        sub, t2 = add_subscription_data(filter_subscriptions(180))
        return inv + sub, t1 + t2, "6 Months Report"

    elif report_id == 5:
        inv, t1 = add_invoice_data(filter_invoices(365))
        sub, t2 = add_subscription_data(filter_subscriptions(365))
        return inv + sub, t1 + t2, "12 Months Report"

    # =========================
    # STATUS BASED
    # =========================
    elif report_id == 6:
        inv, t1 = add_invoice_data(invoices.filter(payment_status='PAID'))
        sub, t2 = add_subscription_data(subscriptions.filter(status='ACTIVE'))
        return inv + sub, t1 + t2, "Paid Report"

    elif report_id == 7:
        inv, t1 = add_invoice_data(invoices.filter(payment_status='PENDING'))
        sub, t2 = add_subscription_data(subscriptions.filter(status='PENDING'))
        return inv + sub, t1 + t2, "Pending Report"

    elif report_id == 8:
        inv, t1 = add_invoice_data(invoices.filter(payment_status='OVERDUE'))
        sub, t2 = add_subscription_data(subscriptions.filter(status='EXPIRED'))
        return inv + sub, t1 + t2, "Overdue Report"

    # =========================
    # TOP PRODUCT
    # =========================
    elif report_id == 9:

        product_data = {}

        for inv in invoices:
            for item in inv.items.all():
                name = item.product.name

                if name not in product_data:
                    product_data[name] = {"qty": 0, "total": 0}

                product_data[name]["qty"] += item.quantity
                product_data[name]["total"] += float(item.quantity * item.product.price)

        if product_data:
            top = max(product_data, key=lambda x: product_data[x]["qty"])

            return [{
                "invoice": "-",
                "customer": "-",
                "product": top,
                "amount": product_data[top]["total"],
                "status": f"Top Product (Qty: {product_data[top]['qty']})"
            }], product_data[top]["total"], "Top Product Report"

    # =========================
    # LOWEST PRODUCT
    # =========================
    elif report_id == 10:

        product_data = {}

        for inv in invoices:
            for item in inv.items.all():
                name = item.product.name

                if name not in product_data:
                    product_data[name] = {"qty": 0, "total": 0}

                product_data[name]["qty"] += item.quantity
                product_data[name]["total"] += float(item.quantity * item.product.price)

        if product_data:
            low = min(product_data, key=lambda x: product_data[x]["qty"])

            return [{
                "invoice": "-",
                "customer": "-",
                "product": low,
                "amount": product_data[low]["total"],
                "status": f"Lowest Product (Qty: {product_data[low]['qty']})"
            }], product_data[low]["total"], "Lowest Product Report"

    return None, None, None

# =========================
# PDF GENERATE
# =========================
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def generate_pdf(request, report_id):

    data, total, title = get_report_data(report_id)

    if not data:
        return HttpResponse("Invalid Report")

    font_path = os.path.join(settings.BASE_DIR, "invoice", "font", "DejaVuSans.ttf")
    pdfmetrics.registerFont(TTFont('DejaVu', font_path))

    template = get_template("dashboard/single_report.html")
    html = template.render({
        "title": title,
        "data": data,
        "total": total,
        "now": now(),
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{title}.pdf"'

    # pisa.CreatePDF(html, dest=response)
    response.content = b"PDF Generation Temporarily Disabled"
    return response


# =========================
# ZIP DOWNLOAD
# =========================
def download_all_reports(request):

    buffer = io.BytesIO()
    zip_file = zipfile.ZipFile(buffer, 'w')

    for report_id in range(1, 11):

        data, total, title = get_report_data(report_id)

        template = get_template("dashboard/single_report.html")
        html = template.render({
            "title": title,
            "data": data,
            "total": total,
            "now": now(),
        })

        pdf_buffer = io.BytesIO()
        # pisa.CreatePDF(html, dest=pdf_buffer)
        pdf_buffer.write(b"PDF Generation Temporarily Disabled")

        zip_file.writestr(f"{title}.pdf", pdf_buffer.getvalue())

    zip_file.close()

    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="All_Reports.zip"'

    return response
def ai_suggestions(request):
    invoices = Invoice.objects.all()
    subscriptions = Subscription.objects.all()

    total_revenue = (
        invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    ) + (
        subscriptions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    )

    pending = invoices.filter(payment_status='PENDING').count()
    overdue = invoices.filter(payment_status='OVERDUE').count()
    paid = invoices.filter(payment_status='PAID').count()

    prompt = f"""
    You are a smart business assistant for billing software.

    Analyze this data and give 4 short suggestions:

    Total Revenue: {total_revenue}
    Paid Invoices: {paid}
    Pending Invoices: {pending}
    Overdue Invoices: {overdue}

    Rules:
    - Give short points
    - Mix positive + warning + improvement
    - Keep it simple
    """

    try:
        # 🔥 UPDATED MODEL
        model = genai.GenerativeModel("gemini-2.5-flash")

        response = model.generate_content(prompt)

        lines = response.text.split("\n")

        suggestions = []

        for line in lines:
            if line.strip():
                suggestions.append({
                    "type": "info",
                    "text": line.strip()
                })

    except Exception as e:
        suggestions = [{
            "type": "danger",
            "text": "AI error: " + str(e)
        }]

    return JsonResponse({
        "suggestions": suggestions
    })
