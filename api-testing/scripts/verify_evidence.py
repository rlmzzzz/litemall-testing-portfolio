# -*- coding: utf-8 -*-
"""
提单前证据校准：把 3 个接口缺陷的"实际结果"重新实测一遍，
保证禅道单里的数字/返回值与现场完全一致。

用法：python verify_evidence.py
"""
import json
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8080"
ACCOUNTS = {"admin123": "admin123", "mall123": "mall123", "promotion123": "promotion123"}


def call(path, method="GET", body=None, token=None):
    headers = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-Litemall-Admin-Token"] = token
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        resp = urllib.request.urlopen(req, timeout=25)
        return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return -1, str(e).encode()


def login(u):
    _, raw = call("/admin/auth/login", "POST", {"username": u, "password": ACCOUNTS[u]})
    return json.loads(raw)["data"]["token"]


def brief(raw, keys=("errno", "errmsg", "total", "page", "limit", "pages")):
    d = json.loads(raw)
    data = d.get("data") or {}
    out = {k: d.get(k) for k in ("errno", "errmsg")}
    if isinstance(data, dict):
        for k in keys[2:]:
            if k in data:
                out[k] = data[k]
        if isinstance(data.get("list"), list):
            out["list_len"] = len(data["list"])
    return out


def show(tag, path, token=None, method="GET", body=None):
    status, raw = call(path, method=method, body=body, token=token)
    try:
        info = brief(raw)
    except Exception:  # noqa: BLE001
        info = raw[:120].decode("utf-8", "replace")
    print("%-46s HTTP=%-4s 字节=%-8d %s" % (tag, status, len(raw), info))
    return raw


print("=" * 108)
print("一、Bug-7 证据校准：低权限账号能否访问 /admin/dashboard")
print("=" * 108)

tokens = {u: login(u) for u in ACCOUNTS}
for u in ACCOUNTS:
    show("%s 仅 header 访问 /admin/dashboard" % u, "/admin/dashboard", tokens[u])

print()
print("-- 身份自证 /admin/auth/info（证明 token 到底属于谁）--")
for u in ("mall123", "promotion123"):
    status, raw = call("/admin/auth/info", token=tokens[u])
    d = json.loads(raw)["data"]
    perms = d.get("perms") or []
    print("%s -> name=%s roles=%s perms=%d 条" % (u, d.get("name"), d.get("roles"), len(perms)))
    print("     权限清单: %s" % ", ".join(p.strip() for p in perms))

print()
print("-- 对照组：同一 token 访问其它 13 个接口 --")
control = [
    "/admin/goods/list", "/admin/user/list", "/admin/order/list", "/admin/coupon/list",
    "/admin/topic/list", "/admin/issue/list", "/admin/keyword/list", "/admin/ad/list",
    "/admin/role/list", "/admin/log/list", "/admin/comment/list", "/admin/aftersale/list",
    "/admin/groupon/list", "/admin/brand/list", "/admin/category/list",
]
for p in control:
    show("mall123 -> %s" % p, p + "?page=1&limit=5", tokens["mall123"])

print()
print("=" * 108)
print("二、Bug-8 证据校准：/admin/goods/list 分页参数边界")
print("=" * 108)
for q in ["page=1&limit=5", "page=1&limit=0", "page=1&limit=-1", "page=1&limit=abc",
          "page=1&limit=10000", "page=50&limit=5", "page=9999&limit=5", "page=0&limit=5"]:
    show("admin123 goods/list?%s" % q, "/admin/goods/list?" + q, tokens["admin123"])

print()
print("-- limit=0 与 limit=5 响应体大小对比（列表接口臃肿证据）--")
for q in ["page=1&limit=5", "page=1&limit=0"]:
    _, raw = call("/admin/goods/list?" + q, token=tokens["admin123"])
    d = json.loads(raw)
    lst = (d.get("data") or {}).get("list") or []
    print("  %-16s 响应=%d 字节, list=%d 条" % (q, len(raw), len(lst)))
    if lst:
        keys = list(lst[0].keys())
        print("     单条字段(%d): %s" % (len(keys), ",".join(keys)))

print()
print("=" * 108)
print("三、Bug-6 证据校准：/admin/goods/detail 异常 id")
print("=" * 108)
for q in ["id=99999999", "id=0", "id=-1", "id=99999999999", "id=abc", "id=1181009"]:
    show("admin123 goods/detail?%s" % q, "/admin/goods/detail?" + q, tokens["admin123"])
show("admin123 goods/detail（不传 id）", "/admin/goods/detail", tokens["admin123"])

print()
print("=" * 108)
print("四、未登录基线（证明登录校验是全局生效的）")
print("=" * 108)
for p in ["/admin/dashboard", "/admin/goods/list", "/admin/goods/detail?id=1"]:
    show("不带任何凭证 -> %s" % p, p)

print()
print("校准完成。")
