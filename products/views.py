from django.shortcuts import render, redirect
from django.db.models import Q
from django.contrib import messages   # ✅ IMPORTANT
from .models import Product


def product_list(request):

    if request.method == "POST":

        # ✅ CHECK: STOCK UPDATE (from +Stock button)
        product_id = request.POST.get("product_id")

        if product_id:
            add_stock = request.POST.get("stock")

            if add_stock:
                product = Product.objects.get(id=product_id)
                product.stock += int(add_stock)
                product.save()

                # ✅ SUCCESS MESSAGE
                messages.success(request, f"{product.name} stock updated successfully!")

            return redirect("admin_products")

        # ✅ ADD PRODUCT
        name = request.POST.get("name")
        category = request.POST.get("category")
        price = request.POST.get("price")
        stock = request.POST.get("stock")
        unit = request.POST.get("unit")

        # ✅ Basic validation
        if name and category and price and stock and unit:

            existing_product = Product.objects.filter(
                name__iexact=name,
                category=category
            ).first()

            if existing_product:
                existing_product.stock += int(stock)
                existing_product.save()

                # ✅ MESSAGE
                messages.success(request, f"{existing_product.name} stock increased!")

            else:
                Product.objects.create(
                    name=name,
                    category=category,
                    price=price,
                    stock=stock,
                    unit=unit,
                )

                # ✅ MESSAGE
                messages.success(request, "New product added successfully!")

        return redirect("admin_products")

    # ✅ FETCH PRODUCTS
    products = Product.objects.all().order_by("product_id")

    # ✅ SEARCH
    search_query = request.GET.get("search")

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(product_id__icontains=search_query) |
            Q(category__icontains=search_query)
        )

    # ✅ CONTEXT
    context = {
        "products": products,
        "page_title": "Products",
        "page_subtitle": f"{products.count()} products in inventory"
    }

    return render(request, "dashboard/products.html", context)