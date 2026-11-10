"""INTENTIONALLY INSECURE: exactly two SQLi, three XSS and one SSRF sink.

Training/static-analysis code only. Routes are enabled only by the separate
codeql_fixtures.urls URLconf, never by config.urls.
"""

from urllib.request import urlopen

from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def catalog_search(request):
    """SQLI-1: customer-facing catalog search with unsafe SQL interpolation."""
    term = request.GET.get('q', '')
    with connection.cursor() as cursor:
        # INTENTIONALLY INSECURE SQLI-1 (CWE-89): use bound parameters in real code.
        cursor.execute("SELECT id, label FROM products_product WHERE label LIKE '%" + term + "%'")
        rows = cursor.fetchall()
    return JsonResponse({'products': rows})


@require_GET
def price_report(request):
    """SQLI-2: merchandising report with an unvalidated numeric filter."""
    ceiling = request.GET.get('ceiling', '100')
    with connection.cursor() as cursor:
        # INTENTIONALLY INSECURE SQLI-2 (CWE-89): validate and bind numeric input.
        cursor.execute('SELECT id, label, price FROM products_product WHERE price <= ' + ceiling)
        rows = cursor.fetchall()
    return JsonResponse({'products': rows})


@require_GET
def search_heading(request):
    """XSS-1: reflected catalog search heading."""
    term = request.GET.get('q', '')
    # INTENTIONALLY INSECURE XSS-1 (CWE-79): HTML text must be escaped.
    return HttpResponse('<h1>Results for ' + term + '</h1>')


@require_GET
def promotion_preview(request):
    """XSS-2: merchandising promotion copy preview."""
    copy = request.GET.get('copy', '')
    # INTENTIONALLY INSECURE XSS-2 (CWE-79): untrusted rich text is not sanitized.
    return HttpResponse('<section class="promotion">' + copy + '</section>')


@require_GET
def stock_notice(request):
    """XSS-3: a stock notification form prefilled with the requested SKU."""
    sku = request.GET.get('sku', '')
    # INTENTIONALLY INSECURE XSS-3 (CWE-79): quotes can escape the HTML attribute.
    return HttpResponse('<input name="sku" value="' + sku + '">')


@require_GET
def supplier_probe(request):
    """SSRF-1: check a supplier feed's availability at a caller-provided URL."""
    feed_url = request.GET.get('url', '')
    # INTENTIONALLY INSECURE SSRF-1 (CWE-918): no destination/protocol allowlist.
    with urlopen(feed_url, timeout=3) as upstream:
        status = upstream.status
    return JsonResponse({'supplier_status': status})
