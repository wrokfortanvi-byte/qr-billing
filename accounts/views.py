from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .models import User

def register_view(request):
    if request.method == "POST":

        email = request.POST.get('email')   # 🔥 change
        password = request.POST.get('password')
        user_type = request.POST.get('user_type')

        # 🔥 username = email
        if User.objects.filter(username=email).exists():
            messages.error(request, "User already exists")
            return redirect('register')

        user = User.objects.create_user(
            username=email,   # 🔥 IMPORTANT
            email=email,
            password=password,
            user_type=user_type
        )

        # 🔵 Admin
        if user_type == "admin":
            user.is_staff = True
            user.is_superuser = True

        # 🟢 Customer
        elif user_type == "customer":
            user.is_staff = False
            user.is_superuser = False

        user.save()

        messages.success(request, "Account created successfully. Please login.")
        return redirect('login')

    return render(request, "register.html")
# ✅ LOGIN VIEW
def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.user_type.lower() == "admin":
                return redirect('admin_dashboard')
            elif user.user_type.lower() == "customer":
                return redirect('customer_dashboard')
            else:
                messages.error(request, "User type not defined")
                return redirect('login')

        else:
            messages.error(request, "Invalid Credentials")

    return render(request, "login.html")
def logout_view(request):
    logout(request)
    return redirect('login')  