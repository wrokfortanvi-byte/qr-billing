from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Integration(models.Model):

    TYPE_CHOICES = (
        ('whatsapp', 'WhatsApp'),
        ('razorpay', 'Razorpay'),
        ('tally', 'Tally'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.type}"