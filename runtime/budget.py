"""Shared AI cost accounting. This module does not call the provider."""

import threading
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from errors import InfrastructureError, LimitReached

# Standard, global endpoint pricing verified against the official model page on
# 2026-10-30. Unknown models/currencies fail before inference. No hosted tools,
# priority tier, previous_response_id, or unbounded generation are enabled.
PRICING = {
    "gpt-5.4-mini-2026-03-17": {
        "context": 400000,
        "input": Decimal("0.75"),
        "output": Decimal("4.50"),
        "source": "https://developers.openai.com/api/docs/models/gpt-5.4-mini",
        "verified": "2026-10-30",
    },
    "gpt-5.6-luna": {
        "context": 1050000,
        "input": Decimal("0.20"),
        "output": Decimal("1.20"),
        # Default cache writes can cost more than ordinary input tokens.
        "cache_write_multiplier": Decimal("1.25"),
        "cache_ttl": "30m",
        "long_context_threshold": 272000,
        "long_input_multiplier": Decimal("2"),
        "long_output_multiplier": Decimal("1.5"),
        "source": "https://developers.openai.com/api/docs/models/gpt-5.6-luna",
        "verified": "2026-10-30",
    },
}
MAX_OUTPUT = 2048


@dataclass(frozen=True)
class RequestReservation:
    estimated: Decimal
    maximum: Decimal
    input_tokens: int | None = None


class Budget:
    """Keeps one shared cost ledger for all device workers."""

    def __init__(self, model, amount, currency):
        if model not in PRICING or currency != "USD":
            raise InfrastructureError(
                "No validated USD pricing bound for the configured model/currency"
            )
        self.price = PRICING[model]
        self.model = model
        self.limit = Decimal(str(amount))
        self.pending_maximum = Decimal(0)
        self.accounted = Decimal(0)
        self.uncertain = Decimal(0)
        self.pending = Decimal(0)
        self.input_tokens = self.output_tokens = self.requests = 0
        self.cached_tokens = 0
        self.cache_usage_requests = 0
        self.usage_records = []
        self.lock = threading.Lock()
        self.journal = lambda: None
        # Keep the model-wide ceiling for legacy ledgers and unknown exposure.
        self.bound = self._cost(self.price["context"], MAX_OUTPUT)

    def restore(self, snapshot):
        """Resume the same run's ledger after the device worker has exited."""
        try:
            if (snapshot["model"] != self.model or snapshot["currency"] != "USD"
                    or Decimal(snapshot["limit"]) != self.limit
                    or Decimal(snapshot["maximumRequestReservation"]) != self.bound):
                raise ValueError("The saved ledger uses different budget settings")
            costs = [Decimal(snapshot[key]) for key in
                     ("accountedUpperCost", "uncertainUpperCost", "pendingUpperCost")]
            if any(not cost.is_finite() or cost < 0 for cost in costs):
                raise ValueError("The saved ledger contains invalid costs")
            accounted, uncertain, pending = costs
            requests, inputs, outputs = [snapshot[key] for key in ("requests", "inputTokens", "outputTokens")]
            cached = snapshot["cachedInputTokens"]
            cache_requests = snapshot["cacheUsageRequests"]
            usage = snapshot["requestUsage"]
            if (any(type(value) is not int or value < 0 for value in (requests, inputs, outputs, cache_requests))
                    or (cached is not None and (type(cached) is not int or not 0 <= cached <= inputs))
                    or not isinstance(usage, list) or not all(isinstance(row, dict) for row in usage)):
                raise ValueError("The saved ledger contains invalid usage")
            pending_requests = requests - len(usage)
            if 'pendingEstimatedCost' in snapshot:
                estimated = Decimal(snapshot['pendingEstimatedCost'])
                valid_pending = (estimated.is_finite() and 0 <= estimated <= pending <= pending_requests * self.bound)
            elif 'pendingReservations' in snapshot:
                # Earlier runs on main stored individual maximum reservations.
                reservations = [Decimal(value) for value in snapshot['pendingReservations']]
                valid_pending = (len(reservations) == pending_requests
                                 and all(value.is_finite() and 0 <= value <= self.bound for value in reservations)
                                 and sum(reservations, Decimal(0)) == pending)
            else:
                valid_pending = pending_requests >= 0 and pending == pending_requests * self.bound
            if not valid_pending:
                raise ValueError("The saved ledger contains invalid pending costs")
        except (KeyError, TypeError, ValueError, InvalidOperation):
            raise InfrastructureError("The saved AI budget could not be restored safely") from None

        self.accounted = accounted
        # A stopped worker cannot settle in-flight usage. Retain its maximum exposure.
        self.uncertain = uncertain + pending
        self.requests, self.input_tokens, self.output_tokens = requests, inputs, outputs
        self.cached_tokens = cached or 0
        self.cache_usage_requests = cache_requests
        self.usage_records = usage + [dict(kind='device request', status='uncertain')] * pending_requests

    def reserve(self, input_tokens=None, *, allow_overrun=False):
        """Hold the counted input cost before starting inference."""
        with self.lock:
            reservation = self._request_cost(input_tokens)
            if not allow_overrun and self.accounted + self.uncertain + self.pending + reservation.estimated > self.limit:
                message = "Remaining shared AI budget cannot fund a worst-case request" if input_tokens is None else (
                    "Remaining shared AI budget cannot fund the counted request input")
                raise LimitReached(message)
            self.pending += reservation.estimated
            self.pending_maximum += reservation.maximum
            self.requests += 1
        try:
            self.journal()
        except Exception:
            # The request cannot be sent if its reservation could not be saved.
            with self.lock:
                self._release(reservation)
                self.requests -= 1
            raise
        return reservation

    def _request_cost(self, input_tokens):
        if input_tokens is None:
            return RequestReservation(self.bound, self.bound)
        if type(input_tokens) is not int or not 0 <= input_tokens <= self.price['context']:
            raise InfrastructureError("Provider input token count is outside the configured model context")
        return RequestReservation(self._cost(input_tokens, 0), self._cost(input_tokens, MAX_OUTPUT),
                                  input_tokens)

    def release_unsent(self, reservation=None):
        """Release a reservation when cancellation prevented transport from starting."""
        with self.lock:
            self._release(reservation or RequestReservation(self.bound, self.bound))
            self.requests -= 1
        self.journal()

    def _release(self, reservation):
        self.pending -= reservation.estimated
        self.pending_maximum -= reservation.maximum

    def finish(self, usage=None, kind='decision', *, reservation=None):
        """Settle a request against reported usage, which may exceed the estimate."""
        reservation = reservation or RequestReservation(self.bound, self.bound)
        with self.lock:
            self._release(reservation)
            invalid = self._settle_usage(usage, reservation)
            self._record_usage(usage, kind, invalid)
        self.journal()
        if invalid:
            raise InfrastructureError("API usage did not fit the validated reservation bounds")

    def _record_usage(self, usage, kind, invalid):
        if not isinstance(usage, dict) or invalid:
            self.usage_records.append(dict(kind=kind, status='uncertain'))
            return
        details = usage.get('input_tokens_details')
        cached = details.get('cached_tokens') if isinstance(details, dict) else None
        if type(cached) is not int or not 0 <= cached <= usage['input_tokens']:
            cached = None
        else:
            self.cached_tokens += cached
            self.cache_usage_requests += 1
        self.usage_records.append(dict(kind=kind, status='recorded', inputTokens=usage['input_tokens'],
            outputTokens=usage['output_tokens'], cachedInputTokens=cached))

    def _settle_usage(self, usage, reservation):
        if not isinstance(usage, dict):
            self.uncertain += reservation.maximum
            return False
        inp, out = usage.get("input_tokens"), usage.get("output_tokens")
        if not self._valid_usage(inp, out):
            self.uncertain += self.bound
            return True
        self.accounted += self._cost(inp, out)
        self.input_tokens += inp
        self.output_tokens += out
        return False

    def _cost(self, input_tokens, output_tokens):
        """Bound usage charges, including cache writes and long-context rates."""
        # Charge every input token at the cache-write rate when it is higher.
        # This remains safe without depending on optional cache usage details.
        input_rate = self.price["input"] * self.price.get("cache_write_multiplier", 1)
        output_rate = self.price["output"]
        if input_tokens > self.price.get("long_context_threshold", self.price["context"]):
            input_rate *= self.price["long_input_multiplier"]
            output_rate *= self.price["long_output_multiplier"]
        return (input_tokens * input_rate + output_tokens * output_rate) / 1000000

    def _valid_usage(self, inp, out):
        return (
            type(inp) is int
            and type(out) is int
            and 0 <= inp <= self.price["context"]
            and 0 <= out <= MAX_OUTPUT
        )

    def snapshot(self):
        """Return a consistent, secret-free view of the current cost ledger."""
        with self.lock:
            return {
                "model": self.model,
                "currency": "USD",
                "limit": str(self.limit),
                "accountedUpperCost": str(self.accounted),
                "uncertainUpperCost": str(self.uncertain),
                "pendingUpperCost": str(self.pending_maximum),
                "pendingEstimatedCost": str(self.pending),
                "budgetOverrun": str(max(Decimal(0), self.accounted + self.uncertain - self.limit)),
                "requests": self.requests,
                "inputTokens": self.input_tokens,
                "outputTokens": self.output_tokens,
                'cachedInputTokens': self.cached_tokens if self.cache_usage_requests else None,
                'cacheUsageRequests': self.cache_usage_requests,
                'requestUsage': [dict(row) for row in self.usage_records],
                "maximumRequestReservation": str(self.bound),
                "pricingSource": self.price["source"],
                "pricingVerified": self.price["verified"],
            }
