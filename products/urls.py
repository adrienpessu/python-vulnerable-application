from django.urls import path

from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='list'),
    path('products/search/', views.search_product, name='search_product'),
    path('products/xss/', views.display_product, name='display_product'),
    path('products/new/', views.product_form, name='create'),
    path('products/<int:pk>/', views.product_detail, name='detail'),
    path('products/<int:pk>/edit/', views.product_form, name='update'),
    path('products/<int:pk>/delete/', views.product_delete, name='delete'),
    path('products/<int:pk>/photo/', views.product_photo, name='photo'),
]
