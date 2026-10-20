"""Conservative registration, product, and cart evidence rules."""

from dataclasses import replace
import unittest

from adaptive_qa.discovery import (
    CommerceSnapshot, FieldSnapshot, FormSnapshot, LinkSnapshot, PageSnapshot,
    detect_page_features,
)
from adaptive_qa.models import FeatureStatus


class CommerceDiscoveryTests(unittest.TestCase):
    def findings(self, **kwargs):
        return {item.feature: item for item in detect_page_features(
            PageSnapshot('https://example.com/', **kwargs))}

    def registration(self, action='Create account'):
        return FormSnapshot(fields=(FieldSnapshot('email'),
                                    FieldSnapshot('password', autocomplete='new-password')),
                            buttons=(action,))

    def product(self):
        return CommerceSnapshot('product', name='Sample product', has_price=True,
                                has_currency=True, actions=('Add to cart',))

    def test_registration_requires_same_form_new_password_identity_and_action(self):
        for action in ('Register', 'Sign up', 'Create an account', 'Kayıt ol', 'ÜYE OL'):
            with self.subTest(action=action):
                finding = self.findings(forms=(self.registration(action),))['registration']
                self.assertEqual(finding.status, FeatureStatus.PRESENT)
                self.assertEqual(finding.evidence, ('form[0]',))

    def test_registration_action_without_new_password_remains_uncertain(self):
        form = replace(self.registration(), fields=(FieldSnapshot('email'), FieldSnapshot('password')))
        self.assertEqual(self.findings(forms=(form,))['registration'].status, FeatureStatus.UNKNOWN)

    def test_password_reset_is_not_registration(self):
        form = replace(self.registration(), buttons=('Reset password',))
        self.assertEqual(self.findings(forms=(form,))['registration'].status, FeatureStatus.UNKNOWN)

    def test_separate_forms_cannot_prove_registration(self):
        forms = (FormSnapshot(fields=self.registration().fields),
                 FormSnapshot(buttons=('Register',)))
        self.assertEqual(self.findings(forms=forms)['registration'].status, FeatureStatus.UNKNOWN)

    def test_hidden_registration_fields_do_not_prove_presence(self):
        form = replace(self.registration(), fields=(FieldSnapshot('email'),
            FieldSnapshot('password', autocomplete='new-password', visible=False)))
        self.assertEqual(self.findings(forms=(form,))['registration'].status, FeatureStatus.UNKNOWN)

    def test_product_requires_name_price_currency_and_purchase_action(self):
        result = self.findings(commerce=(self.product(),))
        self.assertEqual(result['product'].status, FeatureStatus.PRESENT)
        self.assertEqual(result['cart'].status, FeatureStatus.UNKNOWN)

    def test_partial_product_regions_remain_unknown(self):
        for values in ({'name': ''}, {'has_price': False}, {'has_currency': False}, {'actions': ()}):
            with self.subTest(values=values):
                result = self.findings(commerce=(replace(self.product(), **values),))
                self.assertEqual(result['product'].status, FeatureStatus.UNKNOWN)

    def test_separate_product_regions_cannot_combine_evidence(self):
        regions = (replace(self.product(), actions=()),
                   CommerceSnapshot('product', actions=('Add to cart',)))
        self.assertEqual(self.findings(commerce=regions)['product'].status, FeatureStatus.UNKNOWN)

    def test_turkish_purchase_action_is_supported(self):
        result = self.findings(commerce=(replace(self.product(), actions=('Sepete ekle',)),))
        self.assertEqual(result['product'].status, FeatureStatus.PRESENT)

    def test_named_empty_cart_is_present_without_checkout(self):
        for name in ('Shopping cart', 'Basket', 'Sepetim', 'Alışveriş sepeti'):
            with self.subTest(name=name):
                finding = self.findings(commerce=(CommerceSnapshot('cart', name=name, empty=True),))['cart']
                self.assertEqual(finding.status, FeatureStatus.PRESENT)

    def test_populated_cart_requires_items_quantity_and_checkout(self):
        cart = CommerceSnapshot('cart', name='Cart', has_items=True, has_quantity=True,
                                actions=('Checkout',))
        self.assertEqual(self.findings(commerce=(cart,))['cart'].status, FeatureStatus.PRESENT)
        for values in ({'has_items': False}, {'has_quantity': False}, {'actions': ()}, {'name': 'Account'}):
            with self.subTest(values=values):
                self.assertEqual(self.findings(commerce=(replace(cart, **values),))['cart'].status,
                                 FeatureStatus.UNKNOWN)

    def test_hidden_commerce_does_not_prove_presence(self):
        result = self.findings(commerce=(replace(self.product(), visible=False),), collection_complete=True)
        self.assertEqual(result['product'].status, FeatureStatus.ABSENT)

    def test_contradictory_cart_evidence_remains_uncertain(self):
        cart = CommerceSnapshot('cart', name='Cart', empty=True, has_items=True,
                                has_quantity=True, actions=('Checkout',))
        self.assertEqual(self.findings(commerce=(cart,))['cart'].status, FeatureStatus.UNKNOWN)

    def test_commerce_links_are_hints_only(self):
        result = self.findings(links=(LinkSnapshot('Register', '/register'),
            LinkSnapshot('Products', '/products'), LinkSnapshot('Cart', '/cart')), collection_complete=True)
        for feature in ('registration', 'product', 'cart'):
            self.assertEqual(result[feature].status, FeatureStatus.UNKNOWN)

    def test_invalid_commerce_models_are_rejected(self):
        for values in ({'kind': 'checkout'}, {'kind': 'product', 'has_price': 1},
                       {'kind': 'cart', 'actions': []}, {'kind': 'product', 'name': None}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                CommerceSnapshot(**values)
        with self.assertRaises(ValueError):
            PageSnapshot('https://example.com/', commerce=['product'])


if __name__ == '__main__':
    unittest.main()
