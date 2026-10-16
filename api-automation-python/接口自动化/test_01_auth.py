# -*- coding: utf-8 -*-
"""
第一组用例：登录接口（对应你 Postman 里的认证模块）

pytest 的三条铁律，看懂这个文件的写法就够用了：

  1. 文件必须叫 test_*.py      —— 否则 pytest 找不到它
  2. 函数必须叫 def test_xxx() —— 否则 pytest 不把它当用例
  3. 判断对错用 Python 自带的 assert，不要 if + print
       assert 条件, "失败时想说的提示语"
       条件成立 → 这条用例绿（passed）
       条件不成立 → 这条用例红（failed）

再强调一次第 3 条的区别 —— 这是自动化测试的灵魂：
  if + print  ：脚本永远执行完，永远是"跑完了"，但你得肉眼看输出才知道对不对
  assert      ：判断交给机器，**不对就直接标红**，一眼看到结论
"""

import pytest

from conftest import ADMIN_PASS, ADMIN_USER, login


def test_正确账号密码_登录成功并返回token():
    """正向用例：登录成功，errno=0，且拿到非空的 token。"""
    body = login(ADMIN_USER, ADMIN_PASS)

    assert body["errno"] == 0, f"期望 errno=0（成功），实际 {body['errno']}：{body['errmsg']}"
    assert body["data"]["token"], "errno=0 但 token 是空的，这本身也是缺陷"


def test_密码错误_登录失败():
    """反向用例：密码不对，应当拒绝，且不下发 token。"""
    body = login(ADMIN_USER, "wrong-password")

    assert body["errno"] != 0, "密码错误却登录成功了 —— 这是致命缺陷"

    # ★ 这里我第一版写错过：直接写 body["data"].get("token")，结果红了，
    #   报 AttributeError: 'str' object has no attribute 'get'。
    #   原因是：登录失败时 data 不是字典，而是字符串（多半是空串或提示语）。
    #   教训：**不能假设响应结构一定长什么样，取值前先看类型。**
    #   这也是"红了先分清是脚本错还是系统错" —— 这次是脚本错。
    data = body.get("data")
    data_dict = data if isinstance(data, dict) else {}

    assert not data_dict.get("token"), \
        f"密码错误时不该下发 token，实际拿到了：{data_dict.get('token')}"


def test_账号不存在_登录失败():
    """反向用例：账号不存在应与密码错误表现一致（避免暴露账号是否存在）。"""
    body = login("no-such-user-xyz", ADMIN_PASS)

    assert body["errno"] != 0, "不存在的账号竟然登录成功了"


# ---------------------------------------------------------------------------
# 参数化：同一条用例逻辑，换不同的测试数据跑多次
#
# 上面三条写成了一条条函数，其实 test_密码错误 和 test_账号不存在 逻辑完全一样，
# 只是数据不同。pytest 的写法是 @pytest.mark.parametrize：
#   第一个参数是"参数名字符串"，第二个参数是"数据列表（可含 tuples）"
# 好处：加一组新数据只要在列表里加一行，不用复制整个函数。
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "username, password, 场景描述",
    [
        ("admin123",   "admin123",   "正确账号密码"),
        ("admin123",   "wrong123",   "密码错误"),
        ("nobody-xyz", "admin123",   "账号不存在"),
        ("",           "admin123",   "用户名为空"),
        ("admin123",   "",           "密码为空"),
    ],
)
def test_登录_多组账号密码(username, password, 场景描述):
    """用参数化一次性覆盖 5 组数据 —— 这就是"数据驱动"。"""
    body = login(username, password)

    if 场景描述 == "正确账号密码":
        assert body["errno"] == 0, f"[{场景描述}] 应当登录成功，实际 {body}"
    else:
        assert body["errno"] != 0, f"[{场景描述}] 应当被拒绝，实际 errno={body['errno']}：{body['errmsg']}"
