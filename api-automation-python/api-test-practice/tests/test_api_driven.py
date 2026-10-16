"""
数据驱动接口自动化测试。
核心思想：测试逻辑只写一次，用例数据放在 cases.json 里。
加用例 = 往 JSON 里加一行，不用改代码。这就是"数据驱动"。
"""
import json
import os

import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8099")


def load_cases():
    path = os.path.join(os.path.dirname(__file__), "data", "cases.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


CASES = load_cases()


def _get_field(body, field):
    """支持 data.id 这种嵌套取值。"""
    actual = body
    for part in field.split("."):
        if not isinstance(actual, dict):
            return None
        actual = actual.get(part)
    return actual


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_api(case):
    method = case["method"]
    url = BASE_URL + case["path"]

    headers = {}
    if case.get("token"):
        headers["Authorization"] = "Bearer " + case["token"]

    kwargs = {"headers": headers, "timeout": 10}
    if case.get("body") is not None:
        kwargs["json"] = case["body"]

    resp = requests.request(method, url, **kwargs)

    # 1) 状态码断言
    assert resp.status_code == case["expected_status"], (
        f"状态码期望 {case['expected_status']}，实际 {resp.status_code}，"
        f"响应体: {resp.text[:200]}"
    )

    # 2) 字段断言（可选，支持 data.id 嵌套）
    field = case.get("expect_field")
    if field:
        body = resp.json()
        actual = _get_field(body, field)
        assert actual is not None, f"期望响应包含字段 {field}，实际响应: {body}"

    # 3) 响应时间断言（可选）
    if "max_ms" in case:
        elapsed = resp.elapsed.total_seconds() * 1000
        assert elapsed <= case["max_ms"], (
            f"响应时间 {elapsed:.0f}ms 超过上限 {case['max_ms']}ms"
        )
