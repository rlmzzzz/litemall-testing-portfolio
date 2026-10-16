# -*- coding: utf-8 -*-
"""
litemall 后台接口「凭证通道」探测脚本
------------------------------------------------
回答一个问题：/admin/dashboard 到底认什么凭证？
一次性跑完全部场景，输出可直接截屏放进测试记录。

用法：
    python probe_auth.py
前置：docker 里 litemall 容器已启动（8080 端口可用）
"""
import json
import sys
import urllib.request
import urllib.error
import http.cookiejar

sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8080"
HOST_ALT = "http://localhost:8080"
EP = "/admin/dashboard"


def new_jar():
    """返回 (cookiejar, opener)"""
    cj = http.cookiejar.CookieJar()
    return cj, urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def login(opener, host=BASE, user="mall123"):
    req = urllib.request.Request(
        host + "/admin/auth/login",
        data=json.dumps({"username": user, "password": user}).encode(),
        headers={"Content-Type": "application/json"})
    return json.loads(opener.open(req, timeout=10).read())["data"]["token"]


def probe(tag, url=None, headers=None, opener=None):
    url = url or (BASE + EP)
    req = urllib.request.Request(url, headers=headers or {})
    op = opener or urllib.request.build_opener()
    try:
        r = op.open(req, timeout=15)
        d = json.loads(r.read())
        print("  %-44s errno=%-4s %s" % (tag, d.get("errno"), str(d.get("data"))[:46]))
    except urllib.error.HTTPError as e:
        print("  %-44s HTTP=%s %s" % (tag, e.code, e.read().decode("utf-8", "replace")[:46]))
    except Exception as e:
        print("  %-44s 异常 %s" % (tag, e))


def main():
    print("=" * 78)
    print("实验 0：token 和 JSESSIONID 是不是同一个东西")
    print("=" * 78)
    cj0, op0 = new_jar()
    tok0 = login(op0)
    cookie0 = [c.value for c in cj0][0] if len(cj0) else None
    print("  响应体里的 token      : %s" % tok0)
    print("  Cookie 里的 JSESSIONID: %s" % cookie0)
    print("  两者是否一模一样      : %s" % (tok0 == cookie0))
    print("  → 说明：token 不是另造的一把钥匙，它就是 sessionId，只是换了个投递口")

    print()
    print("=" * 78)
    print("实验 1：不带任何 cookie，只改凭证的「放法 / 名字」")
    print("=" * 78)
    tok = login(urllib.request.build_opener())
    probe("什么都不带（基线）")
    probe("?token=<有效值>（放 Query Params）", BASE + EP + "?token=" + tok)
    probe("?token=乱码（放 Query Params）", BASE + EP + "?token=abc123-broken")
    probe("Header「Token: 有效值」（改名）", headers={"Token": tok})
    probe("Header「Authorization: Bearer 有效值」", headers={"Authorization": "Bearer " + tok})
    probe("Header「x-litemall-admin-token: 有效值」（全小写）", headers={"x-litemall-admin-token": tok})
    probe("Header「X-Litemall-Admin-Token: 有效值」（正解）", headers={"X-Litemall-Admin-Token": tok})

    print()
    print("=" * 78)
    print("实验 2：只要带了 cookie，header 怎么写都不影响结果（危险！）")
    print("=" * 78)
    cj1, op1 = new_jar()
    login(op1)
    print("  已在 127.0.0.1 登录，cookie = %s" % [c.value[:18] for c in cj1])
    probe("只用 cookie，不带任何 header", opener=op1)
    probe("cookie + ?token=乱码", BASE + EP + "?token=abc123-broken", opener=op1)
    probe("cookie + Header 改名「Token: 乱码」", headers={"Token": "garbage"}, opener=op1)

    print()
    print("=" * 78)
    print("实验 3：header 与 cookie 的优先级，以及乱码 header 的副作用")
    print("=" * 78)
    cj2, op2 = new_jar()
    tok2 = login(op2)
    print("  登录后 cookie = %s" % [c.value[:18] for c in cj2])
    probe("① 只用 cookie", opener=op2)
    probe("② cookie + 乱码 header", headers={"X-Litemall-Admin-Token": "garbage"}, opener=op2)
    print("  ② 之后 cookie = %s  ← 被服务端换发了新的" % [c.value[:18] for c in cj2])
    probe("③ 继续用这个新 cookie", opener=op2)
    probe("④ cookie + 空 header", headers={"X-Litemall-Admin-Token": ""}, opener=op2)

    print()
    print("=" * 78)
    print("实验 4：cookie 是按域名隔离的")
    print("=" * 78)
    cj3, op3 = new_jar()
    login(op3, host=HOST_ALT)
    print("  在 localhost 登录，cookie = %s" % [c.value[:18] for c in cj3])
    probe("拿 localhost 的 cookie 去请求 127.0.0.1",
          url="http://127.0.0.1:8080" + EP, opener=op3)
    probe("拿 localhost 的 cookie 请求 localhost",
          url="http://localhost:8080" + EP, opener=op3)

    print()
    print("=" * 78)
    print("无凭证时服务端原话")
    print("=" * 78)
    r = urllib.request.urlopen(urllib.request.Request(BASE + EP), timeout=15)
    print("  " + r.read().decode("utf-8"))


if __name__ == "__main__":
    main()
