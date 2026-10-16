# -*- coding: utf-8 -*-
"""给禅道 Bug #4 追加 Fiddler 真实页面改包证据（先读原 steps，再追加后 PUT，最后回读校验）"""
import json
import sys
import urllib.request
import urllib.error
import base64

BASE = "http://127.0.0.1/zentao/api.php/v1"
OUTER_USER = "zentao"
OUTER_PASS = "123456"
ACCOUNT = "admin"
PASSWORD = "5408lyT@"
BUG_ID = "4"

# 追加内容（HTML；& 已转义为 &amp;）
APPEND = (
    '<p><strong>【补充证据 · 2026-09-21 · Fiddler 在真实页面请求上改包复现】</strong></p>'
    '<ol>'
    '<li>目的：排除"请求是测试人员自己拼的"这一争议。以下操作全部发生在后台页面自身发出的请求上，全程只改动一个数字。</li>'
    '<li>前置：浏览器打开 http://localhost:9527 ，用 admin123 登录 → 商品管理 → 商品列表，页面正常显示 20 行。</li>'
    '<li>Fiddler Classic 已开启抓包（系统代理指向 127.0.0.1:8888），可正常捕获 localhost:9527 流量。</li>'
    '<li>左下 QuickExec 命令行输入 <code>bpu /admin/goods/list</code> 回车 → 仅对该接口下请求断点。</li>'
    '<li>回到页面点「查询」→ 请求被拦下（会话列表出现红色暂停标记、页面转圈，属预期现象不是卡死）。</li>'
    '<li>双击该会话 → 右侧 Inspectors → 上半部分 Request → Headers 视图第一行为：<br/>'
    'GET http://localhost:9527/admin/goods/list?page=1&amp;limit=20&amp;sort=add_time&amp;order=desc HTTP/1.1<br/>'
    '仅将 <strong>limit=20 改为 limit=0</strong>，其余字符一字未动。</li>'
    '<li>放行（点 Run to Completion，或在 QuickExec 输入 g 回车）。</li>'
    '<li>实际结果：该会话 Result=200；左侧 Body 列显示 241,737 字节（gzip 压缩后的传输大小），'
    '点击横幅 "Response body is encoded. Click to decode." 解压后为约 1,514,715 字节；'
    '浏览器商品列表一页渲染约 250 行（正常为 20 行）。</li>'
    '<li>结论：与本单 Postman 直连后端 8080 的结果完全一致（1,514,715 字节 / 250 条），说明缺陷与调用方、与前端无关，'
    '根因是服务端未对 limit 做下限校验。<strong>"正常用户不会这么发"不成立</strong>：'
    '该请求由页面正常交互触发，仅在传输途中被改写了一个数字，任何人都可用同类工具在 3 分钟内完成。</li>'
    '<li>收尾：QuickExec 输入 <code>bpu</code> 回车清除断点。</li>'
    '<li>待补充附件：① Fiddler 会话列表截图（含 Result=200 / Body=241,737 两列）'
    '② 解压后 TextView 响应体截图 ③ 浏览器页面一页显示 250 行的截图。</li>'
    '</ol>'
)


def req(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    basic = base64.b64encode(f"{OUTER_USER}:{OUTER_PASS}".encode()).decode()
    r.add_header("Authorization", "Basic " + basic)
    if token:
        r.add_header("Token", token)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")


def main():
    st, tk = req("POST", "/tokens", {"account": ACCOUNT, "password": PASSWORD})
    if st != 201:
        print("TOKEN FAIL", st, tk)
        sys.exit(1)
    token = tk["token"]

    # 1. 读原始内容
    st, bug = req("GET", f"/bugs/{BUG_ID}", token=token)
    if st != 200:
        print("GET FAIL", st, bug)
        sys.exit(1)
    before = {
        "title": bug.get("title"), "severity": bug.get("severity"),
        "pri": bug.get("pri"), "type": bug.get("type"), "status": bug.get("status"),
        "os": bug.get("os"), "browser": bug.get("browser"), "module": bug.get("module"),
        "product": bug.get("product"), "project": bug.get("project"),
    }
    old_steps = bug.get("steps") or ""
    if "Fiddler 在真实页面请求上改包复现" in old_steps:
        print("已追加过，跳过，避免重复")
        return

    # 2. 追加并 PUT（只提交 steps 一个字段）
    new_steps = old_steps + APPEND
    st, res = req("PUT", f"/bugs/{BUG_ID}", {"steps": new_steps}, token=token)
    print("PUT", st, json.dumps(res, ensure_ascii=False)[:300])

    # 3. 回读校验：确认追加成功，且其它字段没被服务端默认值覆盖
    st, bug2 = req("GET", f"/bugs/{BUG_ID}", token=token)
    print("REGET", st)
    after = {
        "title": bug2.get("title"), "severity": bug2.get("severity"),
        "pri": bug2.get("pri"), "type": bug2.get("type"), "status": bug2.get("status"),
        "os": bug2.get("os"), "browser": bug2.get("browser"), "module": bug2.get("module"),
        "product": bug2.get("product"), "project": bug2.get("project"),
    }
    print("追加成功:", "Fiddler 在真实页面请求上改包复现" in (bug2.get("steps") or ""))
    print("steps 长度:", len(old_steps), "->", len(bug2.get("steps") or ""))
    diff = {k: (before[k], after[k]) for k in before if before[k] != after[k]}
    print("字段漂移:", diff if diff else "无")


if __name__ == "__main__":
    main()
