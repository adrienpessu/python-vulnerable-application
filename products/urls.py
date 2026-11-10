from django.urls import path

from . import codeql_examples
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='list'),
    path('products/new/', views.product_form, name='create'),
    path('products/<int:pk>/', views.product_detail, name='detail'),
    path('products/<int:pk>/edit/', views.product_form, name='update'),
    path('products/<int:pk>/delete/', views.product_delete, name='delete'),
    path('products/<int:pk>/photo/', views.product_photo, name='photo'),
    path('codeql-demo/sql-injection/label/', codeql_examples.sql_injection_label, name='codeql-sqli-label'),
    path('codeql-demo/sql-injection/order/', codeql_examples.sql_injection_order, name='codeql-sqli-order'),
    path('codeql-demo/xss/response/', codeql_examples.xss_response, name='codeql-xss-response'),
    path('codeql-demo/xss/markup/', codeql_examples.xss_markup, name='codeql-xss-markup'),
    path('codeql-demo/xss/concatenation/', codeql_examples.xss_concatenation, name='codeql-xss-concatenation'),
    path('codeql-demo/ssrf/preview/', codeql_examples.ssrf_preview, name='codeql-ssrf-preview'),
]
