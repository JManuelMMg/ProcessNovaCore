import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.inventory.models import Product, Stock
from apps.users.models import Branch, Membership, Organization

User = get_user_model()


class PosApiTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name='Test Org',
            rfc='XAXX010101000',
            razon_social='Test SA',
            regimen_fiscal='601',
            codigo_postal='01000',
        )
        self.branch = Branch.objects.create(
            organization=self.org,
            name='Sucursal Test',
            codigo_postal='01000',
            is_main=True,
        )
        self.user = User.objects.create_user(
            username='posuser',
            email='pos@test.com',
            password='TestPass123!',
        )
        Membership.objects.create(
            user=self.user,
            organization=self.org,
            role='branch_manager',
            branch=self.branch,
        )
        self.product = Product.objects.create(
            organization=self.org,
            name='Producto POS',
            sku='SKU-001',
            barcode='7501234567890',
            price=Decimal('100.00'),
            cost=Decimal('50.00'),
            tax_rate=Decimal('16.00'),
            is_taxable=True,
        )
        Stock.objects.create(
            organization=self.org,
            product=self.product,
            branch=self.branch,
            quantity=25,
        )
        self.client = Client()
        self.client.login(username='posuser', password='TestPass123!')

    def test_scan_product_by_barcode(self):
        response = self.client.post(
            reverse('sales:api_scan_product'),
            data=json.dumps({'barcode': '7501234567890'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['product']['id'], self.product.id)

    def test_add_to_cart_checkout_flow(self):
        add_response = self.client.post(
            reverse('sales:api_add_to_cart'),
            data=json.dumps({
                'product_id': self.product.id,
                'quantity': 2,
                'sale_type': 'pos',
            }),
            content_type='application/json',
        )
        self.assertEqual(add_response.status_code, 200)
        cart = add_response.json()['cart']
        self.assertEqual(len(cart['items']), 1)
        self.assertEqual(cart['items'][0]['quantity'], 2)

        checkout_response = self.client.post(
            reverse('sales:api_checkout'),
            data=json.dumps({
                'payment_method': 'cash',
                'amount_paid': float(cart['total']),
                'sale_type': 'pos',
            }),
            content_type='application/json',
        )
        self.assertEqual(checkout_response.status_code, 200)
        self.assertTrue(checkout_response.json()['success'])

        self.product.stock_set.get(branch=self.branch).refresh_from_db()
        self.assertEqual(self.product.stock_set.get(branch=self.branch).quantity, 23)

    def test_products_cache_includes_tax_fields(self):
        response = self.client.get(reverse('sales:api_products_cache'))
        self.assertEqual(response.status_code, 200)
        products = response.json()['products']
        self.assertEqual(len(products), 1)
        self.assertIn('tax_rate', products[0])
        self.assertIn('is_taxable', products[0])

    def test_inventory_add_stock_by_barcode(self):
        response = self.client.post(
            reverse('inventory:api_add_stock'),
            data=json.dumps({'barcode': '7501234567890', 'quantity': 5}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['new_quantity'], 30)
