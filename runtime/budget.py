"""Shared AI cost accounting. This module does not call the provider."""

import threading
from decimal import Decimal
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
        self.accounted = Decimal(0)
        self.uncertain = Decimal(0)
        self.pending = Decimal(0)
        self.input_tokens = self.output_tokens = self.requests = 0
        self.lock = threading.Lock()
        self.journal = lambda: None
        # Reserve the ENTIRE model context, including image input, plus the
        # enforced output cap. This avoids estimates of screenshot/BPE tokens.
        self.bound = self._cost(self.price["context"], MAX_OUTPUT)

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
            isinstance(inp, int)
            and isinstance(out, int)
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
                "pendingUpperCost": str(self.pending),
                "requests": self.requests,
                "inputTokens": self.input_tokens,
                "outputTokens": self.output_tokens,
                "maximumRequestReservation": str(self.bound),
                "pricingSource": self.price["source"],
                "pricingVerified": self.price["verified"],
            }
