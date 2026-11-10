"""Regression tests for deliberate vulnerabilities; never send real SSRF traffic."""

from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from products.models import Product

from .urls import urlpatterns


class ProductionIsolationTests(SimpleTestCase):
    def test_fixture_routes_are_not_mounted(self):
        for debug in (False, True):
            with self.settings(DEBUG=debug):
                for route in urlpatterns:
                    with self.subTest(debug=debug, route=str(route.pattern)):
                        self.assertEqual(self.client.get('/' + str(route.pattern)).status_code, 404)


@override_settings(ROOT_URLCONF='codeql_fixtures.urls')
class InsecureFixtureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Product.objects.create(label='Mug', description='Ceramic', price='12.50')
        Product.objects.create(label='Desk', description='Oak', price='200.00')

    def test_sqli_1_bypasses_search(self):
        url = '/__insecure__/catalog-search/'
        self.assertEqual(len(self.client.get(url, {'q': 'Mug'}).json()['products']), 1)
        self.assertEqual(len(self.client.get(url, {'q': "' OR 1=1 -- "}).json()['products']), 2)

    def test_sqli_2_bypasses_price_filter(self):
        url = '/__insecure__/price-report/'
        self.assertEqual(len(self.client.get(url, {'ceiling': '20'}).json()['products']), 1)
        self.assertEqual(len(self.client.get(url, {'ceiling': '0 OR 1=1'}).json()['products']), 2)

    def test_three_xss_contexts_preserve_markup(self):
        for route, key, payload in [
            ('search-heading', 'q', '<script>alert(1)</script>'),
            ('promotion-preview', 'copy', '<img src=x onerror=alert(1)>'),
            ('stock-notice', 'sku', '\"><script>alert(1)</script>'),
        ]:
            with self.subTest(route=route):
                response = self.client.get(f'/__insecure__/{route}/', {key: payload})
                self.assertContains(response, payload)
                self.assertTrue(response['Content-Type'].startswith('text/html'))

    @patch('codeql_fixtures.views.urlopen')
    def test_ssrf_forwards_arbitrary_destination(self, urlopen):
        urlopen.return_value.__enter__.return_value.status = 200
        destination = 'http://127.0.0.1:9000/internal-feed'
        response = self.client.get('/__insecure__/supplier-probe/', {'url': destination})
        self.assertEqual(response.json(), {'supplier_status': 200})
        urlopen.assert_called_once_with(destination, timeout=3)
