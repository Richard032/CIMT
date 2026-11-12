"""Run one OpenAI Agents SDK turn using CIMT's audited request path."""

import asyncio

from agents import Agent, Model, ModelRefusalError, ModelResponse, ModelRetrySettings, ModelSettings, RunConfig, Runner, Usage
from openai.types.responses import ResponseOutputMessage, ResponseOutputRefusal, ResponseOutputText

from errors import InfrastructureError


def run_turn(body, request):
    """Return the provider response so CIMT can handle status and command syntax."""
    instructions, *inputs = body["input"]
    model = AuditedResponsesModel(body, request)
    agent = Agent(
        name="CIMT", instructions=instructions["content"], model=model,
        model_settings=ModelSettings(retry=ModelRetrySettings(max_retries=0)),
    )
    try:
        asyncio.run(Runner.run(agent, inputs, max_turns=1,
                               run_config=RunConfig(tracing_disabled=True)))
    except ModelRefusalError:
        # CIMT reports refusals without including the provider's refusal text.
        pass
    return model.response


class AuditedResponsesModel(Model):
    """Give the SDK model output while retaining the original Responses record."""

    def __init__(self, body, request):
        self.settings = {key: value for key, value in body.items() if key != "input"}
        self.request = request
        self.response = None

    async def get_response(self, system_instructions, input, model_settings, tools,
                           output_schema, handoffs, tracing, *, previous_response_id,
                           conversation_id, prompt):
        body = dict(self.settings, input=[{"role": "system", "content": system_instructions}, *input])
        self.response = await asyncio.to_thread(self.request, body)
        if not isinstance(self.response, dict):
            raise InfrastructureError("OpenAI response was not an object")
        usage = self.response.get("usage") or {}
        return ModelResponse(
            output=self._messages(),
            usage=Usage(requests=1, input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0)),
            response_id=self.response.get("id"),
        )

    def stream_response(self, *args, **kwargs):
        raise NotImplementedError("CIMT uses non-streaming model turns")

    def _messages(self):
        # CIMT handles incomplete replies and output-limit retries using the original status.
        if self.response.get("status") != "completed":
            return []
        messages = []
        for index, item in enumerate(self.response.get("output", [])):
            if item.get("type") != "message":
                continue
            content = []
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    content.append(ResponseOutputText(type="output_text", text=part.get("text", ""), annotations=[]))
                elif part.get("type") == "refusal":
                    content.append(ResponseOutputRefusal(type="refusal", refusal=part.get("refusal", "")))
            messages.append(ResponseOutputMessage(
                type="message", id=item.get("id", f"cimt-message-{index}"), role="assistant",
                status="completed", content=content))
        return messages
