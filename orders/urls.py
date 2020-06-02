from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


# since here we used class so need as_view function to link


urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register_view, name='register'),
    path('login',views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile',views.ProfileView,name='profile'),
    path('menu', views.menu_view, name='menu'),
    path('cart', views.cart_view, name='cart'),
    path('emptycart', views.empty_cart, name='emptycart'),
    path('add', views.additem, name='additem'),
    path('place', views.place, name='place'),
    path('charge', views.charge, name='charge'),
    path('pending', views.pending_view, name='pending'),
    path('history', views.history_view, name='history'),
    path('orders', views.orders_view, name='orders'),
    path('complete', views.complete_order, name='complete'),
    path('cancel', views.cancel_order, name='cancel')

 ]
