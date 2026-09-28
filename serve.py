"""AnythingLLM 文档工作台静态服务(替换 python -m http.server)

- 静态:上传页 uploader/,默认端口 8001
- GET /api/doc-content?name=<doc.json> :读取本机 AnythingLLM
  storage/documents/custom-documents 下的文档 JSON,返回 title + pageContent,
  供网页「点击列表项预览正文」使用(AnythingLLM 公开 API 不返回文档正文)。
"""
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(ROOT, "uploader")
DOC_DIR = os.path.join(
    os.environ.get("APPDATA", ""),
    "anythingllm-desktop",
    "storage",
    "documents",
    "custom-documents",
)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=UPLOAD_DIR, **kwargs)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/doc-content":
            name = parse_qs(url.query).get("name", [""])[0]
            self._doc_content(name)
            return
        return super().do_GET()

    def _doc_content(self, name):
        name = os.path.basename(name)  # 防目录穿越
        if not name.endswith(".json"):
            return self._json(400, {"error": "invalid document name"})
        path = os.path.join(DOC_DIR, name)
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            return self._json(200, {
                "title": d.get("title", name),
                "content": d.get("pageContent", ""),
                "meta": {
                    "wordCount": d.get("wordCount"),
                    "published": d.get("published"),
                    "tokenEstimate": d.get("token_count_estimate"),
                },
            })
        except FileNotFoundError:
            return self._json(404, {"error": "document not found"})
        except Exception as exc:  # noqa: BLE001
            return self._json(500, {"error": str(exc)})

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # 保持安静,避免控制台刷屏
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    print(f"文档工作台: http://127.0.0.1:{port}  (doc dir: {DOC_DIR})")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()