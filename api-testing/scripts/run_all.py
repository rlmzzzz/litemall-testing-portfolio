# -*- coding: utf-8 -*-
"""
litemall 接口测试一键执行脚本
用法：python run_all.py
前置：Docker 三个容器已启动（litemall / mysql / litemall-admin-web）
"""
import os, sys, glob, subprocess, datetime

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
NODE_WORKSPACE = r"C:\Users\李玉亭\.workbuddy\binaries\node\workspace\node_modules"
REPORT_DIR = os.path.join(HERE, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

env = dict(os.environ)
env["NODE_PATH"] = NODE_WORKSPACE

collections = sorted(glob.glob(os.path.join(HERE, "*.postman_collection.json")))
if not collections:
    print("未找到任何 .postman_collection.json"); sys.exit(1)

print("=" * 72)
print(f" litemall 接口测试  |  {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
print(f" 共 {len(collections)} 个集合")
print("=" * 72)

total = {"req": 0, "assert": 0, "fail": 0}
failed_list = []

for c in collections:
    name = os.path.basename(c).replace(".postman_collection.json", "")
    html = os.path.join(REPORT_DIR, f"{name}报告.html")
    jsonout = os.path.join(REPORT_DIR, f"{name}.json")
    print(f"\n▶ 运行：{name}")
    cmd = [
        "newman.cmd", "run", c,
        "-e", os.path.join(HERE, "litemall.postman_environment.json"),
        "-r", "cli,json,htmlextra",
        "--reporter-json-export", jsonout,
        "--reporter-htmlextra-export", html,
        "--reporter-htmlextra-title", f"litemall 接口测试 - {name}",
        "--reporter-htmlextra-darkTheme",
    ]
    subprocess.run(" ".join(f'"{x}"' for x in cmd), env=env, cwd=HERE, shell=True)

    if os.path.exists(jsonout):
        import json
        with open(jsonout, encoding="utf-8") as f:
            d = json.load(f)
        stats = d["run"]["stats"]
        r = stats["requests"]["total"]; a = stats["assertions"]["total"]; fl = stats["assertions"]["failed"]
        total["req"] += r; total["assert"] += a; total["fail"] += fl
        print(f"   请求 {r}  断言 {a}  失败 {fl}")
        for e in d["run"]["executions"]:
            for asr in e.get("assertions", []):
                if asr.get("error"):
                    failed_list.append((name, e["item"]["name"], asr["assertion"],
                                        asr["error"].get("message", "")[:100]))

print()
print("=" * 72)
print(f" 汇总：请求 {total['req']}  断言 {total['assert']}  失败 {total['fail']}")
print("=" * 72)
if failed_list:
    print("\n失败断言明细（这些是「按需求预期应正确、实际未实现」的缺陷证据）：")
    for n, item, asr, msg in failed_list:
        print(f"  [{n}] {item}")
        print(f"      {asr}")
        print(f"      实际：{msg}")
print(f"\nHTML 报告目录：{REPORT_DIR}")
