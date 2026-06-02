from decimal import Decimal, InvalidOperation
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Prefetch, Q, Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .models import Category, Order, OrderItem, Product
from .seed import seed_data


def get_user_role(user):
    if not user.is_authenticated:
        return None
    return getattr(getattr(user, "profile", None), "role", "CUSTOMER")


def admin_required(view):
    @wraps(view)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if get_user_role(request.user) != "ADMIN":
            messages.error(request, "Admin access is required for this page.")
            return redirect("catalog")
        return view(request, *args, **kwargs)

    return wrapped_view


def ensure_seeded():
    seed_data()


def home(request):
    ensure_seeded()
    featured_products = Product.objects.select_related("category").filter(featured=True)[:3]
    latest_products = Product.objects.select_related("category")[:4]
    categories = Category.objects.all()[:3]
    stats = {
        "products": Product.objects.count(),
        "categories": Category.objects.count(),
        "orders": Order.objects.count(),
        "customers": User.objects.filter(profile__role="CUSTOMER").count(),
    }
    return render(
        request,
        "index.html",
        {
            "featured_products": featured_products,
            "latest_products": latest_products,
            "categories": categories,
            "stats": stats,
        },
    )


def register(request):
    ensure_seeded()
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()

        if not name or not email or not password:
            messages.error(request, "All fields are required.")
            return redirect("register")

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect("register")

        if User.objects.filter(username=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect("register")

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=name,
            password=password,
        )
        user.profile.role = "CUSTOMER"
        user.profile.save(update_fields=["role"])

        messages.success(request, "Registration successful. Please login.")
        return redirect("login")

    return render(request, "register.html")


def login_view(request):
    ensure_seeded()
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}.")
            return redirect("catalog")

        messages.error(request, "Invalid email or password.")
        return redirect("login")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")


def catalog(request):
    ensure_seeded()
    query = request.GET.get("q", "").strip()
    category_param = request.GET.get("category", "").strip()
    selected_category = int(category_param) if category_param.isdigit() else None

    products = Product.objects.select_related("category").all()
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
        )
    if selected_category:
        products = products.filter(category_id=selected_category)
    products = products.order_by("-featured", "-created_at")

    selected_category_obj = Category.objects.filter(pk=selected_category).first() if selected_category else None

    context = {
        "products": products,
        "categories": Category.objects.all(),
        "selected_category": selected_category,
        "query": query,
        "low_stock_count": Product.objects.filter(stock__lte=5).count(),
        "result_count": products.count(),
        "featured_count": products.filter(featured=True).count(),
        "in_stock_count": products.filter(stock__gt=0).count(),
        "selected_category_name": getattr(selected_category_obj, "name", ""),
    }
    return render(request, "catalog.html", context)


@login_required
def buy_product(request, product_id):
    if request.method != "POST":
        return HttpResponseForbidden("Method not allowed.")

    ensure_seeded()

    try:
        quantity = max(int(request.POST.get("quantity", 1)), 1)
    except ValueError:
        messages.error(request, "Quantity must be a valid number.")
        return redirect("catalog")

    address = request.POST.get("shipping_address", "").strip()
    payment_method = request.POST.get("payment_method", "Cash on Delivery").strip()

    if not address:
        messages.error(request, "Shipping address is required to place an order.")
        return redirect("catalog")

    with transaction.atomic():
        product = get_object_or_404(Product.objects.select_for_update(), pk=product_id)

        if product.stock < quantity:
            messages.error(request, "Requested quantity is not available in stock.")
            return redirect("catalog")

        total_amount = product.price * Decimal(quantity)
        order = Order.objects.create(
            user=request.user,
            total_amount=total_amount,
            shipping_address=address,
            payment_method=payment_method,
            status="Processing",
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            price=product.price,
        )
        product.stock -= quantity
        product.save(update_fields=["stock"])

    messages.success(request, "Order placed successfully.")
    return redirect("orders")


@login_required
def orders(request):
    ensure_seeded()
    base_queryset = Order.objects.select_related("user").prefetch_related(
        Prefetch("items", queryset=OrderItem.objects.select_related("product"))
    )
    is_admin = get_user_role(request.user) == "ADMIN"
    orders_list = base_queryset if is_admin else base_queryset.filter(user=request.user)
    total_amount = orders_list.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

    return render(
        request,
        "orders.html",
        {
            "orders": orders_list,
            "is_admin": is_admin,
            "summary": {
                "total": orders_list.count(),
                "active": orders_list.exclude(status="Delivered").count(),
                "delivered": orders_list.filter(status="Delivered").count(),
                "amount": total_amount,
            },
        },
    )


@login_required
@admin_required
def admin_dashboard(request):
    ensure_seeded()
    products = Product.objects.select_related("category").order_by("stock", "name")
    revenue = Order.objects.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
    context = {
        "products": products,
        "categories": Category.objects.all(),
        "low_stock_products": products.filter(stock__lte=5)[:4],
        "metrics": {
            "products": products.count(),
            "orders": Order.objects.count(),
            "revenue": revenue,
            "customers": User.objects.filter(profile__role="CUSTOMER").count(),
        },
    }
    return render(request, "admin.html", context)


@login_required
@admin_required
def add_product(request):
    if request.method != "POST":
        return redirect("admin_dashboard")

    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()
    price = request.POST.get("price", "").strip()
    stock = request.POST.get("stock", "").strip()
    category_id = request.POST.get("category_id", "").strip()
    image_url = request.POST.get("image_url", "").strip()
    featured = request.POST.get("featured") == "on"

    if not all([name, description, price, stock, category_id]):
        messages.error(request, "Please fill in all required product fields.")
        return redirect("admin_dashboard")

    try:
        category = Category.objects.get(pk=int(category_id))
        price_value = Decimal(price)
        stock_value = int(stock)
    except (Category.DoesNotExist, InvalidOperation, ValueError):
        messages.error(request, "Price, stock and category should contain valid values.")
        return redirect("admin_dashboard")

    Product.objects.create(
        name=name,
        description=description,
        price=price_value,
        stock=stock_value,
        category=category,
        image_url=image_url
        or "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=900&q=80",
        featured=featured,
    )
    messages.success(request, "Product added successfully.")
    return redirect("admin_dashboard")


@login_required
@admin_required
def update_order_status(request, order_id):
    if request.method != "POST":
        return redirect("orders")

    order = get_object_or_404(Order, pk=order_id)
    status = request.POST.get("status", "Processing").strip()
    valid_statuses = {choice[0] for choice in Order.STATUS_CHOICES}

    if status not in valid_statuses:
        messages.error(request, "Invalid order status.")
        return redirect("orders")

    order.status = status
    order.save(update_fields=["status"])

    messages.success(request, "Order status updated.")
    return redirect("orders")


@login_required
def profile_view(request):
    ensure_seeded()
    user_orders = Order.objects.filter(user=request.user)
    total_spent = user_orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
    total_orders = user_orders.count()
    context = {
        "profile_user": request.user,
        "profile_role": get_user_role(request.user),
        "profile_created_at": getattr(request.user.profile, "created_at", None),
        "total_spent": total_spent,
        "total_orders": total_orders,
        "active_orders": user_orders.exclude(status="Delivered").count(),
        "delivered_orders": user_orders.filter(status="Delivered").count(),
        "latest_order": user_orders.first(),
    }
    return render(request, "profile.html", context)
