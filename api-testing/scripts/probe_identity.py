# -*- coding: utf-8 -*-
"""
Bug-7 取证脚本：证明「访问 /admin/dashboard 的身份确实是 mall123」
全程不带任何 cookie，只靠 X-Litemall-Admin-Token header。
"""
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')
BASE = "http://127.0.0.1:8080"


def call(path, token=None):
    headers = {"X-Litemall-Admin-Token": token} if token else {}
    req = urllib.request.Request(BASE + path, headers=headers)
    r = urllib.request.urlopen(req, timeout=15)   # 注意：无 CookieProcessor，绝不带 cookie
    return json.loads(r.read())


def login(user):
    req = urllib.request.Request(BASE + "/admin/auth/login",
                                data=json.dumps({"username": user, "password": user}).encode(),
                                headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())["data"]["token"]


for user in ["admin123", "mall123"]:
    tok = login(user)
    info = call("/admin/auth/info", tok)["data"]
    dash = call("/admin/dashboard", tok)
    roles = info.get("roles") or []
    perms = info.get("perms") or []
    print("=" * 74)
    print("账号：%s" % user)
    print("  token          : %s" % tok)
    print("  /admin/auth/info 证明「我是谁」 → nickName = %s" % info.get("name") or info.get("nickName"))
    print("  角色 roles     : %s" % roles)
    print("  权限 perms 数量 : %d" % len(perms))
    print("  权限 perms 明细 : %s" % ("、".join(perms) if perms else "（空）"))
    print("  /admin/dashboard → errno=%s  data=%s" % (dash.get("errno"), dash.get("data")))

print()
print("=" * 74)
print("对照：mall123 在「有权限」和「无权限」接口上的表现")
for path in ["/admin/brand/list?page=1&limit=1", "/admin/category/list?page=1&limit=1",
             "/admin/goods/list?page=1&limit=1", "/admin/order/list?page=1&limit=1",
             "/admin/dashboard"]:
    d = call(path, login("mall123"))
    print("  %-42s errno=%-5s errmsg=%s" % (path, d.get("errno"), d.get("errmsg")))
