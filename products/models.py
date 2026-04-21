from django.db import models


class Product(models.Model):

    CATEGORY_CHOICES = [
        ('Grocery', 'Grocery'),
        ('Dairy', 'Dairy'),
        ('Snacks', 'Snacks'),
        ('Household', 'Household'),
        ('Bakery', 'Bakery'),   # ✅ ADD THIS
    ]

    UNIT_CHOICES = [
        ('kg', 'Kg'),
        ('litre', 'Litre'),
        ('pack', 'Pack'),
        ('bag', 'Bag'),
        ('packet', 'Packet'),
    ]

    product_id = models.CharField(max_length=10, unique=True, blank=True)
    name = models.CharField(max_length=100)

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    hsn_code = models.CharField(max_length=20, blank=True, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)

    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    stock = models.IntegerField()

    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)

    def save(self, *args, **kwargs):

        # AUTO PRODUCT ID
        if not self.product_id:
            last_product = Product.objects.order_by('-id').first()

            if last_product:
                last_id = int(last_product.product_id[1:])
                new_id = last_id + 1
            else:
                new_id = 1

            self.product_id = f"p{new_id:03d}"

        # ✅ GST MAP UPDATED
        gst_map = {
            "Grocery": 5,
            "Dairy": 0,
            "Snacks": 18,
            "Household": 18,
            "Bakery": 5   # ✅ ADD
        }

        # ✅ HSN MAP UPDATED
        hsn_map = {
            "Grocery": "1006",
            "Dairy": "0405",
            "Snacks": "1905",
            "Household": "3402",
            "Bakery": "1905"   # ✅ ADD
        }

        self.gst_rate = gst_map.get(self.category, 18)
        self.hsn_code = hsn_map.get(self.category)

        super().save(*args, **kwargs)

    
    def __str__(self):
        return f"{self.product_id} - {self.name}"