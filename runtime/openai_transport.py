"""HTTPS access to OpenAI. Request construction belongs to the agent."""

import json
import ssl
import time
import urllib.error
import urllib.request
import truststore
from errors import InfrastructureError, LimitReached


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise InfrastructureError("Unexpected redirect from the OpenAI API")


class OpenAiTransport:
    """Sends one API request with a deadline and safe error messages."""

    def __init__(self, key, deadline, opener=None, clock=time.time):
        self.key = key
        self.deadline = deadline
        self.clock = clock
        self.http = opener or self._create_opener()

    @staticmethod
    def _create_opener():
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=context), NoRedirect()
        )

    def request(self, path, body=None):
        """Send one bounded HTTPS request and keep error messages free of private input."""
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            raise LimitReached("Whole-run time limit reached")
        request = self._create_request(path, body)
        try:
            with self.http.open(request, timeout=min(90, remaining)) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            # Provider error bodies may echo private input. Keep only the status.
            raise InfrastructureError(
                "OpenAI API request failed with HTTP " + str(error.code)
            ) from None
        except (OSError, ValueError) as error:
            raise InfrastructureError(
                "OpenAI API transport/response failed: " + type(error).__name__
            ) from None

    def _create_request(self, path, body):
        data = None if body is None else json.dumps(body).encode()
        return urllib.request.Request(
            "https://api.openai.com/v1/" + path,
            data=data,
            headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"},
        )
