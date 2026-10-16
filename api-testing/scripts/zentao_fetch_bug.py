# -*- coding: utf-8 -*-
"""读取禅道指定 Bug 单的当前内容（只 GET，不改任何数据）"""
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
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")


def main():
    st, tk = req("POST", "/tokens", {"account": ACCOUNT, "password": PASSWORD})
    if st != 201:
        print("TOKEN FAIL", st, tk)
        sys.exit(1)
    token = tk["token"]
    bug_id = sys.argv[1] if len(sys.argv) > 1 else "4"
    st, bug = req("GET", f"/bugs/{bug_id}", token=token)
    print("HTTP", st)
    if st != 200:
        print(bug)
        sys.exit(1)
    for k in ("id", "title", "severity", "pri", "type", "status", "os", "browser",
              "openedBuild", "module", "product", "project", "keywords"):
        print(f"{k:12} = {bug.get(k)}")
    print("-" * 60)
    print("STEPS:\n", bug.get("steps") or "(空)")
    print("-" * 60)
    print("FILES:", json.dumps(bug.get("files"), ensure_ascii=False)[:500])


if __name__ == "__main__":
    main()
