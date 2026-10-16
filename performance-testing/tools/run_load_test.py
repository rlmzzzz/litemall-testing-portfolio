#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JMeter 梯度压测一键脚本
用法：
    python run_load_test.py                # 默认梯度 10/30/50/100
    python run_load_test.py --levels 10,50  # 只跑指定并发
    python run_load_test.py --loops 20      # 每档循环次数

做三件事：
 1. 按梯度逐档无界面跑 JMeter，生成 .jtl 原始数据 + HTML 仪表盘报告
 2. 解析 .jtl 算出每档的 关键指标（TPS / 平均 / 90% / 最大 / 错误率）
 3. 输出 Markdown 汇总表 + 写一份 CSV，直接能贴进性能报告
"""
import argparse
import csv
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

JMETER = Path(r"C:\Users\李玉亭\WorkBuddy\2026-09-15-16-30-32\litemall-测试实战\工具\apache-jmeter-5.6.3\bin\jmeter.bat")
BASE = Path(r"C:\Users\李玉亭\WorkBuddy\2026-09-15-16-30-32\litemall-测试实战\性能测试")
JMX = BASE / "scripts" / "litemall-admin-core.jmx"
STEADY_JMX = BASE / "scripts" / "litemall-admin-core-steady.jmx"
RESULTS = BASE / "results"
REPORTS = BASE / "reports"
JAVA_HOME = r"D:\jdk-11"


def run_one(threads, ramp, loops, steady=False, duration=45, tag_prefix="load"):
    """跑一档并发，返回 jtl 路径"""
    tag = f"{tag_prefix}_{threads}"
    jtl = RESULTS / f"{tag}.jtl"
    log = RESULTS / f"{tag}.log"
    out_dir = REPORTS / tag
    for p in (jtl, log):
        if p.exists():
            p.unlink()
    # ★ -e -o 的目录必须为空或不存在，否则 JMeter 会【秒退且退出码仍为 0】（实测踩到）
    #   注意：单纯 rmtree 可能静默失败（目录被占用/有残留子目录），所以删完还要复查，
    #   复查失败就换一个唯一目录名，彻底规避这一类失败。
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    if out_dir.exists():
        out_dir = REPORTS / f"{tag}_{int(time.time())}"
        print(f"  提示：原报告目录未能删除，改用 {out_dir.name}", flush=True)

    jmx = STEADY_JMX if steady else JMX
    cmd = [
        str(JMETER), "-n",
        "-t", str(jmx),
        "-l", str(jtl),
        "-j", str(log),
        f"-Jthreads={threads}",
        f"-Jramp={ramp}",
    ]
    if steady:
        cmd.append(f"-Jduration={duration}")
    else:
        cmd.append(f"-Jloops={loops}")
    cmd += ["-e", "-o", str(out_dir)]
    env = dict(os.environ)
    env["JAVA_HOME"] = JAVA_HOME
    env["JVM_ARGS"] = "-Xms256m -Xmx768m"

    mode = f"稳态 {duration}s" if steady else f"循环 {loops} 次"
    print(f"\n===== 并发 {threads} | 爬坡 {ramp}s | {mode} =====", flush=True)
    r = subprocess.run(cmd, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("JMeter 退出码非 0：", r.returncode, flush=True)
        print((r.stderr or "")[-1500:], flush=True)
    # ★ 退出码 0 不代表成功：报告目录非空时 JMeter 会秒退且退出码仍为 0
    rows = 0
    if jtl.exists():
        with open(jtl, "r", encoding="utf-8", errors="replace") as f:
            rows = max(0, sum(1 for _ in f) - 1)
    if rows == 0:
        print("⚠️ 本次未产生任何采样（0 行），结果无效！", flush=True)
        print(f"   排查：看 {log.name} 里有没有 ERROR，常见原因是报告目录非空", flush=True)
    else:
        print(f"  采样行数：{rows}", flush=True)
    return jtl


def pct(values, p):
    """百分位数（最近秩法，与 JMeter 口径一致的近似）"""
    if not values:
        return 0.0
    s = sorted(values)
    k = max(1, int(round(p / 100.0 * len(s) + 0.5)) - 1)
    return float(s[min(k, len(s) - 1)])


def parse_jtl(jtl):
    """解析 jtl，按 label 汇总"""
    stats = {}
    if not jtl.exists():
        return stats
    with open(jtl, "r", encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            label = row.get("label", "?")
            try:
                elapsed = float(row.get("elapsed") or 0)
                ts = int(row.get("timeStamp") or 0)
                ok = str(row.get("success", "")).lower() == "true"
            except ValueError:
                continue
            d = stats.setdefault(label, {"n": 0, "err": 0, "times": [], "ts": []})
            d["n"] += 1
            if not ok:
                d["err"] += 1
            d["times"].append(elapsed)
            d["ts"].append(ts)
    out = {}
    for label, d in stats.items():
        span_ms = (max(d["ts"]) - min(d["ts"])) if len(d["ts"]) > 1 else 1
        span_s = max(span_ms / 1000.0, 0.001)
        out[label] = {
            "样本数": d["n"],
            "失败数": d["err"],
            "错误率%": round(d["err"] * 100.0 / d["n"], 2) if d["n"] else 0,
            "TPS": round(d["n"] / span_s, 1),
            "平均ms": round(statistics.mean(d["times"]), 1),
            "中位ms": round(statistics.median(d["times"]), 1),
            "90%ms": round(pct(d["times"], 90), 0),
            "最大ms": round(max(d["times"]), 0),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", default="10,30,50,100", help="并发梯度，逗号分隔")
    ap.add_argument("--loops", type=int, default=10, help="每档循环次数（非稳态模式）")
    ap.add_argument("--steady", action="store_true",
                    help="稳态压测模式：固定时长持续加压，TPS 才可信")
    ap.add_argument("--duration", type=int, default=45, help="稳态模式每档持续秒数")
    ap.add_argument("--ramp", type=int, default=None, help="爬坡秒数（默认低于30并发用5s，否则10s）")
    args = ap.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    levels = [int(x) for x in args.levels.split(",") if x.strip()]

    all_rows = []
    for n in levels:
        ramp = args.ramp if args.ramp is not None else (5 if n <= 30 else 10)
        jtl = run_one(n, ramp, args.loops,
                      steady=args.steady, duration=args.duration,
                      tag_prefix="steady" if args.steady else "load")
        st = parse_jtl(jtl)
        for label, m in st.items():
            row = {"并发": n, "接口": label}
            row.update(m)
            all_rows.append(row)
        print(f"  完成：{len(st)} 个采样标签", flush=True)

    # CSV
    csv_name = "稳态压测汇总.csv" if args.steady else "梯度压测汇总.csv"
    csv_path = RESULTS / csv_name
    if all_rows:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)

    # Markdown 汇总
    title = "稳态压测汇总（固定时长，TPS 可信）" if args.steady else "梯度压测汇总（循环模式，TPS 受爬坡稀释）"
    keys = ["并发", "接口", "样本数", "失败数", "错误率%", "TPS", "平均ms", "90%ms", "最大ms"]
    print(f"\n\n## {title}\n")
    print("| " + " | ".join(keys) + " |")
    print("|" + "---|" * len(keys))
    for r in all_rows:
        print("| " + " | ".join(str(r.get(k, "")) for k in keys) + " |")
    print(f"\nCSV 已写出：{csv_path}")


if __name__ == "__main__":
    main()
