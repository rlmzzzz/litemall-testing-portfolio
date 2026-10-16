"""
本地 Mock 接口服务（仅用 Python 标准库，无需联网、无额外依赖）。
作用：给练习用的接口自动化框架提供一个稳定、可控的被测对象。
面试可讲："为了练习，我用一个 stdlib 的 http.server 自己写了一个 mock REST 服务，
再针对它写了一套数据驱动测试——这样不依赖任何外部网络也能演示完整流程。"
"""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 模拟一份内存里的商品数据
PRODUCTS = {
    1: {"id": 1, "name": "机械键盘", "price": 299},
    2: {"id": 2, "name": "无线鼠标", "price": 99},
}


class Handler(BaseHTTPRequestHandler):
    # ---- 工具方法 ----
    def _send(self, code, payload=None, extra_headers=None):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        if payload is not None:
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def _auth_ok(self):
        # 简单鉴权：请求头带 Authorization: Bearer secret-token 才算登录
        return self.headers.get("Authorization") == "Bearer secret-token"

    # ---- GET ----
    def do_GET(self):
        if self.path == "/api/products":
            return self._send(200, {"code": 0, "data": list(PRODUCTS.values())})
        if self.path == "/api/products/1":
            return self._send(200, {"code": 0, "data": PRODUCTS[1]})
        if self.path == "/api/products/999":
            return self._send(404, {"code": 404, "msg": "not found"})
        if self.path == "/api/slow":
            time.sleep(1.5)  # 故意慢，用于演示响应时间断言
            return self._send(200, {"code": 0, "data": "ok"})
        if self.path == "/api/admin/users":
            if not self._auth_ok():
                return self._send(401, {"code": 401, "msg": "unauthorized"})
            return self._send(200, {"code": 0, "data": [{"id": 1, "name": "admin"}]})
        return self._send(404, {"code": 404, "msg": "not found"})

    # ---- POST ----
    def do_POST(self):
        if self.path == "/api/products":
            body = self._read_body()
            new_id = max(PRODUCTS) + 1
            PRODUCTS[new_id] = {
                "id": new_id,
                "name": body.get("name", "未命名"),
                "price": body.get("price", 0),
            }
            return self._send(201, {"code": 0, "data": PRODUCTS[new_id]})
        if self.path == "/api/login":
            body = self._read_body()
            if body.get("username") == "admin" and body.get("password") == "admin123":
                return self._send(200, {"code": 0, "data": {"token": "secret-token"}})
            return self._send(401, {"code": 401, "msg": "bad credentials"})
        return self._send(404, {"code": 404, "msg": "not found"})

    # ---- DELETE ----
    def do_DELETE(self):
        if self.path == "/api/products/1":
            return self._send(200, {"code": 0, "data": "deleted"})
        return self._send(404, {"code": 404, "msg": "not found"})

    # 让控制台安静
    def log_message(self, *args):
        pass


def run_server(host="127.0.0.1", port=8099):
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"[mock_api] 服务已启动：http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
