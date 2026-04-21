from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Integration


@login_required
def integrations_page(request):

    db_integrations = Integration.objects.filter(user=request.user)

    ALL_INTEGRATIONS = [
        {
            "type": "whatsapp",
            "name": "WhatsApp Business",
            "desc": "Send invoices & reminders via WhatsApp"
        },
        {
            "type": "razorpay",
            "name": "Razorpay",
            "desc": "Accept online payments with UPI, cards & wallets"
        },
        {
            "type": "tally",
            "name": "Tally ERP",
            "desc": "Sync invoices and accounting data"
        }
    ]

    final_data = []

    for item in ALL_INTEGRATIONS:
        db_obj = db_integrations.filter(type=item["type"]).first()

        final_data.append({
            "type": item["type"],
            "name": item["name"],
            "desc": item["desc"],
            "is_active": db_obj.is_active if db_obj else False
        })

    connected_count = sum(1 for i in final_data if i["is_active"])

    return render(request, "dashboard/integrations.html", {
        "integrations": final_data,
        "connected_count": connected_count,

        # 🔥 ADD THIS
        "page_title": "Integrations",
        "page_subtitle": "Connect third-party services to automate your workflow"
    })

@login_required
def toggle_integration(request):

    if request.method == "POST":

        type = request.POST.get("type")

        # ✅ Security check
        if type not in ["whatsapp", "razorpay", "tally"]:
            return JsonResponse({"error": "Invalid integration"})

        obj, created = Integration.objects.get_or_create(
            user=request.user,
            type=type
        )

        obj.is_active = not obj.is_active
        obj.save()

        message = "Connected" if obj.is_active else "Disconnected"

        return JsonResponse({
            "status": "success",
            "integration": type,
            "active": obj.is_active,
            "message": message
        })


