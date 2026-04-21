from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Notification(models.Model):

    TYPE_CHOICES = (
        ('warning','Warning'),
        ('success','Success'),
        ('info','Info'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_notifications"
    )

    title = models.CharField(max_length=200)

    message = models.TextField()

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title