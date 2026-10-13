#!/usr/bin/env python3
"""本地拦截 Claude Code 的 API 请求：只把请求体落盘，然后返回一个错误，不转发。

用法：python3 capture_server.py [port] [outdir]
"""
import json, os, sys, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
OUT = sys.argv[2] if len(sys.argv) > 2 else "captured"
os.makedirs(OUT, exist_ok=True)
n = [0]


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _handle(self, method):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        n[0] += 1
        path = self.path
        rec = {
            "seq": n[0],
            "time": datetime.datetime.now().isoformat(timespec="seconds"),
            "method": method,
            "path": path,
            "headers": {k: v for k, v in self.headers.items()},
            "body_bytes": len(body),
        }
        base = os.path.join(OUT, f"{n[0]:03d}")
        with open(base + ".meta.json", "w") as f:
            json.dump(rec, f, indent=2, ensure_ascii=False)
        with open(base + ".body.bin", "wb") as f:
            f.write(body)
        try:
            parsed = json.loads(body)
            with open(base + ".body.json", "w") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            rec["parsed"] = True
            rec["model"] = parsed.get("model")
            rec["system_blocks"] = len(parsed.get("system") or []) if isinstance(parsed.get("system"), list) else 1
            rec["tools"] = len(parsed.get("tools") or [])
            rec["messages"] = len(parsed.get("messages") or [])
        except Exception as e:
            rec["parsed"] = f"error: {e}"
        with open(base + ".meta.json", "w") as f:
            json.dump(rec, f, indent=2, ensure_ascii=False)
        print(f"[capture] #{n[0]} {method} {path} {len(body)}B model={rec.get('model')} "
              f"system={rec.get('system_blocks')} tools={rec.get('tools')}", flush=True)
        payload = json.dumps({"type": "error", "error": {"type": "invalid_request_error",
                                                         "message": "captured locally; not forwarded"}}).encode()
        self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        self._handle("POST")

    def do_GET(self):
        self._handle("GET")

    def log_message(self, *a):
        pass


print(f"capture server on http://127.0.0.1:{PORT}  -> {OUT}/", flush=True)
ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
