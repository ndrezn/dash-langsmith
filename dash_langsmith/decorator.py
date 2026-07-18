"""
@mcp_traced decorator: wraps @mcp_enabled and adds LangSmith tracing.

Use this instead of @mcp_enabled when you want per-tool traces with
structured inputs and outputs recorded in LangSmith.
"""

from typing import Optional

import langsmith
from dash.mcp import mcp_enabled as _dash_mcp_enabled


def mcp_traced(
    func=None,
    *,
    name: Optional[str] = None,
    expose_docstring: Optional[bool] = None,
    project_name: Optional[str] = None,
):
    """
    Expose a function as a Dash MCP tool and trace every invocation to LangSmith.

    Supports both bare and parameterized usage::

        @mcp_traced
        def get_sales(region: str) -> dict:
            ...

        @mcp_traced(name="sales_by_region", expose_docstring=True, project_name="my-app")
        def get_sales(region: str) -> dict:
            \"\"\"Return sales total for a given region.\"\"\"
            ...

    Args:
        name: Tool name shown to AI agents. Defaults to the function name.
        expose_docstring: Whether to include the docstring in the tool description.
            Inherits the app-wide setting when unset.
        project_name: LangSmith project to record runs under.
            Falls back to the LANGCHAIN_PROJECT env var when unset.
    """

    def decorator(fn):
        traced = langsmith.traceable(
            name=name or fn.__name__,
            run_type="tool",
            project_name=project_name,
        )(fn)

        mcp_kwargs = {}
        if name is not None:
            mcp_kwargs["name"] = name
        if expose_docstring is not None:
            mcp_kwargs["expose_docstring"] = expose_docstring

        if mcp_kwargs:
            return _dash_mcp_enabled(**mcp_kwargs)(traced)
        return _dash_mcp_enabled(traced)

    if func is not None:
        return decorator(func)
    return decorator
