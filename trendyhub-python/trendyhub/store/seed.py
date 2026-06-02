from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction

from .models import Category, Product


def seed_data():
    with transaction.atomic():
        admin_user, created = User.objects.get_or_create(
            username="admin@trendyhub.com",
            defaults={
                "email": "admin@trendyhub.com",
                "first_name": "Admin User",
                "is_staff": True,
            },
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save(update_fields=["password"])

        admin_profile = admin_user.profile
        admin_profile.role = "ADMIN"
        admin_profile.save(update_fields=["role"])

        if Category.objects.exists():
            return

        men = Category.objects.create(
            name="Men",
            description="Streetwear, casual shirts and essentials.",
        )
        women = Category.objects.create(
            name="Women",
            description="Modern fashion for everyday wear.",
        )
        accessories = Category.objects.create(
            name="Accessories",
            description="Bags, watches and style add-ons.",
        )

        Product.objects.bulk_create(
            [
                Product(
                    name="Urban Denim Jacket",
                    description="Classic blue denim jacket with a modern regular fit.",
                    price=Decimal("2499.00"),
                    stock=18,
                    image_url="https://images.unsplash.com/photo-1523398002811-999ca8dec234?auto=format&fit=crop&w=900&q=80",
                    featured=True,
                    category=men,
                ),
                Product(
                    name="Minimal Cotton Kurti",
                    description="Soft cotton kurti designed for comfort and style.",
                    price=Decimal("1799.00"),
                    stock=24,
                    image_url="https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=80",
                    featured=True,
                    category=women,
                ),
                Product(
                    name="Premium Analog Watch",
                    description="Metal strap watch built to elevate formal and casual outfits.",
                    price=Decimal("3299.00"),
                    stock=12,
                    image_url="https://images.unsplash.com/photo-1523170335258-f5ed11844a49?auto=format&fit=crop&w=900&q=80",
                    featured=False,
                    category=accessories,
                ),
                Product(
                    name="Classic White Sneakers",
                    description="Versatile sneakers with cushioned sole and premium finish.",
                    price=Decimal("2899.00"),
                    stock=20,
                    image_url="https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
                    featured=True,
                    category=men,
                ),
            ]
        )
