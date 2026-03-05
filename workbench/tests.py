from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from .app_builder import (
    AppBuilderError,
    FieldSpec,
    build_model_fields,
    normalize_app_name,
    parse_spec,
    run_post_generation_setup,
)


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

    @patch("workbench.app_builder.subprocess.run")
    def test_run_post_generation_setup_ok(self, mocked_run):
        mocked_run.side_effect = [
            SimpleNamespace(returncode=0, stdout="makemigrations ok"),
            SimpleNamespace(returncode=0, stdout="migrate ok"),
        ]

        result = run_post_generation_setup("demo_app")

        self.assertTrue(result.ok)
        self.assertEqual(len(result.steps), 2)
        self.assertTrue(all(step.ok for step in result.steps))
        self.assertIn("makemigrations demo_app --noinput", result.steps[0].command)
        self.assertIn("migrate --noinput", result.steps[1].command)

    @patch("workbench.app_builder.subprocess.run")
    def test_run_post_generation_setup_stops_on_failure(self, mocked_run):
        mocked_run.side_effect = [
            SimpleNamespace(returncode=1, stdout="makemigrations failed"),
            SimpleNamespace(returncode=0, stdout="migrate ok"),
        ]

        result = run_post_generation_setup("demo_app")

        self.assertFalse(result.ok)
        self.assertEqual(len(result.steps), 1)
        self.assertFalse(result.steps[0].ok)
        self.assertEqual(mocked_run.call_count, 1)
