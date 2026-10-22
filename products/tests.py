import tempfile
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Product


def photo_upload(name='photo.png', image_format='PNG', size=(10, 10), suffix=b''):
    output = BytesIO()
    Image.new('RGB', size, color='blue').save(output, format=image_format)
    return SimpleUploadedFile(name, output.getvalue() + suffix, content_type='image/png')


class ProductTests(TestCase):
    def setUp(self):
        self.media = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(override_settings(MEDIA_ROOT=self.media))
        self.data = {'label': 'Coffee mug', 'description': 'A blue ceramic mug.', 'price': '12.50'}

    def create_product(self, **extra):
        response = self.client.post(reverse('products:create'), {**self.data, **extra})
        self.assertEqual(response.status_code, 302)
        return Product.objects.latest('pk')

    def test_empty_catalog(self):
        self.assertContains(self.client.get(reverse('products:list')), 'No products yet')

    def test_create_and_read_product(self):
        product = self.create_product()
        self.assertEqual(product.price, Decimal('12.50'))
        self.assertEqual(product.description, self.data['description'])
        self.assertFalse(product.photo)
        self.assertContains(self.client.get(reverse('products:list')), 'Coffee mug')
        response = self.client.get(reverse('products:detail', args=[product.pk]))
        self.assertContains(response, 'A blue ceramic mug.')
        self.assertContains(response, '12.50')

    def test_create_and_serve_photo(self):
        product = self.create_product(photo=photo_upload(suffix=b'<script>untrusted</script>'))
        self.assertTrue(Path(product.photo.path).exists())
        self.assertNotIn('photo.png', product.photo.name)
        response = self.client.get(reverse('products:photo', args=[product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        content = b''.join(response.streaming_content)
        self.assertNotIn(b'<script>', content)
        Image.open(BytesIO(content)).verify()

    def test_supported_image_formats(self):
        for image_format, extension in [('JPEG', 'jpg'), ('PNG', 'png'), ('WEBP', 'webp')]:
            with self.subTest(image_format=image_format):
                product = self.create_product(photo=photo_upload(f'image.{extension}', image_format))
                self.assertTrue(product.photo.name.endswith(f'.{extension}'))

    def test_edit_keeps_photo_if_no_new_upload(self):
        product = self.create_product(photo=photo_upload())
        original_path = product.photo.path
        response = self.client.post(reverse('products:update', args=[product.pk]), {
            **self.data, 'label': 'New label', 'price': '0.00',
        })
        self.assertRedirects(response, reverse('products:detail', args=[product.pk]))
        product.refresh_from_db()
        self.assertEqual(product.label, 'New label')
        self.assertEqual(product.price, Decimal('0.00'))
        self.assertEqual(product.photo.path, original_path)
        self.assertTrue(Path(original_path).exists())

    def test_edit_photo_link_uses_photo_endpoint(self):
        product = self.create_product(photo=photo_upload())
        response = self.client.get(reverse('products:update', args=[product.pk]))
        self.assertContains(response, f'href="{reverse("products:photo", args=[product.pk])}"')

    def test_replace_and_clear_photo(self):
        product = self.create_product(photo=photo_upload())
        original_path = product.photo.path
        self.client.post(reverse('products:update', args=[product.pk]), {
            **self.data, 'photo': photo_upload(),
        })
        product.refresh_from_db()
        self.assertNotEqual(product.photo.path, original_path)
        self.assertFalse(Path(original_path).exists())
        replacement_path = product.photo.path
        self.client.post(reverse('products:update', args=[product.pk]), {
            **self.data, 'photo-clear': 'on',
        })
        product.refresh_from_db()
        self.assertFalse(product.photo)
        self.assertFalse(Path(replacement_path).exists())

    def test_delete_requires_post_and_removes_photo(self):
        product = self.create_product(photo=photo_upload())
        photo_path = product.photo.path
        url = reverse('products:delete', args=[product.pk])
        self.assertContains(self.client.get(url), 'Delete product?')
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
        self.assertTrue(Path(photo_path).exists())
        self.assertRedirects(self.client.post(url), reverse('products:list'))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        self.assertFalse(Path(photo_path).exists())

    def test_delete_product_without_photo(self):
        product = self.create_product()
        self.assertRedirects(
            self.client.post(reverse('products:delete', args=[product.pk])),
            reverse('products:list'),
        )

    def test_invalid_prices(self):
        for price in ['-0.01', '1.234', 'NaN', 'Infinity', '100000000.00', '', 'abc']:
            with self.subTest(price=price):
                response = self.client.post(reverse('products:create'), {**self.data, 'price': price})
                self.assertEqual(response.status_code, 200)
                self.assertIn('price', response.context['form'].errors)
        self.assertEqual(Product.objects.count(), 0)

    def test_required_fields(self):
        response = self.client.post(reverse('products:create'), {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context['form'].errors), {'label', 'description', 'price'})
        self.assertFalse(Product.objects.exists())

    def test_invalid_update_does_not_change_product_or_photo(self):
        product = self.create_product(photo=photo_upload())
        photo_path = product.photo.path
        response = self.client.post(reverse('products:update', args=[product.pk]), {
            **self.data, 'price': '-1', 'photo': photo_upload(),
        })
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.price, Decimal('12.50'))
        self.assertEqual(product.photo.path, photo_path)
        self.assertEqual(len(list(Path(self.media).rglob('*.*'))), 1)

    def test_rejects_invalid_photos(self):
        uploads = [
            SimpleUploadedFile('fake.png', b'not an image', content_type='image/png'),
            SimpleUploadedFile('image.svg', b'<svg onload="alert(1)"></svg>'),
            photo_upload('image.gif', 'GIF'),
            photo_upload(suffix=b'0' * (5 * 1024 * 1024)),
            photo_upload(size=(4097, 1)),
        ]
        for photo in uploads:
            with self.subTest(filename=photo.name, size=photo.size):
                response = self.client.post(reverse('products:create'), {**self.data, 'photo': photo})
                self.assertEqual(response.status_code, 200)
                self.assertIn('photo', response.context['form'].errors)
        self.assertFalse(Product.objects.exists())
        self.assertEqual(list(Path(self.media).iterdir()), [])

    def test_missing_products_and_photos_return_404(self):
        for route in ['detail', 'update', 'delete', 'photo']:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(f'products:{route}', args=[999])).status_code, 404)
        product = self.create_product()
        self.assertEqual(self.client.get(reverse('products:photo', args=[product.pk])).status_code, 404)

    def test_missing_photo_file_returns_404(self):
        product = self.create_product(photo=photo_upload())
        Path(product.photo.path).unlink()
        self.assertEqual(self.client.get(reverse('products:photo', args=[product.pk])).status_code, 404)

    def test_text_is_escaped(self):
        product = self.create_product(label='<script>alert(1)</script>', description='<img src=x onerror=alert(1)>')
        for url in [reverse('products:list'), reverse('products:detail', args=[product.pk])]:
            response = self.client.get(url)
            self.assertNotContains(response, '<script>alert(1)</script>')
            self.assertContains(response, '&lt;script&gt;')
            self.assertNotContains(response, '<img src=x')

    def test_csrf_protects_mutations(self):
        product = self.create_product()
        client = Client(enforce_csrf_checks=True)
        for url in [
            reverse('products:create'),
            reverse('products:update', args=[product.pk]),
            reverse('products:delete', args=[product.pk]),
        ]:
            self.assertEqual(client.post(url, self.data).status_code, 403)
        client.get(reverse('products:create'))
        token = client.cookies['csrftoken'].value
        response = client.post(reverse('products:create'), {**self.data, 'csrfmiddlewaretoken': token})
        self.assertEqual(response.status_code, 302)

    def test_unsupported_methods_do_not_mutate(self):
        product = self.create_product()
        url = reverse('products:delete', args=[product.pk])
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertEqual(self.client.put(reverse('products:update', args=[product.pk])).status_code, 405)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_database_rejects_negative_price(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.create(**{**self.data, 'price': Decimal('-1.00')})


class CodeQLFixtureTests(TestCase):
    def test_sql_injection_fixture_filters_by_label(self):
        Product.objects.create(label='Coffee mug', description='A mug.', price='12.50')
        Product.objects.create(label='Tea cup', description='A cup.', price='8.00')
        response = self.client.get(reverse('products:codeql_sql_injection'), {'label': 'Coffee mug'})
        self.assertContains(response, 'Coffee mug')
        self.assertNotContains(response, 'Tea cup')

    def test_sql_injection_fixture_allows_filter_bypass(self):
        Product.objects.create(label='Coffee mug', description='A mug.', price='12.50')
        Product.objects.create(label='Tea cup', description='A cup.', price='8.00')
        response = self.client.get(
            reverse('products:codeql_sql_injection'), {'label': "' OR 1=1 -- "},
        )
        self.assertContains(response, 'Coffee mug')
        self.assertContains(response, 'Tea cup')

    def test_xss_fixture_reflects_unescaped_html(self):
        payload = '<script>alert("CodeQL XSS fixture")</script>'
        response = self.client.get(reverse('products:codeql_xss'), {'message': payload})
        self.assertEqual(response['Content-Type'], 'text/html')
        self.assertContains(response, payload)

    def test_fixtures_only_accept_get(self):
        for route in ['codeql_sql_injection', 'codeql_xss']:
            with self.subTest(route=route):
                self.assertEqual(self.client.post(reverse(f'products:{route}')).status_code, 405)
