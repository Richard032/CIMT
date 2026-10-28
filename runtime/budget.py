"""Shared AI cost accounting. This module does not call the provider."""

import threading
from decimal import Decimal
from errors import InfrastructureError, LimitReached

# Standard, global endpoint pricing verified against the official model page on
# 2026-10-28. Unknown models/currencies fail before inference. No hosted tools,
# priority tier, previous_response_id, or unbounded generation are enabled.
PRICING = {
    "gpt-5.4-mini-2026-03-17": {
        "context": 400000,
        "input": Decimal("0.75"),
        "output": Decimal("4.50"),
        "source": "https://developers.openai.com/api/docs/models/gpt-5.4-mini",
        "verified": "2026-10-28",
    },
}
MAX_OUTPUT = 2048


class Budget:
    """Keeps one shared cost ledger for all device workers."""

    def __init__(self, model, amount, currency):
        if model not in PRICING or currency != "USD":
            raise InfrastructureError(
                "No validated USD pricing bound for the configured model/currency"
            )
        self.price = PRICING[model]
        self.limit = Decimal(str(amount))
        self.accounted = Decimal(0)
        self.uncertain = Decimal(0)
        self.pending = Decimal(0)
        self.input_tokens = self.output_tokens = self.requests = 0
        self.lock = threading.Lock()
        self.journal = lambda: None
        # Reserve the ENTIRE model context, including image input, plus the
        # enforced output cap. This avoids estimates of screenshot/BPE tokens.
        self.bound = (
            self.price["context"] * self.price["input"] + MAX_OUTPUT * self.price["output"]
        ) / 1000000

    def reserve(self):
        """Hold the maximum request cost before any paid call starts."""
        with self.lock:
            if self.accounted + self.uncertain + self.pending + self.bound > self.limit:
                raise LimitReached("Remaining shared AI budget cannot fund a worst-case request")
            self.pending += self.bound
            self.requests += 1
        self.journal()

    def finish(self, usage=None):
        """Settle one reservation, keeping its full cost when usage is uncertain."""
        with self.lock:
            self.pending -= self.bound
            invalid = self._settle_usage(usage)
        self.journal()
        if invalid:
            raise InfrastructureError("API usage did not fit the validated reservation bounds")

    def _settle_usage(self, usage):
        if not isinstance(usage, dict):
            self.uncertain += self.bound
            return False
        inp, out = usage.get("input_tokens"), usage.get("output_tokens")
        if not self._valid_usage(inp, out):
            self.uncertain += self.bound
            return True
        # Ignore caching discounts to keep the accounted cost conservative.
        self.accounted += (inp * self.price["input"] + out * self.price["output"]) / 1000000
        self.input_tokens += inp
        self.output_tokens += out
        return False

    def _valid_usage(self, inp, out):
        return (
            isinstance(inp, int)
            and isinstance(out, int)
            and 0 <= inp <= self.price["context"]
            and 0 <= out <= MAX_OUTPUT
        )

    def snapshot(self):
        """Return a consistent, secret-free view of the current cost ledger."""
        with self.lock:
            return {
                "currency": "USD",
                "limit": str(self.limit),
                "accountedUpperCost": str(self.accounted),
                "uncertainUpperCost": str(self.uncertain),
                "pendingUpperCost": str(self.pending),
                "requests": self.requests,
                "inputTokens": self.input_tokens,
                "outputTokens": self.output_tokens,
                "maximumRequestReservation": str(self.bound),
                "pricingSource": self.price["source"],
                "pricingVerified": self.price["verified"],
            }
