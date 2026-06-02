from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("catalog/", views.catalog, name="catalog"),
    path("products/<int:product_id>/buy/", views.buy_product, name="buy_product"),
    path("orders/", views.orders, name="orders"),
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/products/add/", views.add_product, name="add_product"),
    path("admin/orders/<int:order_id>/status/", views.update_order_status, name="update_order_status"),
    path("profile/", views.profile_view, name="profile"),
]
