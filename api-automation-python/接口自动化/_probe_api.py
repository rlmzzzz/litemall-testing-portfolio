# -*- coding: utf-8 -*-
"""临时探测：确认几个业务的真实返回，用来写准确的断言期望值。"""
import os
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
import json
import requests

BASE = "http://127.0.0.1:8080"

def show(title, r):
    try:
        b = r.json()
    except Exception:
        print(f"{title} -> HTTP {r.status_code} 非 JSON: {r.text[:200]}")
        return
    print(f"{title} -> HTTP {r.status_code}")
    print("   errno =", b.get("errno"))
    print("   errmsg=", b.get("errmsg"))
    d = b.get("data")
    if isinstance(d, dict):
        print("   data keys =", list(d.keys()))
        if "list" in d:
            print("   list len =", len(d["list"]), " total =", d.get("total"))
    elif isinstance(d, list):
        print("   data is list, len =", len(d))
    print()

# 1 正常登录
r = requests.post(f"{BASE}/admin/auth/login", json={"username": "admin123", "password": "admin123"}, timeout=10)
show("[正确密码]", r)
token = r.json()["data"]["token"]

# 2 错误密码
r = requests.post(f"{BASE}/admin/auth/login", json={"username": "admin123", "password": "wrongpwd"}, timeout=10)
show("[错误密码]", r)

# 3 不存在的账号
r = requests.post(f"{BASE}/admin/auth/login", json={"username": "nosuchuser", "password": "admin123"}, timeout=10)
show("[不存在账号]", r)

# 4 不带 token 查商品列表
r = requests.get(f"{BASE}/admin/goods/list", params={"page": 1, "limit": 20}, timeout=10)
show("[无token查列表]", r)

# 5 带假 token
r = requests.get(f"{BASE}/admin/goods/list", params={"page": 1, "limit": 20},
                 headers={"X-Litemall-Admin-Token": "fake-token-123"}, timeout=10)
show("[假token查列表]", r)

# 6 正常 limit=20
r = requests.get(f"{BASE}/admin/goods/list", params={"page": 1, "limit": 20},
                 headers={"X-Litemall-Admin-Token": token}, timeout=10)
show("[token + limit=20]", r)

# 7 limit=0（Bug-8）
r = requests.get(f"{BASE}/admin/goods/list", params={"page": 1, "limit": 0},
                 headers={"X-Litemall-Admin-Token": token}, timeout=10)
show("[token + limit=0]", r)

# 8 limit=-1
r = requests.get(f"{BASE}/admin/goods/list", params={"page": 1, "limit": -1},
                 headers={"X-Litemall-Admin-Token": token}, timeout=10)
show("[token + limit=-1]", r)

# 9 page=0
r = requests.get(f"{BASE}/admin/goods/list", params={"page": 0, "limit": 20},
                 headers={"X-Litemall-Admin-Token": token}, timeout=10)
show("[token + page=0]", r)

# 10 响应时间基准
r = requests.get(f"{BASE}/admin/goods/list", params={"page": 1, "limit": 20},
                 headers={"X-Litemall-Admin-Token": token}, timeout=10)
print("[耗时]", r.elapsed.total_seconds(), "秒")
