from django.test import TestCase

from .app_builder import AppBuilderError, FieldSpec, build_model_fields, normalize_app_name, parse_spec


class AppBuilderTests(TestCase):
    def test_normalize_app_name_rejects_existing(self):
        with self.assertRaises(AppBuilderError):
            normalize_app_name("workbench")

    def test_parse_spec_uses_defaults_when_invalid(self):
        spec = parse_spec({"fields": "bad"}, "custom_app")
        self.assertEqual(spec.model_name, "CustomApp")
        self.assertGreaterEqual(len(spec.fields), 1)

    def test_build_model_fields_for_choice(self):
        lines = build_model_fields(
            [
                FieldSpec(
                    name="status",
                    kind="choice",
                    required=True,
                    choices=["OPEN", "DONE"],
                )
            ]
        )
        rendered = "\n".join(lines)
        self.assertIn("STATUS_CHOICES", rendered)
        self.assertIn("default=\"OPEN\"", rendered)
