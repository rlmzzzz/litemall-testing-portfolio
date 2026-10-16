# -*- coding: utf-8 -*-
"""
逐个实测「没有 @RequiresPermissions 注解」的 4 个 controller，
判断哪些是合理的、哪些是权限漏洞。
"""
import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding='utf-8')
BASE = "http://127.0.0.1:8080"


def login(user="mall123"):
    req = urllib.request.Request(BASE + "/admin/auth/login",
                                data=json.dumps({"username": user, "password": user}).encode(),
                                headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())["data"]["token"]


def probe(path, token=None, tag=None):
    headers = {"X-Litemall-Admin-Token": token} if token else {}
    req = urllib.request.Request(BASE + path, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=15)
        raw = r.read()
        d = json.loads(raw)
        data = d.get("data")
        shown = str(data)[:52] if not isinstance(data, list) else "[数组 长度=%d] %s" % (
            len(data), str(data[:1])[:40])
        print("  %-46s errno=%-5s %-8s %s" % (tag or path, d.get("errno"), "%dB" % len(raw), shown))
    except urllib.error.HTTPError as e:
        print("  %-46s HTTP=%s %s" % (tag or path, e.code, e.read().decode("utf-8", "replace")[:40]))
    except Exception as e:
        print("  %-46s 异常 %s" % (tag or path, e))


tok = login()
CASES = [
    ("/admin/dashboard?a=1", "AdminDashbordController /admin/dashboard"),
    ("/admin/region/list", "AdminRegionController  /admin/region/list"),
    ("/admin/region/clist?id=1", "AdminRegionController  /admin/region/clist?id=1"),
    ("/admin/profile/nnotice?limit=3", "AdminProfileController /nnotice"),
    ("/admin/auth/index", "AdminAuthController     /admin/auth/index"),
    ("/admin/auth/info", "AdminAuthController     /admin/auth/info"),
]
print("【不带任何凭证】")
for p, tag in CASES:
    probe(p, None, tag)
print()
print("【带 mall123 的有效 token（无 cookie）】")
for p, tag in CASES:
    probe(p, tok, tag)
