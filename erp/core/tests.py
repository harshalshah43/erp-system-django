import json
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.test import TestCase

from .forms import ProductForm
from .models import Product, StockDocument, StockMove
from .services import StockError, post_document, reverse_document

TXN = StockDocument.Kind.TRANSACTION


def make_product(name="Widget", stock=0):
    p = Product.objects.create(name=name, price=1)
    if stock:
        post_document(StockDocument.Kind.OPENING, [(p.pk, stock)])
    p.refresh_from_db()
    return p


class LedgerMixin:
    def assertBalanced(self):
        """stock_quantity must equal the sum of moves for every product."""
        for p in Product.objects.all():
            ledger = p.moves.aggregate(t=Sum("quantity"))["t"] or 0
            self.assertEqual(p.stock_quantity, ledger, p.name)

    def stock(self, product):
        product.refresh_from_db()
        return product.stock_quantity


class PostDocumentTests(LedgerMixin, TestCase):
    def setUp(self):
        self.p = make_product(stock=10)

    def test_in_and_out_create_one_document_with_lines(self):
        other = make_product("Gadget")
        doc = post_document(TXN, [(self.p.pk, -3), (other.pk, 5)], note="n")
        self.assertEqual(self.stock(self.p), 7)
        self.assertEqual(self.stock(other), 5)
        self.assertEqual(doc.lines.count(), 2)
        self.assertBalanced()

    def test_all_or_nothing(self):
        other = make_product("Gadget", stock=1)
        with self.assertRaisesMessage(StockError, "Not enough stock for Gadget"):
            post_document(TXN, [(self.p.pk, -3), (other.pk, -2)])
        self.assertEqual(self.stock(self.p), 10)
        self.assertEqual(StockDocument.objects.filter(kind=TXN).count(), 0)
        self.assertBalanced()

    def test_lines_are_netted_per_product(self):
        post_document(TXN, [(self.p.pk, -15), (self.p.pk, 8)])  # net -7 with 10 in stock
        self.assertEqual(self.stock(self.p), 3)
        self.assertBalanced()

    def test_rejects_empty_zero_and_unknown(self):
        for lines in ([], [(self.p.pk, 0)], [(999999, 1)]):
            with self.subTest(lines=lines), self.assertRaises(StockError):
                post_document(TXN, lines)
        self.assertBalanced()

    def test_database_backstops(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Product.objects.filter(pk=self.p.pk).update(stock_quantity=-1)
        doc = StockDocument.objects.create(kind=TXN)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            StockMove.objects.create(document=doc, product=self.p, quantity=0)


class ReverseDocumentTests(LedgerMixin, TestCase):
    def setUp(self):
        self.p = make_product(stock=10)
        self.doc = post_document(TXN, [(self.p.pk, 5)])

    def test_reverse_restores_stock_and_keeps_original(self):
        rev = reverse_document(self.doc)
        self.assertEqual(self.stock(self.p), 10)
        self.assertEqual(rev.reverses, self.doc)
        self.assertEqual(self.doc.lines.get().quantity, 5)  # original untouched
        self.assertBalanced()

    def test_cannot_reverse_twice_or_reverse_a_reversal(self):
        rev = reverse_document(self.doc)
        with self.assertRaises(StockError):
            reverse_document(self.doc)
        with self.assertRaises(StockError):
            reverse_document(rev)

    def test_cannot_reverse_receipt_already_issued(self):
        post_document(TXN, [(self.p.pk, -15)])
        with self.assertRaises(StockError):
            reverse_document(self.doc)
        self.assertEqual(self.stock(self.p), 0)


class StockTransactionViewTests(LedgerMixin, TestCase):
    url = "/core/stock-transaction/"

    def setUp(self):
        self.p = make_product(stock=10)

    def post(self, lines, note=""):
        return self.client.post(self.url, json.dumps({"note": note, "lines": lines}),
                                content_type="application/json")

    def test_page_renders(self):
        self.assertContains(self.client.get(self.url), "Stock Transaction")

    def test_saves_one_document(self):
        r = self.post([{"product": self.p.pk, "type": "OUT", "quantity": 3},
                       {"product": self.p.pk, "type": "IN", "quantity": 5}], note="Delivery")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.stock(self.p), 12)
        doc = StockDocument.objects.get(kind=TXN)
        self.assertEqual((doc.note, doc.lines.count()), ("Delivery", 2))
        self.assertBalanced()

    def test_errors_are_400_and_save_nothing(self):
        bad = [
            [],
            [{"product": self.p.pk, "type": "IN", "quantity": 0}],
            [{"product": self.p.pk, "type": "XX", "quantity": 1}],
            [{"product": 999999, "type": "IN", "quantity": 1}],
            [{"product": self.p.pk, "type": "IN", "quantity": 1},
             {"product": self.p.pk, "type": "OUT", "quantity": 50}],
            [{"product": "abc", "type": "IN", "quantity": 1}],
        ]
        for lines in bad:
            with self.subTest(lines=lines):
                r = self.post(lines)
                self.assertEqual(r.status_code, 400)
                self.assertIn("error", r.json())
        self.assertEqual(self.client.post(self.url, "not json", content_type="application/json").status_code, 400)
        self.assertEqual(self.stock(self.p), 10)
        self.assertFalse(StockDocument.objects.filter(kind=TXN).exists())


class StockTakeViewTests(LedgerMixin, TestCase):
    url = "/core/stock-take/"

    def setUp(self):
        self.widget = make_product("Widget", stock=10)
        self.gadget = make_product("Gadget", stock=5)

    def post(self, lines):
        return self.client.post(self.url, json.dumps({"note": "", "lines": lines}),
                                content_type="application/json")

    def test_page_renders(self):
        self.assertContains(self.client.get(self.url), "Stock Take")

    def test_only_counted_items_change(self):
        self.post([{"product": self.gadget.pk, "counted": 4, "expected": 5}])
        self.assertEqual(self.stock(self.gadget), 4)
        self.assertEqual(self.stock(self.widget), 10)
        self.assertEqual(StockDocument.objects.get(kind="TAKE").lines.get().quantity, -1)
        self.assertBalanced()

    def test_movement_during_count_is_kept(self):
        # Counter sees 10 and counts 8. Meanwhile 20 are received.
        post_document(TXN, [(self.widget.pk, 20)])
        self.post([{"product": self.widget.pk, "counted": 8, "expected": 10}])
        self.assertEqual(self.stock(self.widget), 28)
        self.assertBalanced()

    def test_matching_counts_save_nothing(self):
        r = self.post([{"product": self.widget.pk, "counted": 10, "expected": 10}])
        self.assertEqual(r.status_code, 200)
        self.assertFalse(StockDocument.objects.filter(kind="TAKE").exists())

    def test_negative_count_rejected(self):
        r = self.post([{"product": self.widget.pk, "counted": -1, "expected": 10}])
        self.assertEqual(r.status_code, 400)


class ProductViewTests(LedgerMixin, TestCase):
    def test_product_form_has_no_stock_field(self):
        self.assertNotIn("stock_quantity", ProductForm().fields)

    def test_edit_updates_in_place(self):
        p = make_product(stock=10)
        self.client.post(f"/core/edit-product/{p.pk}/", {"name": "Renamed", "description": "", "price": "2"})
        self.assertEqual(Product.objects.count(), 1)
        p.refresh_from_db()
        self.assertEqual((p.name, p.stock_quantity), ("Renamed", 10))

    def test_delete_without_history_deletes(self):
        p = make_product()
        self.assertRedirects(self.client.post(f"/core/delete-product/{p.pk}/"), "/core/home/")
        self.assertFalse(Product.objects.exists())

    def test_delete_with_history_archives(self):
        p = make_product(stock=3)
        self.assertContains(self.client.get(f"/core/delete-product/{p.pk}/"), "archived")
        self.assertRedirects(self.client.post(f"/core/delete-product/{p.pk}/"), "/core/home/")
        p.refresh_from_db()
        self.assertFalse(p.is_active)
        self.assertNotContains(self.client.get("/core/home/"), "Widget</td>")
        self.assertEqual(self.client.get("/core/product-search/?q=Widget").json()["results"], [])

    def test_search_pages(self):
        for i in range(17):
            make_product(f"Item {i:02d}")
        page1 = self.client.get("/core/product-search/?page=1").json()
        page2 = self.client.get("/core/product-search/?page=2").json()
        self.assertEqual((len(page1["results"]), page1["has_next"]), (15, True))
        self.assertEqual((len(page2["results"]), page2["has_next"]), (2, False))


class AdminTests(LedgerMixin, TestCase):
    def setUp(self):
        User.objects.create_superuser("admin", "admin@example.com", "pw")
        self.client.login(username="admin", password="pw")
        self.p = make_product(stock=10)
        self.doc = StockDocument.objects.get()

    def test_documents_are_read_only(self):
        base = "/admin/core/stockdocument/"
        self.assertEqual(self.client.get(f"{base}add/").status_code, 403)
        self.assertEqual(self.client.get(f"{base}{self.doc.pk}/delete/").status_code, 403)
        self.client.post(f"{base}{self.doc.pk}/change/", {"kind": "TXN", "note": "edited"})
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.note, "")
        self.assertEqual(self.client.get(f"{base}{self.doc.pk}/change/").status_code, 200)

    def test_stock_not_editable_on_product(self):
        self.client.post(f"/admin/core/product/{self.p.pk}/change/",
                         {"name": "Widget", "description": "", "price": "1",
                          "is_active": "on", "stock_quantity": "999"})
        self.assertEqual(self.stock(self.p), 10)

    def test_reverse_action(self):
        r = self.client.post("/admin/core/stockdocument/",
                             {"action": "reverse_selected", "_selected_action": [self.doc.pk]}, follow=True)
        self.assertContains(r, "reversed by")
        self.assertEqual(self.stock(self.p), 0)
        self.assertBalanced()


class CheckStockCommandTests(TestCase):
    def test_reports_mismatch(self):
        p = make_product(stock=5)
        call_command("check_stock", stdout=StringIO())
        Product.objects.filter(pk=p.pk).update(stock_quantity=7)
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("check_stock", stdout=out)
        self.assertIn("stock 7, moves add up to 5", out.getvalue())
