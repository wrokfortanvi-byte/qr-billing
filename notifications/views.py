from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Notification


# =========================
# ALL NOTIFICATIONS PAGE
# =========================

@login_required
def notifications_view(request):

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    # ✅ unread → read mark karo
    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    return render(request, "dashboard/notifications.html", {
        'notifications': notifications,
        'page_title': 'Notifications',
        'page_subtitle': 'Stay updated with your business alerts'
    })


# =========================
# 🔔 LATEST NOTIFICATION API (FIXED)
# =========================

@login_required
def latest_notification(request):

    notification = Notification.objects.filter(
        user=request.user
    ).order_by('-id').first()

    if notification:
        return JsonResponse({
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.type
        })

    return JsonResponse({})

# =========================
# 🔢 NOTIFICATION COUNT (NO CHANGE + SAFE)
# =========================

@login_required
def notification_count(request):

    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        "count": count
    })
