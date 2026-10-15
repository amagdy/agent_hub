"""Agentic loop against a local Ollama server, using only the stdlib.

Talks to Ollama's native `/api/chat` endpoint directly (no litellm / SDK).
Tools come from a ToolRegistrar, same as agent_runner.AgentRunner.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

# Allow running this file directly (see agent_runner.py).
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentic_framework.tool_registrar import ToolRegistrar  # noqa: E402
from utils.logger import logger  # noqa: E402

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "granite4:3b"


class OllamaError(RuntimeError):
    """Raised when the Ollama server cannot be reached or returns an error."""


class OllamaCaller:
    """Calls an Ollama model and runs its tool calls via a ToolRegistrar."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        registrar: ToolRegistrar | None = None,
        host: str | None = None,
        max_turns: int = 100,
        timeout: float = 120.0,
        context_size: int = 16384,
        temperature: float = 0.0,
    ):
        self.model = model
        self.max_turns = max_turns
        self.timeout = timeout
        self.context_size = context_size
        # Sent as options.temperature; None leaves the model's default.
        self.temperature = temperature
        self.host = (host or os.environ.get("OLLAMA_HOST") or DEFAULT_HOST).rstrip("/")
        if not self.host.startswith(("http://", "https://")):
            self.host = f"http://{self.host}"

        self.registrar = registrar or ToolRegistrar().discover()
        self.tools = self.registrar.tools
        self.available_functions = self.registrar.available_functions
        # Parameter names per tool, used to drop arguments the schema doesn't declare.
        self.allowed_params = self.registrar.allowed_params

    # ---- low level -----------------------------------------------------
    def chat(self, messages: list[dict]) -> dict:
        """Send one non-streaming chat request and return the assistant message."""
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": self.tools,
            "stream": False,
            "options": {
                "num_ctx": self.context_size,
                "temperature": self.temperature
            }
        }
        logger.debug("POST %s/api/chat with %d message(s)", self.host, len(messages))
        request = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                body = json.load(resp)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama returned HTTP {e.code}: {detail}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise OllamaError(f"Cannot reach Ollama at {self.host}: {e}") from e

        message = body.get("message")
        if message is None:
            raise OllamaError(f"Unexpected Ollama response: {body}")
        logger.debug("Model message: %s", message)
        return message

    # ---- agentic loop --------------------------------------------------
    def run(self, user_prompt: str) -> str:
        logger.info("user_prompt", prompt=user_prompt)
        messages: list[dict] = [{"role": "user", "content": user_prompt}]

        for turn in range(1, self.max_turns + 1):
            bound_logger = logger.bind(turn=turn)
            message = self.chat(messages)
            # The assistant turn (with its tool_calls) must stay in the history.
            bound_logger.info("assistant_message", message=message)
            messages.append(message)

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                bound_logger.info("final_answer", message=message.get("content"))
                return message.get("content", "")
            for tool_call in tool_calls:
                tool_output = self._execute_tool_call(tool_call)
                messages.append(tool_output)

        logger.warn("max_turns_reached", max_turns=self.max_turns)
        return "Max turns reached without a final answer."

    def _execute_tool_call(self, tool_call: dict) -> dict:
        """Run one tool call and return the tool message for the history."""
        function = tool_call.get("function", {})
        function_name = function.get("name", "")
        function_to_call = self.available_functions.get(function_name)

        if function_to_call is None:
            logger.error("unknown_tool_call", tool_call=function_name)
            content = f"Error: unknown tool '{function_name}'."
        else:
            # Any failure is reported back to the model so every tool call gets
            # a response and one bad call doesn't abort the others.
            try:
                function_args = self._parse_arguments(function.get("arguments"))
                allowed = self.allowed_params.get(function_name, set())
                dropped = sorted(set(function_args) - allowed)
                if dropped:
                    logger.error("undeclared_args", function_name=function_name, dropped=dropped)
                function_args = {k: v for k, v in function_args.items() if k in allowed}
                logger.info("trigger_tool_call", tool_call=tool_call, function_args=function_args)
                content = str(function_to_call(**function_args))
                logger.info("tool_call_output", function_name=function_name, output=content)
            except Exception as e:
                logger.error("tool_call_error", function_name=function_name, error=str(e))
                content = f"Error: {type(e).__name__}: {e}"

        return {"role": "tool", "tool_name": function_name, "content": content}

    @staticmethod
    def _parse_arguments(arguments: Any) -> dict:
        """Ollama normally sends a dict; tolerate a JSON string too."""
        if not arguments:
            return {}
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        if not isinstance(arguments, dict):
            raise ValueError(f"tool arguments must be an object, got {type(arguments).__name__}")
        return arguments


if __name__ == "__main__":
    caller = OllamaCaller(model=DEFAULT_MODEL)
    print(caller.run("What is the temperature and wind speed in Redmond, WA on 2025-01-15?"))
