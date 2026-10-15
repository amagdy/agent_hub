"""Discover tools in the `tools` package and expose them to the agentic loop.

Tool convention (see tools/weather.py):
  * Every public class in a `tools.*` module is a tool group.
  * `__init__`'s docstring holds a JSON schema for the constructor arguments.
  * Every public method with a JSON docstring becomes one tool. Its schema is
    merged with the constructor schema, since the class is instantiated with
    the constructor arguments right before the method is called.
  * Every public module-level function with a JSON docstring is a standalone
    tool (see tools/file_io.py).
  * Support classes and helper functions without a JSON docstring are ignored.
"""

import importlib
import inspect
import json
import pkgutil
from typing import Any, Callable
from utils.logger import logger  # noqa: E402,F401


DEFAULT_SESSION_ID = "default"
TOOLS_PACKAGE = "tools"


def _parse_schema(obj: Any) -> dict | None:
    """Return the JSON schema stored in obj's docstring, or None."""
    doc = inspect.getdoc(obj)
    if not doc:
        return None
    try:
        schema = json.loads(doc)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON schema from docstring of {obj}: {doc}")
        return None
    return schema if isinstance(schema, dict) else None


class ToolRegistrar:
    def __init__(self, session_id: str = DEFAULT_SESSION_ID, package: str = TOOLS_PACKAGE):
        self.package = package
        self._schemas: dict[str, dict] = {}
        self._functions: dict[str, Callable[..., Any]] = {}
        self.session_id = session_id        

    # ---- discovery / registration -------------------------------------
    def discover(self) -> "ToolRegistrar":
        """Import every module in the tools package and register its tools."""
        pkg = importlib.import_module(self.package)
        for info in pkgutil.iter_modules(pkg.__path__):
            if info.name.startswith("_"):
                continue
            module = importlib.import_module(f"{self.package}.{info.name}")
            for _, cls in inspect.getmembers(module, inspect.isclass):
                if cls.__module__ == module.__name__ and not cls.__name__.startswith("_"):
                    self._register_class(module.__name__, cls)
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if func.__module__ == module.__name__ and not name.startswith("_"):
                    self._register_function(module.__name__, name, func)
        return self

    def _add_tool(self, module_name: str, name: str, schema: dict, props: dict,
                  required: list[str], func: Callable[..., Any]) -> None:
        tool_name = f"{module_name.split('.')[-1]}_{name}"
        if tool_name in self._schemas:
            raise ValueError(f"Duplicate tool name: {tool_name}")
        self._schemas[tool_name] = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": schema.get("description", ""),
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                },
            },
        }
        self._functions[tool_name] = func

    def _register_function(self, module_name: str, name: str, func: Callable[..., Any]) -> None:
        schema = _parse_schema(func)
        if schema is None:
            return
        params = schema.get("parameters", {})
        self._add_tool(module_name, name, schema, dict(params.get("properties", {})),
                       list(params.get("required", [])), func)

    def _register_class(self, module_name: str, cls: type) -> None:
        init_schema = _parse_schema(cls.__init__) or {}
        init_params = init_schema.get("parameters", {})
        init_props = dict(init_params.get("properties", {}))
        init_required = list(init_params.get("required", []))
        init_arg_names = set(inspect.signature(cls.__init__).parameters) - {"self"}

        for name, method in inspect.getmembers(cls, inspect.isfunction):
            if name.startswith("_"):
                continue
            schema = _parse_schema(method)
            if schema is None:
                continue

            params = schema.get("parameters", {})
            props = {**init_props, **params.get("properties", {})}
            required = list(dict.fromkeys(init_required + params.get("required", [])))

            self._add_tool(module_name, name, schema, props, required,
                           self._make_callable(cls, name, init_arg_names))
    
    def _get_cached_tool_instance(self, cls: type, init_kwargs: dict, session_id: str) -> Any:
        """Return a cached instance of the tool class, or create a new one if not cached."""
        cache_key = f"{cls.__module__}.{cls.__name__}:{json.dumps(init_kwargs, sort_keys=True)}"
        if not hasattr(self, "_tool_instance_cache"):
            self._tool_instance_cache = {}
        if session_id not in self._tool_instance_cache:
            self._tool_instance_cache[session_id] = {}
        if cache_key not in self._tool_instance_cache[session_id]:
            self._tool_instance_cache[session_id][cache_key] = cls(**init_kwargs)
        return self._tool_instance_cache[session_id][cache_key]

    def end_session(self, session_id: str) -> None:
        """Clear the cached tool instances for a given session."""
        if hasattr(self, "_tool_instance_cache") and session_id in self._tool_instance_cache:
            del self._tool_instance_cache[session_id]
    
    def _make_callable(self, cls: type, method_name: str, init_arg_names: set[str]):
        def call(**kwargs: Any) -> Any:
            init_kwargs = {k: v for k, v in kwargs.items() if k in init_arg_names}
            method_kwargs = {k: v for k, v in kwargs.items() if k not in init_arg_names}
            tool_instance = self._get_cached_tool_instance(cls, init_kwargs, self.session_id)
            return getattr(tool_instance, method_name)(**method_kwargs)

        return call

    # ---- what the agentic loop consumes --------------------------------
    @property
    def tools(self) -> list[dict]:
        """OpenAI-style tool schemas, ready for `completion(tools=...)`."""
        return list(self._schemas.values())

    @property
    def available_functions(self) -> dict[str, Callable[..., Any]]:
        return dict(self._functions)

    @property
    def allowed_params(self) -> dict[str, set[str]]:
        return {
            name: set(s["function"]["parameters"]["properties"])
            for name, s in self._schemas.items()
        }


def load_tools(package: str = TOOLS_PACKAGE) -> ToolRegistrar:
    """Discover and register all tools in `package`."""
    return ToolRegistrar(package=package).discover()
