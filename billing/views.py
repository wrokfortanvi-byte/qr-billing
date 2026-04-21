from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from billing.models import Customer
from products.models import Product
from invoice.models import Invoice
from notifications.models import Notification
from dateutil.relativedelta import relativedelta
User = get_user_model()
from django.db.models import Sum
from subscriptions.models import Subscription   # 🔥 ADD THIS

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum

from products.models import Product
from invoice.models import Invoice
from subscriptions.models import Subscription
from notifications.models import Notification


# ===============================
# ADMIN DASHBOARD
# ===============================
@login_required
def admin_dashboard(request):

    total_products = Product.objects.count()
    total_customers = Customer.objects.count()
    total_invoices = Invoice.objects.count()

    # ===============================
    # ✅ TOTAL REVENUE (INVOICE + SUBSCRIPTION)
    # ===============================
    invoice_revenue = Invoice.objects.filter(
        payment_status="PAID"
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    subscription_revenue = Subscription.objects.filter(
        is_paid=True
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    total_revenue = invoice_revenue + subscription_revenue

    # ===============================
    # ✅ RECENT INVOICES
    # ===============================
    recent_invoices = Invoice.objects.select_related(
        "customer"
    ).order_by("-date")[:5]

    # ===============================
    # ✅ RECENT SUBSCRIPTIONS
    # ===============================
    recent_subscriptions = Subscription.objects.select_related(
        "user"
    ).order_by("-id")[:5]

    # ===============================
    # ✅ WEEKLY CHART (INVOICE + SUBSCRIPTION)
    # ===============================
    today = timezone.localdate()
    start_week = today - timedelta(days=today.weekday())

    week_labels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    week_data = []

    for i in range(7):
        day = start_week + timedelta(days=i)
        next_day = day + timedelta(days=1)

        invoice_rev = Invoice.objects.filter(
            date__date=day,
            payment_status="PAID"
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        subscription_rev = Subscription.objects.filter(
            start_date=day,
            is_paid=True
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        total_day = invoice_rev + subscription_rev
        week_data.append(float(total_day))

    # ===============================
    # ✅ GROWTH (INVOICE + SUBSCRIPTION)
    # ===============================
    now = timezone.now()

    last_7_days = now - timedelta(days=7)
    prev_7_days = now - timedelta(days=14)

    current_invoice = Invoice.objects.filter(
        date__gte=last_7_days,
        payment_status="PAID"
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    current_sub = Subscription.objects.filter(
        start_date__gte=last_7_days.date(),
        is_paid=True
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    previous_invoice = Invoice.objects.filter(
        date__gte=prev_7_days,
        date__lt=last_7_days,
        payment_status="PAID"
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    previous_sub = Subscription.objects.filter(
        start_date__gte=prev_7_days.date(),
        start_date__lt=last_7_days.date(),
        is_paid=True
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    current_total = current_invoice + current_sub
    previous_total = previous_invoice + previous_sub

    if previous_total > 0:
        growth = ((current_total - previous_total) / previous_total) * 100
    else:
        growth = 0

    # ===============================
    # 🔔 NOTIFICATIONS
    # ===============================
    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    latest_notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]

    # ===============================
    # CONTEXT
    # ===============================
    context = {
        'total_products': total_products,
        'total_customers': total_customers,
        'total_invoices': total_invoices,
        'total_revenue': total_revenue,

        'recent_invoices': recent_invoices,
        'recent_subscriptions': recent_subscriptions,

        'week_labels': week_labels,
        'week_data': week_data,

        'growth': round(growth, 2),

        'unread_notifications': unread_notifications,
        'latest_notifications': latest_notifications,

        'page_title': 'Dashboard',
        'page_subtitle': "Welcome back! Here's your business overview.",
    }

    return render(request, 'dashboard/admin_dashboard.html', context)
# ===============================
# GLOBAL SEARCH
# ===============================

@login_required
def global_search(request):

    query = request.GET.get("q")

    customers = []
    products = []
    invoices = []

    if query:

        customers = Customer.objects.select_related("user").filter(
            Q(full_name__icontains=query) |
            Q(phone__icontains=query) |
            Q(user__username__icontains=query)
        )

        products = Product.objects.filter(
            name__icontains=query
        )

        invoices = Invoice.objects.filter(
            Q(invoice_number__icontains=query) |
            Q(customer__username__icontains=query)
        )

    context = {
        "query": query,
        "customers": customers,
        "products": products,
        "invoices": invoices,
        "page_title": "Search Results",
        "page_subtitle": f"Results for '{query}'"
    }

    return render(request, "dashboard/search_results.html", context)


@login_required
def customer_dashboard(request):

    user = request.user

    # ===============================
    # 📄 INVOICES
    # ===============================
    invoices = Invoice.objects.filter(
        customer=user
    ).order_by("-date")

    total_invoices = invoices.count()

    invoice_spent = invoices.aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    pending = invoices.filter(payment_status="PENDING").count()
    overdue = invoices.filter(payment_status="OVERDUE").count()

    recent_invoices = invoices[:5]

    # ===============================
    # 🔁 SUBSCRIPTIONS
    # ===============================
    subscriptions = Subscription.objects.filter(user=user)

    total_subscriptions = subscriptions.count()

    subscription_spent = subscriptions.filter(
        is_paid=True
    ).aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    # 👉 TOTAL SPENT
    total_spent = invoice_spent + subscription_spent

    # 👉 ADD subscription into pending & overdue
    pending_sub = subscriptions.filter(is_paid=False).count()

    overdue_sub = subscriptions.filter(
        is_paid=False,
        end_date__lt=timezone.now().date()
    ).count()

    pending += pending_sub
    overdue += overdue_sub

    # ===============================
    # 📊 MONTHLY CHART (APRIL FIXED ✅)
    # ===============================
    labels = []
    data = []

    current_month = timezone.localtime().date().replace(day=1)

    for i in range(5, -1, -1):

        month_start = current_month - relativedelta(months=i)
        month_end = month_start + relativedelta(months=1)

        labels.append(month_start.strftime("%b"))

        # Invoice total
        invoice_total = Invoice.objects.filter(
            customer=user,
            date__date__gte=month_start,
            date__date__lt=month_end
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        # Subscription total
        subscription_total = Subscription.objects.filter(
            user=user,
            start_date__gte=month_start,
            start_date__lt=month_end,
            is_paid=True
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        total = invoice_total + subscription_total

        data.append(float(total))

    # ===============================
    # 🔔 NOTIFICATIONS
    # ===============================
    unread_notifications = Notification.objects.filter(
        user=user,
        is_read=False
    ).count()

    latest_notifications = Notification.objects.filter(
        user=user
    ).order_by('-created_at')[:5]

    # ===============================
    # 🎯 CONTEXT
    # ===============================
    context = {
        "total_invoices": total_invoices,
        "total_subscriptions": total_subscriptions,
        "total_spent": total_spent,
        "pending": pending,
        "overdue": overdue,
        "recent_invoices": recent_invoices,

        "chart_labels": labels,
        "chart_data": data,

        "unread_notifications": unread_notifications,
        "latest_notifications": latest_notifications
    }

    return render(request, "dashboard/customer_dashboard.html", context)
# ===============================
# ADMIN CUSTOMERS
# ===============================

@login_required
def admin_customers(request):

    search_query = request.GET.get("search")

    customers = Customer.objects.select_related("user")

    if search_query:
        customers = customers.filter(
            full_name__icontains=search_query
        )

    customer_data = []

    for customer in customers:

        due_amount = Invoice.objects.filter(
            customer=customer.user
        ).exclude(
            payment_status="PAID"
        ).aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        customer_data.append({
            "customer": customer,
            "due": due_amount
        })

    return render(request, 'dashboard/admin_customers.html', {
        'customers': customer_data,
        'page_title': 'Customers',
        'page_subtitle': f'{len(customer_data)} customers in system',
    })


# ===============================
# ADD CUSTOMER
# ===============================
@login_required
def add_customer(request):

    if request.method == "POST":

        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")

        # CLEAN PHONE
        if phone:
            phone = phone.replace("+91", "").replace(" ", "").strip()

        print("SAVING PHONE:", phone)

        # GET OR CREATE USER
        user = User.objects.filter(username=email).first()

        if not user:
            user = User.objects.create_user(
                username=email,
                email=email,
                password="12345678",
                user_type="customer",
                is_staff=False
            )

        # 🔥 IMPORTANT FIX → USER ME PHONE SAVE KARO
        user.phone = phone
        user.save()

        # CUSTOMER PROFILE
        customer_obj, created = Customer.objects.get_or_create(user=user)

        customer_obj.full_name = full_name
        customer_obj.phone = phone
        customer_obj.address = address
        customer_obj.save()

        messages.success(request, "Customer added successfully!")
        return redirect("admin_customers")

    return redirect("admin_customers")
# ===============================
# NOTIFICATIONS
# ===============================

@login_required
def get_notifications(request):

    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')

    data = []

    for n in notifications:

        data.append({
            "id": n.id,
            "message": n.message,
            "time": n.created_at.strftime("%d %b %Y %H:%M")
        })

    return JsonResponse({
        "notifications": data,
        "count": notifications.count()
    })


@login_required
def mark_notifications_read(request):

    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    return JsonResponse({"status": "ok"})


@login_required
def customer_notifications(request):

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(
        request,
        "dashboard/customer_notification.html",
        {"notifications": notifications}
    )
    # ===============================
# NOTIFICATION COUNT (FOR BELL)
# ===============================

@login_required
def notification_count(request):

    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        "count": count
    })
    
    
    
    # ===============================
# CUSTOMER SEARCH
# ===============================

@login_required
def customer_search(request):

    query = request.GET.get("q")

    invoices = []

    if query:
        invoices = Invoice.objects.filter(
            customer=request.user
        ).filter(
            Q(invoice_number__icontains=query)
        ).order_by("-date")

    context = {
        "query": query,
        "invoices": invoices,
        "page_title": "Search Results",
        "page_subtitle": f"Results for '{query}'"
    }

    return render(request, "dashboard/customer_search.html", context)
