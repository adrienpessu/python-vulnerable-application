"""INTENTIONALLY INSECURE test-only URLconf. Do not include in config.urls."""

from django.urls import path

from . import views

urlpatterns = [
    path('__insecure__/catalog-search/', views.catalog_search),
    path('__insecure__/price-report/', views.price_report),
    path('__insecure__/search-heading/', views.search_heading),
    path('__insecure__/promotion-preview/', views.promotion_preview),
    path('__insecure__/stock-notice/', views.stock_notice),
    path('__insecure__/supplier-probe/', views.supplier_probe),
]
