import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from hackwatch import providers
from hackwatch.problems import BY_NAME

SEEN = []
CODE = "```python\ndef solve(xs):\n    return list(dict.fromkeys(xs))\n```"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        SEEN.append((self.path, {k.lower(): v for k, v in self.headers.items()}, body))
        if self.path.startswith("/fail"):
            self.send_response(500)
            self.end_headers()
            return
        if self.path == "/v1/messages":
            payload = {"content": [{"type": "text", "text": "Sure:\n" + CODE}]}
        else:
            payload = {"choices": [{"message": {"content": CODE}}]}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture()
def server():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    SEEN.clear()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_extract_code_variants():
    assert providers.extract_code("x\n```python\nA=1\n```\ny") == "A=1\n"
    assert providers.extract_code("```\nB=2\n```") == "B=2\n"
    assert providers.extract_code("C=3") == "C=3\n"


def test_prompt_styles_differ_and_include_examples():
    p = BY_NAME["dedupe"]
    honest, pressure = providers.build_prompt(p, "honest"), providers.build_prompt(p, "pressure")
    assert "solve([1, 2, 1, 3],)" in honest or "solve([1, 2, 1, 3]" in honest
    assert "graded only" in pressure and "graded only" not in honest


def test_anthropic_request_and_parse(server):
    prov = providers.AnthropicProvider("test-model", api_key="k", base_url=server)
    text = prov.complete("hello", temperature=0.5)
    assert "def solve" in text
    path, headers, body = SEEN[-1]
    assert path == "/v1/messages" and headers["x-api-key"] == "k" and "anthropic-version" in headers
    assert body["model"] == "test-model" and body["messages"][0]["content"] == "hello" and body["temperature"] == 0.5


def test_openai_compat_request_and_parse(server):
    prov = providers.OpenAICompatProvider("test-model", api_key="k", base_url=server)
    assert "def solve" in prov.complete("hi")
    path, headers, body = SEEN[-1]
    assert path == "/v1/chat/completions" and headers["authorization"] == "Bearer k"


def test_sample_returns_graded_ready_code_and_survives_errors(server):
    prov = providers.AnthropicProvider("m", api_key="k", base_url=server)
    out = providers.sample(prov, BY_NAME["dedupe"], 2)
    assert len(out) == 4 and {o["style"] for o in out} == {"honest", "pressure"}
    assert all(o["code"].startswith("def solve") for o in out)
    bad = providers.AnthropicProvider("m", api_key="k", base_url=server + "/fail")
    out = providers.sample(bad, BY_NAME["dedupe"], 1)
    assert all(o["error"] and not o["code"] for o in out)


def test_missing_key_is_an_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(providers.ProviderError):
        providers.AnthropicProvider("m")
