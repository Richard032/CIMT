"""Accounted access to the OpenAI provider."""

import time
from agents_sdk import run_turn
from openai_transport import OpenAiTransport


class AiServices:
    """Provide model access and account for provider requests."""

    def __init__(self, config, budget, deadline, transport=None, clock=time.monotonic):
        self.model = config["ai-model"]["name"]
        self.clock = clock
        self.budget = budget
        self.transport = transport or OpenAiTransport(config["ai-model"]["api-key"], deadline)

    def check_access(self):
        """Check model access without issuing an inference request."""
        self.transport.request("models/" + self.model)

    def send_post_run(self, body, kind, observer=None):
        """Account for a final proposal even after the testing budget is spent."""
        return self.send(body, kind, observer, allow_overrun=True)

    def send(self, body, kind, observer=None, *, check_cancelled=None, report_timing=None,
             allow_overrun=False):
        if check_cancelled is not None:
            check_cancelled()
        return run_turn(body, lambda request: self._send(
            request, kind, observer, check_cancelled, report_timing, allow_overrun))

    def _send(self, body, kind, observer, check_cancelled, report_timing, allow_overrun):
        if check_cancelled is not None:
            check_cancelled()
        # Keep cache-write charges within the rate used by this pricing profile.
        if self.budget.price.get("cache_ttl"):
            body["prompt_cache_options"] = {"ttl": self.budget.price["cache_ttl"], 'mode': 'explicit'}
            body['input'][0]['content'] = [dict(type='input_text', text=body['input'][0]['content'],
                prompt_cache_breakpoint={'mode': 'explicit'})]
        record = observer.begin(body, kind) if observer is not None else None
        reservation = None
        try:
            if check_cancelled is not None:
                check_cancelled()
            count = getattr(self.transport, 'count_input_tokens', None)
            input_tokens = count(body) if count is not None else None
            if record is not None and input_tokens is not None:
                record['countedInputTokens'] = input_tokens
            if check_cancelled is not None:
                check_cancelled()
            reservation = self.budget.reserve(input_tokens, allow_overrun=allow_overrun)
            if record is not None:
                if reservation.input_tokens is not None:
                    record['estimatedReservation'] = str(reservation.estimated)
                observer.finish(record, 'sending')
            if check_cancelled is not None:
                check_cancelled()
        except Exception:
            try:
                if reservation is not None:
                    self.budget.release_unsent(reservation)
            finally:
                if record is not None:
                    observer.finish(record, 'not sent')
            raise

        response = None
        status = 'failed'
        started = self.clock()
        try:
            response = self.transport.request("responses", body)
            provider_status = response.get('status') if isinstance(response, dict) else None
            status = provider_status if provider_status in ('completed', 'incomplete', 'failed') else 'unknown response'
            return response
        finally:
            seconds = max(0, self.clock() - started)
            usage = response.get("usage") if isinstance(response, dict) else None
            try:
                self.budget.finish(usage, kind=kind, reservation=reservation)
            finally:
                if record is not None:
                    observer.finish(record, status, usage)
                if report_timing is not None:
                    report_timing(dict(kind=kind, status=status, seconds=seconds))
