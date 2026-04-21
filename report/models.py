from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category,on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10,decimal_places=2)

    def __str__(self):
        return self.name


class Invoice(models.Model):

    PAYMENT_STATUS = [
        ('PAID','Paid'),
        ('PENDING','Pending'),
        ('OVERDUE','Overdue')
    ]

    customer_name = models.CharField(max_length=200)

    # ✅ ADD THIS
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    total_amount = models.DecimalField(max_digits=10,decimal_places=2)
    payment_status = models.CharField(max_length=20,choices=PAYMENT_STATUS)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.customer_name