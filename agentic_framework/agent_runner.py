import os
import sys

# Allow running this file directly (`python agentic_framework/<file>.py`):
# only this file's directory is on sys.path then, not the repo root. Append
# (don't insert) so the repo's `operator/` dir can't shadow the stdlib module.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentic_framework.llm_caller import DEFAULT_MODEL, OllamaCaller  # noqa: E402
from agentic_framework.tool_registrar import ToolRegistrar  # noqa: E402
from utils.logger import logger  # noqa: E402,F401


class AgentRunner:
  """Runs user prompts against the tools exposed by a ToolRegistrar.

  Thin wrapper around OllamaCaller, which talks to the local Ollama server
  directly (no LiteLLM).
  """

  def __init__(
      self,
      model: str = DEFAULT_MODEL,
      registrar: ToolRegistrar | None = None,
      max_turns: int = 15,
  ):
    # Accept the old LiteLLM-style "ollama/<model>" name as well.
    self.model = model.removeprefix("ollama/")
    self.max_turns = max_turns
    self.registrar = registrar or ToolRegistrar().discover()

    # Tool definitions come from the registrar.
    self.tools = self.registrar.tools
    self.available_functions = self.registrar.available_functions
    self.allowed_params = self.registrar.allowed_params

    self.caller = OllamaCaller(
        model=self.model,
        registrar=self.registrar,
        max_turns=max_turns,
    )

  def run(self, user_prompt: str) -> str:
    return self.caller.run(user_prompt)


# Ensure Ollama is running locally on port 11434 (or set OLLAMA_HOST).

if __name__ == "__main__":
  runner = AgentRunner(model="granite4:3b")
  print(runner.run("What is the temperature and wind speed in Redmond, WA on 2025-01-15?"))
  print(runner.run("Create a markdown file containing 'Hello, World!' in /home/a1works/agent_hub/temp directory then read the file and write its contents to a new file in the same folder. Then Add the number of files in the folder to count.md file int he same folder."))
  