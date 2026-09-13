import http.client
import json
import os
import urllib.parse

BASE = os.environ.get("COGNEE_SERVER_URL", "http://127.0.0.1:28195").rstrip("/")
_TIMEOUT = float(os.environ.get("COGNEE_TIMEOUT", "300"))


class _HttpClient:
    """Thread-safe synchronous HTTP client that avoids lazy SSL context
    creation in child threads. Uses http.client for http:// and httpx for
    https:// as a fallback.
    """

    def __init__(self, base_url: str, timeout: float = 300.0):
        self.base_url = base_url
        self.timeout = timeout
        parsed = urllib.parse.urlparse(base_url)
        self.scheme = parsed.scheme
        self.host = parsed.hostname
        self.port = parsed.port
        self.path_prefix = parsed.path

    def _request(self, method: str, path: str, body: dict | None = None, headers: dict | None = None) -> dict:
        if self.scheme != "http":
            return self._httpx_request(method, path, body, headers)

        full_path = (self.path_prefix or "") + path
        conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        payload = json.dumps(body) if body is not None else None
        req_headers = headers or {}
        if payload is not None and "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/json"
        try:
            conn.request(method, full_path, body=payload, headers=req_headers)
            response = conn.getresponse()
            data = response.read().decode("utf-8")
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}: {data}")
            return json.loads(data) if data else {}
        finally:
            conn.close()

    def _httpx_request(self, method: str, path: str, body: dict | None = None, headers: dict | None = None) -> dict:
        import httpx

        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            r = client.request(method, path, json=body, headers=headers or {})
            r.raise_for_status()
            return r.json()


def _client():
    return _HttpClient(BASE, _TIMEOUT)


def sync(repo_path: str | None = None, force: bool = False) -> str:
    return _client()._request("POST", "/sync", {"repo_path": repo_path or os.getcwd(), "force": force})["status"]


def search(query: str, scope: str = "code", limit: int = 10) -> dict:
    return _client()._request("POST", "/search", {"query": query, "scope": scope, "limit": limit})


def explore(target: str, direction: str = "callers", depth: int = 2) -> dict:
    return _client()._request("POST", "/explore", {"target": target, "direction": direction, "depth": depth})


def trace(
    step_id: str | None = None,
    tool: str = "",
    args: dict | None = None,
    result: str = "",
    touched_files: list[str] | None = None,
    touched_symbols: list[str] | None = None,
    parent_step_id: str | None = None,
) -> str:
    return _client()._request(
        "POST",
        "/trace",
        {
            "step_id": step_id,
            "tool": tool,
            "args": args or {},
            "result": result,
            "touched_files": touched_files or [],
            "touched_symbols": touched_symbols or [],
            "parent_step_id": parent_step_id,
        },
    )["step_id"]


def remember(data: str, dataset_name: str = "agentic_graph", node_set: list[str] | None = None) -> dict:
	return _client()._request(
		"POST",
		"/api/v1/remember",
		{"data": data, "dataset_name": dataset_name, "node_set": node_set or []},
	)


def recall(query: str, dataset_name: str = "agentic_graph", node_set: list[str] | None = None, top_k: int = 5) -> dict:
	return _client()._request(
		"POST",
		"/api/v1/recall",
		{"query": query, "dataset_name": dataset_name, "node_set": node_set or [], "top_k": top_k},
	)


def correlate(target: str) -> dict:
	return _client()._request("POST", "/correlate", {"target": target})


def watcher_status() -> dict:
	return _client()._request("GET", "/health")
