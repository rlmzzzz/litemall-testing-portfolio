#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
jtl 压测结果对比工具（A/B 对比）
用法：
    python jtl_compare.py A.jtl B.jtl --labels "A组,B组"
输出：按接口逐行对比 样本数 / TPS / 平均 / 90% / 最大 / 平均响应字节
"""
import argparse
import csv
import statistics
from pathlib import Path


def load(jtl):
    rows = []
    with open(jtl, "r", encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            try:
                rows.append({
                    "label": r.get("label", "?"),
                    "elapsed": float(r.get("elapsed") or 0),
                    "bytes": float(r.get("bytes") or 0),
                    "ts": int(r.get("timeStamp") or 0),
                    "ok": str(r.get("success", "")).lower() == "true",
                })
            except ValueError:
                continue
    return rows


def pct(vals, p):
    if not vals:
        return 0
    s = sorted(vals)
    k = max(1, int(round(p / 100.0 * len(s) + 0.5)) - 1)
    return s[min(k, len(s) - 1)]


def summarize(rows):
    out = {}
    for r in rows:
        d = out.setdefault(r["label"], {"n": 0, "err": 0, "t": [], "b": [], "ts": []})
        d["n"] += 1
        if not r["ok"]:
            d["err"] += 1
        d["t"].append(r["elapsed"])
        d["b"].append(r["bytes"])
        d["ts"].append(r["ts"])
    res = {}
    for label, d in out.items():
        span = max((max(d["ts"]) - min(d["ts"])) / 1000.0, 0.001)
        res[label] = {
            "样本": d["n"],
            "错误": d["err"],
            "TPS": round(d["n"] / span, 1),
            "平均ms": round(statistics.mean(d["t"]), 1),
            "90%ms": round(pct(d["t"], 90), 0),
            "最大ms": round(max(d["t"]), 0),
            "平均KB": round(statistics.mean(d["b"]) / 1024.0, 1),
        }
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--labels", default="A组,B组")
    args = ap.parse_args()

    la, lb = [s.strip() for s in args.labels.split(",")][:2]
    sa, sb = summarize(load(args.a)), summarize(load(args.b))

    labels = [k for k in sa if k in sb] or list(sa)
    keys = ["样本", "错误", "TPS", "平均ms", "90%ms", "最大ms", "平均KB"]

    for label in labels:
        print(f"\n### {label}\n")
        print(f"| 指标 | {la} | {lb} | 变化 |")
        print("|---|---|---|---|")
        for k in keys:
            va, vb = sa[label].get(k, 0), sb[label].get(k, 0)
            if k in ("样本", "错误"):
                delta = f"{vb - va:+}"
            else:
                delta = f"{(vb - va) / va * 100:+.1f}%" if va else "n/a"
            print(f"| {k} | {va} | {vb} | {delta} |")


if __name__ == "__main__":
    main()
