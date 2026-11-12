#!/usr/bin/env python3
"""Focused policy checks; no network requests and no real device actions."""

import concurrent.futures, io, pathlib, sys, time, unittest, json
from types import SimpleNamespace
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))
from PIL import Image
from agent import Agent
from budget import Budget
from errors import InfrastructureError, LimitReached
from openai_transport import NoRedirect, OpenAiTransport
from action_prompt import FIELDS
from redaction import Redactor, ScreenMasker
from crashes import CrashCounter
from actions import ActionExecutor

MODEL = "gpt-5.4-mini-2026-03-17"


class RuntimeChecks(unittest.TestCase):
    def test_dynamic_reservation_fits_small_budget(self):
        budget = Budget(MODEL, '.02', 'USD')
        held = budget.reserve(1000, 2048)
        self.assertEqual(held, Decimal('.009966'))
        budget.finish({'input_tokens': 1000, 'output_tokens': 20}, reservation=held)
        self.assertEqual(budget.pending, 0)
        self.assertEqual(budget.accounted, Decimal('.00084'))

    def test_different_reservations_settle_out_of_order(self):
        budget = Budget(MODEL, 1, 'USD')
        first = budget.reserve(1000)
        second = budget.reserve(5000)
        budget.finish(None, reservation=second)
        self.assertEqual(budget.pending, first)
        self.assertEqual(budget.uncertain, second)
        budget.finish({'input_tokens': 1000, 'output_tokens': 0}, reservation=first)
        self.assertEqual(budget.pending, 0)

    def test_restore_retains_each_dynamic_pending_reservation(self):
        budget = Budget(MODEL, 1, 'USD')
        held = budget.reserve(1000) + budget.reserve(5000)
        restored = Budget(MODEL, 1, 'USD')
        restored.restore(budget.snapshot())
        self.assertEqual(restored.uncertain, held)
        self.assertEqual(restored.pending, 0)
        self.assertEqual(len(restored.usage_records), 2)

    def test_dynamic_reservation_rejects_unfunded_request(self):
        budget = Budget(MODEL, '.009', 'USD')
        with self.assertRaises(LimitReached):
            budget.reserve(1000)
        self.assertEqual(budget.requests, 0)

    def test_usage_exceeding_dynamic_reservation_is_accounted_and_stops(self):
        budget = Budget(MODEL, 1, 'USD')
        held = budget.reserve(1, 1)
        with self.assertRaises(InfrastructureError):
            budget.finish({'input_tokens': 1000, 'output_tokens': 20}, reservation=held)
        self.assertEqual(budget.accounted, Decimal('.00084'))

    def test_agent_counts_input_before_reserving_generation(self):
        calls = []
        budget = Budget(MODEL, '.02', 'USD')
        def count(body):
            calls.append('count')
            self.assertEqual(budget.pending, 0)
            return 1000
        def request(path, body):
            calls.append(path)
            self.assertEqual(budget.pending, Decimal('.009966'))
            return {'usage': {'input_tokens': 1000, 'output_tokens': 0}}
        agent = Agent({'ai-model': {'name': MODEL, 'api-key': 'synthetic'}},
                      budget, time.time() + 30,
                      transport=SimpleNamespace(count_input_tokens=count, request=request))
        agent._request({'max_output_tokens': 2048}, 'decision')
        self.assertEqual(calls, ['count', 'responses'])

    def test_token_count_request_preserves_images_and_omits_generation_options(self):
        calls = []
        transport = SimpleNamespace(request=lambda path, body:
            calls.append((path, body)) or {'input_tokens': 1500})
        image = {'type': 'input_image', 'image_url': 'data:image/png;base64,fixture'}
        body = {'model': MODEL, 'input': [{'role': 'user', 'content': [image]}],
                'max_output_tokens': 2048, 'store': False, 'reasoning': {'effort': 'low'}}
        self.assertEqual(OpenAiTransport.count_input_tokens(transport, body), 1500)
        self.assertEqual(calls[0][0], 'responses/input_tokens')
        self.assertEqual(calls[0][1]['input'], body['input'])
        self.assertNotIn('max_output_tokens', calls[0][1])

    def test_invalid_provider_token_counts_are_rejected(self):
        for value in [None, True, -1, '100', 1.5]:
            transport = SimpleNamespace(request=lambda *args: {'input_tokens': value})
            with self.subTest(value=value), self.assertRaises(InfrastructureError):
                OpenAiTransport.count_input_tokens(transport, {'model': MODEL})

    def test_count_failure_prevents_generation(self):
        calls = []
        def count(body):
            raise InfrastructureError('count unavailable')
        budget = Budget(MODEL, 1, 'USD')
        agent = Agent({'ai-model': {'name': MODEL, 'api-key': 'synthetic'}}, budget,
                      time.time() + 30, transport=SimpleNamespace(
                          count_input_tokens=count, request=lambda *args: calls.append(args)))
        with self.assertRaises(InfrastructureError):
            agent._request({'max_output_tokens': 2048}, 'decision')
        self.assertEqual(calls, [])
        self.assertEqual(budget.requests, 0)

    def test_legacy_pending_ledger_restores(self):
        budget = Budget(MODEL, 1, 'USD')
        budget.reserve()
        saved = budget.snapshot()
        del saved['pendingReservations']
        restored = Budget(MODEL, 1, 'USD')
        restored.restore(saved)
        self.assertEqual(restored.uncertain, budget.bound)

    def test_luna_reserves_full_context_with_cache_and_long_context_charges(self):
        budget = Budget("gpt-5.6-luna", 1, "USD")
        self.assertEqual(budget.bound, Decimal("0.5286864"))

    def test_luna_short_usage_includes_default_cache_write_upper_rate(self):
        budget = Budget("gpt-5.6-luna", 1, "USD")
        budget.reserve()
        budget.finish({"input_tokens": 100, "output_tokens": 20})
        self.assertEqual(budget.accounted, Decimal("0.000049"))
        self.assertEqual(budget.pending, 0)

    def test_luna_threshold_uses_short_context_rates(self):
        budget = Budget("gpt-5.6-luna", 1, "USD")
        budget.reserve()
        budget.finish({"input_tokens": 272000, "output_tokens": 20})
        self.assertEqual(budget.accounted, Decimal("0.068024"))

    def test_luna_above_threshold_reprices_the_entire_request(self):
        budget = Budget("gpt-5.6-luna", 1, "USD")
        budget.reserve()
        budget.finish({"input_tokens": 272001, "output_tokens": 20})
        self.assertEqual(budget.accounted, Decimal("0.1360365"))

    def test_luna_missing_usage_keeps_full_reservation(self):
        budget = Budget("gpt-5.6-luna", 1, "USD")
        budget.reserve()
        budget.finish(None)
        self.assertEqual(budget.uncertain, Decimal("0.5286864"))
        self.assertEqual(budget.pending, 0)

    def test_luna_excessive_input_keeps_full_reservation_and_stops(self):
        budget = Budget("gpt-5.6-luna", 1, "USD")
        budget.reserve()
        with self.assertRaises(InfrastructureError):
            budget.finish({"input_tokens": 1050001, "output_tokens": 20})
        self.assertEqual(budget.uncertain, budget.bound)

    def test_luna_full_usage_stays_within_reserved_cost(self):
        budget = Budget("gpt-5.6-luna", 1, "USD")
        budget.reserve()
        budget.finish({"input_tokens": 1050000, "output_tokens": 2048})
        self.assertEqual(budget.accounted, budget.bound)

    def test_luna_unfunded_action_makes_no_api_request(self):
        budget = Budget("gpt-5.6-luna", ".52", "USD")
        calls = []
        agent = Agent(
            {"ai-model": {"name": "gpt-5.6-luna", "api-key": "synthetic"}},
            budget, time.time() + 30,
            transport=SimpleNamespace(request=lambda *args: calls.append(args)),
        )
        with self.assertRaises(LimitReached):
            agent.choose("test", "", "", [], b"image-fixture", [], [], {})
        self.assertFalse(calls)

    def test_luna_ledger_identifies_the_configured_model(self):
        ledger = Budget("gpt-5.6-luna", 1, "USD").snapshot()
        self.assertEqual(ledger["model"], "gpt-5.6-luna")
        self.assertEqual(ledger["maximumRequestReservation"], "0.5286864")

    def test_two_workers_compete_for_final_reservation(self):
        budget = Budget(MODEL, 1, "USD")
        budget.limit = budget.bound

        def reserve(_):
            try:
                budget.reserve()
                return True
            except LimitReached:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, range(2)))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(budget.pending, budget.bound)
        budget.finish(None)
        self.assertEqual(budget.pending, 0)
        self.assertEqual(budget.uncertain, budget.bound)
        with self.assertRaises(LimitReached):
            budget.reserve()

    def test_usage_refunds_only_the_verified_unused_reservation(self):
        budget = Budget(MODEL, 5, "USD")
        snapshots = []
        budget.journal = lambda: snapshots.append(budget.snapshot())
        budget.reserve()
        budget.finish({"input_tokens": 100, "output_tokens": 20})
        self.assertEqual(budget.accounted, Decimal("0.000165"))
        self.assertEqual(budget.pending, 0)
        self.assertEqual(len(snapshots), 2)

    def test_invalid_usage_keeps_full_uncertain_bound(self):
        budget = Budget(MODEL, 5, "USD")
        budget.reserve()
        with self.assertRaises(InfrastructureError):
            budget.finish({"input_tokens": 1, "output_tokens": 999999})
        self.assertEqual(budget.uncertain, budget.bound)

    def test_unknown_model_currency_rejected(self):
        for model, currency in [("unpriced-model", "USD"), (MODEL, "CHF")]:
            with self.assertRaises(InfrastructureError):
                Budget(model, 5, currency)

    def test_unfunded_action_makes_no_api_request(self):
        budget = Budget(MODEL, ".01", "USD")
        calls = []
        agent = Agent(
            {"ai-model": {"name": MODEL, "api-key": "synthetic-not-a-real-key"}},
            budget,
            time.time() + 30,
            transport=SimpleNamespace(request=lambda *args: calls.append(args)),
        )
        with self.assertRaises(LimitReached):
            agent.choose("test", "", "", [], b"image-fixture", [], [], {})
        self.assertFalse(calls)

    def test_incomplete_response_executes_no_action(self):
        budget = Budget(MODEL, 5, "USD")
        transport = SimpleNamespace(
            request=lambda *args: {
                "status": "incomplete",
                "usage": {"input_tokens": 10, "output_tokens": 2048},
            }
        )
        agent = Agent(
            {"ai-model": {"name": MODEL, "api-key": "synthetic-not-a-real-key"}},
            budget,
            time.time() + 30,
            transport=transport,
        )
        with self.assertRaises(InfrastructureError):
            agent.choose("test", "", "", [], b"image-fixture", [], [], {})
        self.assertEqual(budget.uncertain, 0)

    def test_api_redirect_is_rejected(self):
        with self.assertRaises(InfrastructureError):
            NoRedirect().redirect_request()

    def test_element_id_mask_blacks_pixels_and_scrubs_ui(self):
        redactor = Redactor(
            {
                "ai-model": {"api-key": "synthetic-api-secret"},
                "masking": {"rules": [{"element-id": "PasswordEntry"}]},
            }
        )
        raw = [
            {
                "ref": "@e1",
                "identifier": "PasswordEntry",
                "type": "EditText",
                "value": "unknown-secret",
                "coordinates": {"x": 20, "y": 30, "width": 20, "height": 10},
            }
        ]
        source = io.BytesIO()
        Image.new("RGB", (100, 100), "white").save(source, format="PNG")
        safe, encoded = ScreenMasker(redactor).capture(
            raw, source.getvalue(), {"width": 100, "height": 100}
        )
        image = Image.open(io.BytesIO(encoded))
        self.assertEqual(image.getpixel((25, 35)), (0, 0, 0))
        self.assertEqual(image.getpixel((95, 95)), (255, 255, 255))
        self.assertEqual(safe[0]["ref"], "@e1")
        self.assertEqual(safe[0]["value"], "<masked>")

    def test_required_mask_without_bounds_stops(self):
        redactor = Redactor(
            {
                "credentials": {
                    "test": {"username": "synthetic-user", "password": "synthetic-password"}
                },
                "masking": {"rules": [{"element-id": "PasswordEntry"}]},
            }
        )
        source = io.BytesIO()
        Image.new("RGB", (100, 100), "white").save(source, format="PNG")
        with self.assertRaises(InfrastructureError):
            ScreenMasker(redactor).capture(
                [{"identifier": "PasswordEntry", "value": "synthetic-password"}], source.getvalue(), {"width": 100, "height": 100}
            )
        self.assertNotIn("synthetic-password", redactor.text("error synthetic-password"))

    def test_same_point_crashes_cancel_at_three(self):
        counter = CrashCounter()
        self.assertEqual(counter.record("point-A", True), 1)
        counter.record("navigation-B", False)
        self.assertEqual(counter.record("point-A", True), 2)
        self.assertEqual(counter.record("point-A", True), 3)
        self.assertEqual(counter.record("point-A", False), 0)
        self.assertEqual(counter.record("point-A", True), 1)
        self.assertEqual(counter.record("different-crash", True), 1)

    def test_coordinate_taps_are_bounded_by_device_dimensions(self):
        calls = []
        mobile = SimpleNamespace(
            readiness=lambda: None, call=lambda *a, **kw: calls.append((a, kw))
        )
        execution = ActionExecutor({}, Redactor({}), time.time() + 30)
        elements = [{"type": "CimtScreenInfo", "screenWidth": 100, "screenHeight": 200}]
        action = {"action": "tap", "ref": "", "x": 100, "y": 2}
        with self.assertRaises(ValueError):
            execution.execute(mobile, action, elements)
        self.assertFalse(calls)
        action["x"] = 20
        execution.execute(mobile, action, elements)
        self.assertEqual(calls[0][1], {"x": 20, "y": 2})

    def test_credentials_require_stable_element_identifier(self):
        calls = []
        config = {
            "credentials": {
                "test": {"username": "synthetic-user", "password": "synthetic-password"}
            }
        }
        mobile = SimpleNamespace(
            readiness=lambda: None, call=lambda *a, **kw: calls.append((a, kw))
        )
        execution = ActionExecutor(config, Redactor(config), time.time() + 30)
        action = {"action": "credential", "ref": "@e1", "credential": "test", "field": "password"}
        with self.assertRaises(ValueError):
            execution.execute(mobile, action, [{"ref": "@e1"}])
        self.assertFalse(calls)

    def test_model_input_contains_aliases_but_no_credential_values(self):
        config = {
            "ai-model": {"name": MODEL, "api-key": "synthetic-api-key"},
            "credentials": {
                "test": {"username": "synthetic-user", "password": "synthetic-password"}
            },
        }
        action = {k: "" for k in FIELDS}
        action.update(action="done", x=-1, y=-1, remaining=[], completion="blocked", checks=[],
                      planUpdates=[], planStepId=0, discoveredControls=[], configuration=[], pathDecisions=[],
                      context=dict(summary='', includeAll=[], records=[]),
                      recovery=dict(id=-1, decision='none', reason=''))
        bodies = []

        def respond(path, body):
            bodies.append(body)
            return {
                "status": "completed",
                "usage": {"input_tokens": 10, "output_tokens": 10},
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(action)}],
                    }
                ],
            }

        agent = Agent(
            config,
            Budget(MODEL, 5, "USD"),
            time.time() + 30,
            transport=SimpleNamespace(request=respond),
        )
        agent.choose("test", "", "", [], b"image-fixture", [], ["test"], {})
        encoded = json.dumps(bodies)
        for secret in ["synthetic-api-key", "synthetic-user", "synthetic-password"]:
            self.assertNotIn(secret, encoded)
        self.assertIn("credentialAliases", encoded)


if __name__ == "__main__":
    unittest.main(verbosity=2)
