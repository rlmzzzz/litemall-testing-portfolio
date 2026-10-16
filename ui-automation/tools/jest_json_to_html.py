# -*- coding: utf-8 -*-
"""
把 selenium-side-runner 生成的 Jest JSON 结果，转成一份可直接展示的中文 HTML 报告。

用法：
    python jest_json_to_html.py <results-xxx.json> [输出.html]
    python jest_json_to_html.py --latest <reports目录> [输出.html]

为什么需要它：
    selenium-side-runner 的 --output-directory 只产出 JSON（官方没有 HTML 报告选项），
    JSON 没法直接放进作品集 / 给面试官看，所以自己转一层。
"""
import glob
import html
import json
import os
import sys
from datetime import datetime


def load_latest(reports_dir):
    files = sorted(glob.glob(os.path.join(reports_dir, "results-*.json")), key=os.path.getmtime)
    if not files:
        raise SystemExit(f"在 {reports_dir} 下没找到 results-*.json")
    return files[-1]


def fmt_ms(ms):
    if ms is None:
        return "-"
    if ms < 1000:
        return f"{ms} ms"
    return f"{ms / 1000:.2f} s"


def build_html(data, source_name):
    total = data.get("numTotalTests", 0)
    passed = data.get("numPassedTests", 0)
    failed = data.get("numFailedTests", 0)
    pending = data.get("numPendingTests", 0)
    rate = (passed / total * 100) if total else 0.0
    success = data.get("success", False)
    start = data.get("startTime")
    start_str = datetime.fromtimestamp(start / 1000).strftime("%Y-%m-%d %H:%M:%S") if start else "-"

    rows = []
    for tr in data.get("testResults", []):
        for ar in tr.get("assertionResults", []):
            status = ar.get("status")
            if status == "passed":
                badge, cls = "通过", "pass"
            elif status == "failed":
                badge, cls = "失败", "fail"
            else:
                badge, cls = "跳过", "skip"
            titles = ar.get("ancestorTitles", [])
            project = titles[0].replace("Running project ", "") if len(titles) > 0 else "-"
            suite = titles[1].replace("Running suite ", "") if len(titles) > 1 else "-"
            msgs = "\n".join(ar.get("failureMessages", []) or [])
            # 只取最关键的一行，避免堆栈刷屏
            key_line = ""
            for line in msgs.splitlines():
                if line.strip():
                    key_line = line.strip()
                    break
            detail = html.escape(msgs if len(msgs) < 800 else msgs[:800] + "\n... (已截断，完整内容见 JSON)")
            rows.append(f"""
      <tr class="{cls}">
        <td><span class="badge {cls}">{badge}</span></td>
        <td>{html.escape(ar.get('title', '-'))}</td>
        <td>{html.escape(suite)}</td>
        <td>{html.escape(project)}</td>
        <td class="num">{fmt_ms(ar.get('duration'))}</td>
        <td class="err">{html.escape(key_line) if key_line else '-'}<pre class="stack">{detail}</pre></td>
      </tr>""")

    verdict = "全部通过" if success else "存在失败用例"
    vcls = "pass" if success else "fail"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>litemall 自动化回归测试报告</title>
<style>
  body {{ font-family: "Microsoft YaHei", system-ui, sans-serif; background:#f5f6f8; color:#222; margin:0; padding:24px; }}
  h1 {{ font-size:22px; margin:0 0 4px; }}
  .sub {{ color:#666; font-size:13px; margin-bottom:20px; }}
  .cards {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:20px; }}
  .card {{ background:#fff; border:1px solid #e3e6ea; border-radius:8px; padding:14px 18px; min-width:120px; }}
  .card .k {{ font-size:12px; color:#777; }}
  .card .v {{ font-size:24px; font-weight:bold; margin-top:4px; }}
  .verdict {{ display:inline-block; padding:6px 14px; border-radius:6px; font-weight:bold; color:#fff; margin-bottom:16px; }}
  .verdict.pass {{ background:#2e7d32; }}
  .verdict.fail {{ background:#c62828; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid #e3e6ea; border-radius:8px; overflow:hidden; }}
  th {{ background:#eef1f5; text-align:left; font-size:13px; padding:10px 12px; color:#444; }}
  td {{ padding:10px 12px; font-size:13px; border-top:1px solid #eef0f3; vertical-align:top; }}
  td.num {{ text-align:right; white-space:nowrap; }}
  td.err {{ max-width:420px; word-break:break-word; color:#555; }}
  pre.stack {{ display:none; white-space:pre-wrap; font-size:11px; color:#8a2020; background:#fdf3f3; padding:8px; border-radius:4px; margin:6px 0 0; }}
  tr.fail td.err {{ cursor:pointer; }}
  .badge {{ padding:2px 8px; border-radius:4px; color:#fff; font-size:12px; }}
  .badge.pass {{ background:#2e7d32; }}
  .badge.fail {{ background:#c62828; }}
  .badge.skip {{ background:#9e9e9e; }}
  .foot {{ margin-top:18px; font-size:12px; color:#777; }}
  code {{ background:#eee; padding:1px 5px; border-radius:3px; }}
</style>
</head>
<body>
  <h1>litemall 自动化回归测试报告</h1>
  <div class="sub">数据源：<code>{html.escape(source_name)}</code>　｜　执行时间：{start_str}　｜　生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

  <div class="verdict {vcls}">结论：{verdict}</div>

  <div class="cards">
    <div class="card"><div class="k">用例总数</div><div class="v">{total}</div></div>
    <div class="card"><div class="k">通过</div><div class="v" style="color:#2e7d32">{passed}</div></div>
    <div class="card"><div class="k">失败</div><div class="v" style="color:#c62828">{failed}</div></div>
    <div class="card"><div class="k">跳过</div><div class="v">{pending}</div></div>
    <div class="card"><div class="k">通过率</div><div class="v">{rate:.1f}%</div></div>
  </div>

  <table>
    <thead><tr><th>结果</th><th>用例</th><th>套件</th><th>项目</th><th>耗时</th><th>失败原因（点击展开）</th></tr></thead>
    <tbody>{''.join(rows) if rows else '<tr><td colspan="6">没有用例明细</td></tr>'}</tbody>
  </table>

  <div class="foot">
    生成方式：<code>selenium-side-runner</code> 输出 JSON → 本脚本转换为 HTML。<br>
    失败截图目录：<code>reports/screenshots/</code>（需在运行时加 <code>--screenshot-failure-directory</code> 参数）。
  </div>

<script>
document.querySelectorAll('tr.fail td.err').forEach(function(td){{
  td.addEventListener('click', function(){{
    var pre = td.querySelector('pre.stack');
    if (pre) pre.style.display = (pre.style.display === 'block') ? 'none' : 'block';
  }});
}});
</script>
</body>
</html>"""


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    if args[0] == "--latest":
        reports_dir = args[1] if len(args) > 1 else "."
        src = load_latest(reports_dir)
        out = args[2] if len(args) > 2 else os.path.join(reports_dir, "回归测试报告.html")
    else:
        src = args[0]
        out = args[1] if len(args) > 1 else os.path.splitext(src)[0] + ".html"

    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    html_text = build_html(data, os.path.basename(src))
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_text)
    print(f"HTML 报告已生成：{out}")
    print(f"用例 {data.get('numTotalTests', 0)} 个，通过 {data.get('numPassedTests', 0)}，失败 {data.get('numFailedTests', 0)}，"
          f"结论：{'全部通过' if data.get('success') else '存在失败'}")


if __name__ == "__main__":
    main()
