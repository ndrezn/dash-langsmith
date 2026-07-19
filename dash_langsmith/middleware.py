"""
WSGI middleware that traces Dash MCP tool calls to LangSmith.

Drop-in: wrap app.server.wsgi_app and every tools/call request to your
Dash MCP endpoint is automatically recorded as a LangSmith run.

Parent-run linking
------------------
If the MCP client injects a LangSmith run ID into the tool call's _meta
field, the Dash run is created as a child of that run — giving you a full
trace from LLM decision → Dash tool → result in one LangSmith tree.

On the agent side (e.g. langchain-mcp-adapters), emit:

    {"method": "tools/call", "params": {
        "name": "...", "arguments": {...},
        "_meta": {"langsmith_run_id": "<parent-run-uuid>"}
    }}

Session tagging
---------------
The MCP initialize handshake is intercepted to extract the client name
and version. All subsequent tool-call runs from that session are tagged
with the client info.
"""

import io
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import langsmith


class LangSmithMCPMiddleware:
    """
    WSGI middleware that intercepts Dash MCP tool calls and traces them to LangSmith.

    Automatically installed via the dash_hooks entry point when dash-langsmith
    is installed. Can also be applied manually::

        app.server.wsgi_app = LangSmithMCPMiddleware(
            app.server.wsgi_app,
            project_name="my-dash-app",
        )
    """

    def __init__(
        self,
        app,
        mcp_path: str = "/_mcp",
        project_name: Optional[str] = None,
    ):
        self.app = app
        self.mcp_path = mcp_path
        self.project_name = project_name
        self.client = langsmith.Client()
        # session_id -> {"client_name": str, "client_version": str}
        self._sessions: dict[str, dict] = {}

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "")

        if not (path.endswith(self.mcp_path) and method == "POST"):
            return self.app(environ, start_response)

        try:
            content_length = int(environ.get("CONTENT_LENGTH") or 0)
        except (ValueError, TypeError):
            content_length = 0

        body = environ["wsgi.input"].read(content_length)
        environ["wsgi.input"] = io.BytesIO(body)

        try:
            rpc = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.app(environ, start_response)

        rpc_method = rpc.get("method")

        # Intercept initialize to capture client identity for session tagging.
        if rpc_method == "initialize":
            self._handle_initialize(environ, rpc)
            return self.app(environ, start_response)

        if rpc_method != "tools/call":
            return self.app(environ, start_response)

        return self._trace_tool_call(environ, start_response, rpc)

    # ------------------------------------------------------------------

    def _handle_initialize(self, environ, rpc: dict) -> None:
        session_id = self._session_id(environ)
        client_info = rpc.get("params", {}).get("clientInfo", {})
        self._sessions[session_id] = {
            "client_name": client_info.get("name", "unknown"),
            "client_version": client_info.get("version", ""),
        }

    def _trace_tool_call(self, environ, start_response, rpc: dict):
        params = rpc.get("params", {})
        tool_name = params.get("name", "unknown_tool")
        arguments = params.get("arguments", {})
        meta = params.get("_meta", {})

        # Link to a parent LangSmith run if the agent provided one.
        parent_run_id: Optional[str] = meta.get("langsmith_run_id")

        # Tag with the MCP client identity captured at initialize.
        session_id = self._session_id(environ)
        session = self._sessions.get(session_id, {})
        tags = ["dash-mcp"]
        if session.get("client_name"):
            tags.append(f"mcp-client:{session['client_name']}")

        extra = {"metadata": {"mcp_session_id": session_id, **session}}
        if meta:
            extra["metadata"]["mcp_meta"] = meta

        run_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        run_created = False

        try:
            self.client.create_run(
                id=run_id,
                name=tool_name,
                run_type="tool",
                inputs={"arguments": arguments},
                project_name=self.project_name,
                parent_run_id=parent_run_id,
                start_time=start_time,
                tags=tags,
                extra=extra,
            )
            run_created = True
        except Exception:
            pass

        response_chunks = []
        response_meta: dict = {}

        def capturing_start_response(status, headers, exc_info=None):
            response_meta["status"] = status
            return start_response(status, headers, exc_info)

        iterable = self.app(environ, capturing_start_response)

        try:
            for chunk in iterable:
                response_chunks.append(chunk)
        except Exception as exc:
            if run_created:
                try:
                    self.client.update_run(
                        run_id,
                        error=str(exc),
                        end_time=datetime.now(timezone.utc),
                    )
                except Exception:
                    pass
            raise
        finally:
            if hasattr(iterable, "close"):
                iterable.close()

        full_body = b"".join(response_chunks)
        end_time = datetime.now(timezone.utc)

        outputs: dict = {}
        error: Optional[str] = None

        try:
            resp_json = json.loads(full_body)
            if "result" in resp_json:
                outputs = {"result": resp_json["result"]}
            elif "error" in resp_json:
                error = json.dumps(resp_json["error"])
        except (json.JSONDecodeError, UnicodeDecodeError):
            outputs = {"raw": full_body.decode("utf-8", errors="replace")}

        if run_created:
            try:
                self.client.update_run(
                    run_id,
                    outputs=outputs,
                    error=error,
                    end_time=end_time,
                )
            except Exception:
                pass

        return [full_body]

    @staticmethod
    def _session_id(environ: dict) -> str:
        # MCP HTTP transport uses mcp-session-id header per the spec.
        key = "HTTP_MCP_SESSION_ID"
        return environ.get(key) or "no-session"
