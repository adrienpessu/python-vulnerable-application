from urllib.request import urlopen

from django.conf import settings
from django.db import connection
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_GET


def _require_debug_mode():
    if not settings.DEBUG:
        raise Http404


@require_GET
def sql_injection_label(request):
    _require_debug_mode()
    label = request.GET.get('label', '')
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT label FROM products_product WHERE label = '{label}'")
        results = cursor.fetchall()
    return HttpResponse(str(results), content_type='text/plain')


@require_GET
def sql_injection_order(request):
    _require_debug_mode()
    sort = request.GET.get('sort', 'label')
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT label FROM products_product ORDER BY {sort}')
        results = cursor.fetchall()
    return HttpResponse(str(results), content_type='text/plain')


@require_GET
def xss_response(request):
    _require_debug_mode()
    return HttpResponse(request.GET.get('message', ''), content_type='text/html')


@require_GET
def xss_markup(request):
    _require_debug_mode()
    message = request.GET.get('message', '')
    return HttpResponse(f'<p>{message}</p>', content_type='text/html')


@require_GET
def xss_concatenation(request):
    _require_debug_mode()
    message = request.GET.get('message', '')
    return HttpResponse('<p>' + message + '</p>', content_type='text/html')


@require_GET
def ssrf_preview(request):
    _require_debug_mode()
    url = request.GET.get('url', '')
    with urlopen(url, timeout=2) as response:
        body = response.read(1024)
    return HttpResponse(body, content_type='text/plain')
