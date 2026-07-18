# dash-langsmith

Automatic [LangSmith](https://smith.langchain.com) tracing for [Dash MCP](https://dash.plotly.com/dash-mcp) tool calls.

Every time an AI agent calls a tool on your Dash MCP server, a run is recorded in LangSmith — latency, inputs, outputs, and errors included. No code changes to your app required.

## Install

```bash
pip install dash-langsmith
```

## Usage

Set your API key and run your app normally.

```bash
export LANGSMITH_API_KEY=your-key
export LANGSMITH_PROJECT=my-dash-app  # optional
python app.py
```

That's it. The `dash_hooks` entry point registers the tracing middleware automatically at startup.

## How it works

`dash-langsmith` uses Dash's [plugin hooks](https://dash.plotly.com/dash-plugins-using-hooks) system. On startup, `hooks.setup` wraps `app.server.wsgi_app` with a lightweight WSGI middleware that intercepts POST requests to `/_mcp`. When a `tools/call` JSON-RPC message arrives, it creates a LangSmith run before dispatching to Dash and patches it with the response on the way out.

Only `tools/call` requests are traced. Layout, resource, and `tools/list` requests pass through untouched.

## Optional: richer traces with `@mcp_traced`

For explicit per-tool control — custom names, docstrings, per-tool project routing — use the `@mcp_traced` decorator instead of `@mcp_enabled`:

```python
from dash_langsmith import mcp_traced

@mcp_traced(name="get_inventory", expose_docstring=True, project_name="my-dash-app")
def get_inventory(category: str) -> dict:
    """Return inventory levels for a product category."""
    ...
```

## Configuration

| Environment variable  | Default    | Description                          |
|-----------------------|------------|--------------------------------------|
| `LANGSMITH_API_KEY`   | —          | Required                             |
| `LANGSMITH_PROJECT`   | —          | LangSmith project (falls back to `LANGCHAIN_PROJECT`) |
| `DASH_MCP_PATH`       | `/_mcp`    | Override if you set a custom `mcp_path` |

## Requirements

- Dash ≥ 4.3.0 (MCP support)
- langsmith ≥ 0.1.0
