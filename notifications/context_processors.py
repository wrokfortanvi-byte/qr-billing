from .models import Notification

def notification_data(request):

    if request.user.is_authenticated:

        latest_notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]

        unread_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

    else:
        latest_notifications = []
        unread_notifications = 0

    return {
        'latest_notifications': latest_notifications,
        'unread_notifications': unread_notifications
    }