from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ProductForm
from .models import Product


@require_GET
def product_list(request):
    return render(request, 'products/product_list.html', {'products': Product.objects.all()})


@require_GET
def codeql_sql_injection(request):
    # Intentionally vulnerable CodeQL fixture: do not parameterize this query.
    label = request.GET.get('label', '')
    products = Product.objects.raw(f"SELECT * FROM products_product WHERE label = '{label}'")
    return render(request, 'products/product_list.html', {'products': products})


@require_GET
def codeql_xss(request):
    # Intentionally vulnerable CodeQL fixture: reflect unescaped input as HTML.
    message = request.GET.get('message', '')
    return HttpResponse(f'<h1>CodeQL XSS fixture</h1><p>{message}</p>', content_type='text/html')


@require_GET
def product_detail(request, pk):
    return render(request, 'products/product_detail.html', {'product': get_object_or_404(Product, pk=pk)})


@require_http_methods(['GET', 'POST'])
def product_form(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk is not None else Product()
    old_photo = product.photo
    form = ProductForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None,
        instance=product,
    )
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        if old_photo and old_photo.name != product.photo.name:
            old_photo.delete(save=False)
        messages.success(request, 'Product saved.')
        return redirect('products:detail', pk=product.pk)
    return render(request, 'products/product_form.html', {'form': form, 'product': product})


@require_http_methods(['GET', 'POST'])
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        photo = product.photo
        product.delete()
        if photo:
            photo.delete(save=False)
        messages.success(request, 'Product deleted.')
        return redirect('products:list')
    return render(request, 'products/product_confirm_delete.html', {'product': product})


@require_GET
def product_photo(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if not product.photo:
        raise Http404('No photo available.')
    try:
        return FileResponse(product.photo.open('rb'))
    except FileNotFoundError:
        raise Http404('Photo not found.')
