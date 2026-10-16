# -*- coding: utf-8 -*-
"""
litemall 后台 token 获取脚本

用途：一条命令拿到任意账号的 token，省去在 Postman 里手动登录 + 复制粘贴。
      后台 token 有效期 6 小时，过期后重跑一次即可。

用法：
    python get_token.py                        # 默认取 mall123
    python get_token.py admin123 admin123      # 指定账号密码
    python get_token.py --all                  # 三个测试账号全取一遍
    python get_token.py --all --check          # 取完顺手做越权验证

注意：脚本用 127.0.0.1 而不是 localhost。
      因为 localhost 上残留的 JSESSIONID cookie 会替请求开门，让测试结果不可信。
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8080"

# 三个测试账号，密码与用户名相同
ACCOUNTS = {
    "admin123": "admin123",        # 超级管理员，全部权限
    "mall123": "mall123",          # 只有品牌 + 分类权限
    "promotion123": "promotion123",  # 只有营销权限
}


def login(username, password):
    """调用登录接口，返回 (token, nickName)；失败返回 (None, 错误信息)"""
    payload = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/admin/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return None, "HTTP %s" % e.code
    except Exception as e:
        return None, "请求异常：%s（容器起来了吗？docker ps 看一下）" % e

    if body.get("errno") != 0:
        return None, "errno=%s %s" % (body.get("errno"), body.get("errmsg"))

    data = body.get("data") or {}
    return data.get("token"), (data.get("adminInfo") or {}).get("nickName")


def call_with_token(token, path):
    """带上 token 调一个后台接口，返回 (errno, errmsg, 原始响应字节数)"""
    req = urllib.request.Request(
        BASE + path, headers={"X-Litemall-Admin-Token": token}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        return e.code, "HTTP 错误", 0

    body = json.loads(raw.decode("utf-8"))
    return body.get("errno"), body.get("errmsg"), len(raw)


def main():
    parser = argparse.ArgumentParser(description="获取 litemall 后台账号 token")
    parser.add_argument("username", nargs="?", default="mall123", help="账号，默认 mall123")
    parser.add_argument("password", nargs="?", help="密码，默认与账号相同")
    parser.add_argument("--all", action="store_true", help="三个测试账号全取一遍")
    parser.add_argument("--check", action="store_true", help="取完顺手验证统计面板权限")
    args = parser.parse_args()

    targets = list(ACCOUNTS.items()) if args.all else [(args.username, args.password or args.username)]

    print("=" * 62)
    print("  litemall 后台 token 获取")
    print("=" * 62)

    tokens = {}
    for user, pwd in targets:
        token, info = login(user, pwd)
        if token:
            tokens[user] = token
            print("  [OK]   %-14s nickName=%-14s" % (user, info))
            print("         token = %s" % token)
        else:
            print("  [失败] %-14s 原因：%s" % (user, info))

    if not tokens:
        print("\n  一个都没取到，先确认环境：docker ps 应看到 litemall / mysql 都是 Up")
        return 1

    if args.check:
        print()
        print("-" * 62)
        print("  越权验证：用各自的 token 访问 /admin/dashboard")
        print("-" * 62)
        print("  %-14s %-8s %-10s %s" % ("账号", "errno", "响应字节", "说明"))
        for user, token in tokens.items():
            errno, errmsg, size = call_with_token(token, "/admin/dashboard")
            if user == "admin123":
                note = "预期 errno=0（有权限）"
            elif errno == 0:
                note = "★ 异常：无权限账号竟然能访问全站数据（越权）"
            else:
                note = "预期 errno=506（无权限）"
            print("  %-14s %-8s %-10s %s" % (user, errno, size, note))
        print()
        print("  说明：统计面板按设计只应超级管理员可见（AdminDashbordController")
        print("        缺少 @RequiresPermissions 注解）。低权限账号返回 0 即为 Bug。")

    print()
    print("  提示：后台 token 有效期 6 小时，过期后重新跑本脚本即可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
