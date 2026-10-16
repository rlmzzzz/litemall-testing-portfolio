# -*- coding: utf-8 -*-
"""
第二组用例：商品列表接口（对应你 Fiddler 改包测过的那个接口）

这一组里有一条**故意会变红的用例** —— 它不是脚本写错了，
而是测出系统有缺陷。红 = 自动化在最替你盯着 Bug。

另外注意下面 token 这个参数的来历：它没在本文件里定义，
是 conftest.py 里的 fixture，pytest 看到参数名叫 token 就自动注入进来。
"""

import pytest

from conftest import get_goods_list


def test_已登录_默认分页返回20条(token):
    """正向用例：limit=20 时应该正好返回 20 条（对照组）。"""
    body = get_goods_list(token, page=1, limit=20)

    assert body["errno"] == 0, f"查询失败：{body}"
    assert len(body["data"]["list"]) == 20, \
        f"期望返回 20 条，实际 {len(body['data']['list'])} 条"
    assert body["data"]["total"] == 250, \
        f"商品总数不对：期望 250，实际 {body['data']['total']}"


def test_未登录_应拒绝访问():
    """安全用例：不带 token 必须拒绝。"""
    body = get_goods_list(token=None, page=1, limit=20)

    assert body["errno"] == 501, \
        f"未登录却拿到了数据 —— 严重越权缺陷。实际 errno={body['errno']}：{body['errmsg']}"


def test_伪造token_应拒绝访问():
    """安全用例：token 是假的也必须拒绝（防止猜 token 蒙混过关）。"""
    body = get_goods_list(token="fake-token-abc", page=1, limit=20)

    assert body["errno"] == 501, \
        f"假 token 竟然通过了，实际 errno={body['errno']}：{body['errmsg']}"


# ===========================================================================
# ↓↓↓ 下面两条是"故意变红"的：它们测的就是系统真实存在的缺陷 ↓↓↓
# ===========================================================================

def test_limit为0_应被拒绝或返回空列表(token):
    """
    这条对应你在 Fiddler 里发现、已提到禅道 #4 的缺陷（Bug-8）。

    预期：limit=0 是非法参数，服务端应当
        ① 返回错误码，或
        ② 按默认值返回 20 条
    实际：返回了全部 250 条 → 所以这条会变红。

    "红了"不是失败，是自动化**替你把 Bug 复现出来了**。
    """
    body = get_goods_list(token, page=1, limit=0)

    count = len(body["data"]["list"])
    assert count <= 20, (
        f"limit=0 应被拒绝或返回默认条数，实际返回 {count} 条（全量）\n"
        f"        → 这就是禅道 #4：分页参数缺少下限校验，"
        f"一次请求可拖走全站数据（响应体约 1.5MB）"
    )


def test_limit为负数_应被拒绝(token):
    """
    探测新发现：limit=-1 时服务端返回 0 条，不报错也不纠正。

    这条比上一条更隐蔽 —— 没崩、没返回巨量数据，看起来"很正常"，
    但它是**静默接受非法参数**：前端传了个负数过来，服务端照单执行。
    这类问题在有默认值兜底的框架里容易被忽略，却是典型的入参校验缺失。
    """
    body = get_goods_list(token, page=1, limit=-1)

    assert body["errno"] != 0, (
        f"limit=-1 是非法参数，服务端却返回了 errno=0（成功），"
        f"list 长度 = {len(body['data']['list'])}\n"
        f"        → 应返回参数校验错误（如 errno=402），而不是静默接受"
    )


@pytest.mark.parametrize("page", [0, -1, 99999])
def test_页码异常_不应报错(token, page):
    """边界值：页码异常时，服务端应优雅处理（返回成功但列表为空或按页返回），不能 500。"""
    body = get_goods_list(token, page=page, limit=20)

    assert body["errno"] == 0, \
        f"page={page} 时服务端报错了：errno={body['errno']} {body['errmsg']}"
    assert isinstance(body["data"]["list"], list), "list 字段缺失或类型不对"
