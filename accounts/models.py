from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    USER_TYPE = (
        ('admin', 'Admin'),
        ('customer', 'Customer'),
    )

    user_type = models.CharField(max_length=20, choices=USER_TYPE)
    phone = models.CharField(max_length=15, blank=True, null=True)

    profile_image = models.ImageField(
        upload_to='profile_images/',
        blank=True,
        null=True
    )

    def __str__(self):
     return f"{self.username} | {self.email} | {self.phone} | {self.user_type}"
    
    