"""
dash-langsmith: automatic LangSmith tracing for Dash MCP tool calls.

Install this package and every MCP tools/call request to your Dash app is
recorded as a LangSmith run — no code changes required.

Configuration via environment variables:
  LANGSMITH_API_KEY      (required)
  LANGSMITH_PROJECT      LangSmith project name (optional, falls back to LANGCHAIN_PROJECT)
  DASH_MCP_PATH          MCP endpoint path (default: /_mcp)
"""

import os

from dash import hooks

from .decorator import mcp_traced
from .middleware import LangSmithMCPMiddleware


@hooks.setup()
def _install_mcp_tracing(app):
    mcp_path = (
        getattr(app, "mcp_path", None)
        or os.environ.get("DASH_MCP_PATH", "/_mcp")
    )
    project_name = (
        os.environ.get("LANGSMITH_PROJECT")
        or os.environ.get("LANGCHAIN_PROJECT")
    )

    app.server.wsgi_app = LangSmithMCPMiddleware(
        app.server.wsgi_app,
        mcp_path=mcp_path,
        project_name=project_name,
        # environment is read from LANGSMITH_ENVIRONMENT inside the middleware
    )


__all__ = ["LangSmithMCPMiddleware", "mcp_traced"]
