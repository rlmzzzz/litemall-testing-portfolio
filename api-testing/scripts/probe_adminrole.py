# -*- coding: utf-8 -*-
"""
诊断：/admin/admin/list 与 /admin/role/list 在 mall123 身份下到底该返回什么？
以及：带 admin123 的 cookie 时会变成什么？
"""
import json
import sys
import urllib.request
import urllib.error
import http.cookiejar

sys.stdout.reconfigure(encoding='utf-8')
BASE = "http://127.0.0.1:8080"


def login(user, opener=None):
    req = urllib.request.Request(BASE + "/admin/auth/login",
                                data=json.dumps({"username": user, "password": user}).encode(),
                                headers={"Content-Type": "application/json"})
    op = opener or urllib.request.build_opener()
    return json.loads(op.open(req, timeout=10).read())["data"]["token"]


def probe(tag, path, headers=None, opener=None):
    req = urllib.request.Request(BASE + path, headers=headers or {})
    op = opener or urllib.request.build_opener()
    try:
        r = op.open(req, timeout=15)
        raw = r.read()
        d = json.loads(raw)
        data = d.get("data")
        extra = ""
        if isinstance(data, dict) and data.get("list"):
            first = data["list"][0]
            extra = "  首条=%s" % json.dumps(first, ensure_ascii=False)[:70]
        print("  %-40s errno=%-5s %-7s %s%s" % (tag, d.get("errno"), "%dB" % len(raw), d.get("errmsg"), extra))
    except Exception as e:
        print("  %-40s 异常 %s" % (tag, e))


PATHS = ["/admin/admin/list?page=1&limit=5", "/admin/role/list?page=1&limit=5",
         "/admin/user/list?page=1&limit=5"]

tok_mall = login("mall123")
tok_admin = login("admin123")

print("=== A. 只带 mall123 的 header（无 cookie）—— 这才是真实权限 ===")
for p in PATHS:
    probe(p.split("?")[0], p, headers={"X-Litemall-Admin-Token": tok_mall})

print()
print("=== B. 什么凭证都不带 ===")
for p in PATHS:
    probe(p.split("?")[0], p)

print()
print("=== C. 模拟「先登录过 admin123」，只带 admin123 的 cookie ===")
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
login("admin123", opener=op)
print("  cookie = %s" % [c.value[:18] for c in cj])
for p in PATHS:
    probe(p.split("?")[0] + "（admin123 cookie）", p, opener=op)

print()
print("=== D. admin123 的 cookie + mall123 的 header（Postman 实际情形）===")
for p in PATHS:
    probe(p.split("?")[0] + "（cookie+mall header）", p,
          headers={"X-Litemall-Admin-Token": tok_mall}, opener=op)

print()
print("=== E. 身份自证：用 admin123 的 cookie 去问 /admin/auth/info ===")
probe("/admin/auth/info（只带 admin123 cookie）", "/admin/auth/info", opener=op)
