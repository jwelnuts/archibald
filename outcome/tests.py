import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from subscriptions.models import Account, Currency
from transactions.models import Transaction


class OutcomeAttachmentTests(TestCase):
    def setUp(self):
        self.temp_media = tempfile.mkdtemp(prefix="outcome-tests-")
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(shutil.rmtree, self.temp_media, ignore_errors=True)

        self.user = get_user_model().objects.create_user(username="outcome_user", password="test1234")
        self.client.login(username="outcome_user", password="test1234")
        self.currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self.account = Account.objects.create(
            owner=self.user,
            name="Conto Test",
            kind=Account.Kind.BANK,
            currency=self.currency,
            opening_balance=Decimal("0.00"),
            is_active=True,
        )

    def test_add_outcome_accepts_pdf_attachment(self):
        receipt = SimpleUploadedFile(
            "scontrino.pdf",
            b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n",
            content_type="application/pdf",
        )
        response = self.client.post(
            "/outcome/api/add",
            {
                "date": "2026-02-20",
                "amount": "12.90",
                "currency": self.currency.id,
                "account": self.account.id,
                "payee_name": "Bar Centrale",
                "note": "Caffe e cornetto",
                "attachment": receipt,
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/outcome/")

        tx = Transaction.objects.get(owner=self.user, tx_type=Transaction.Type.EXPENSE)
        self.assertTrue(tx.attachment.name.endswith(".pdf"))

    def test_add_outcome_rejects_unsupported_attachment_extension(self):
        unsupported = SimpleUploadedFile(
            "note.txt",
            b"plain text",
            content_type="text/plain",
        )
        response = self.client.post(
            "/outcome/api/add",
            {
                "date": "2026-02-20",
                "amount": "19.90",
                "currency": self.currency.id,
                "account": self.account.id,
                "payee_name": "Cartoleria",
                "attachment": unsupported,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.context["form"].errors)
        self.assertFalse(Transaction.objects.filter(owner=self.user, tx_type=Transaction.Type.EXPENSE).exists())
