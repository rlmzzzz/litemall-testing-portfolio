# -*- coding: utf-8 -*-
"""生成 AutoResponder 用的伪造响应文件（任务 1）。可重复运行，覆盖式生成。"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# 1. 服务端报错：errno=502
FILES = {
    "01-errno502-系统内部错误.json": {
        "errno": 502,
        "errmsg": "系统内部错误",
    },
    # 2. 对照组：合法空列表（用来确认"正常空数据"长什么样，避免把正常现象误判成 Bug）
    "02-errno0-空列表-对照组.json": {
        "errno": 0,
        "errmsg": "成功",
        "data": {"total": 0, "pages": 0, "page": 1, "limit": 20, "list": []},
    },
    # 3. total 类型错误（字符串）：看前端分页组件 / 表格是否崩
    "03-total类型错误-字符串.json": {
        "errno": 0,
        "errmsg": "成功",
        "data": {"total": "abc", "pages": 1, "page": 1, "limit": 20, "list": []},
    },
    # 4. 单条商品名 10000 字符：看表格布局是否被撑破
    "04-超长商品名-10000字符.json": {
        "errno": 0,
        "errmsg": "成功",
        "data": {
            "total": 1,
            "pages": 1,
            "page": 1,
            "limit": 20,
            "list": [
                {
                    "id": 1,
                    "goodsSn": "FAKE-001",
                    "name": "超长" * 5000,
                    "categoryId": 0,
                    "brandId": 0,
                    "gallery": [],
                    "keywords": "",
                    "brief": "",
                    "isOnSale": True,
                    "sortOrder": 0,
                    "picUrl": "",
                    "shareUrl": "",
                    "isNew": False,
                    "isHot": False,
                    "unit": "件",
                    "counterPrice": 0,
                    "retailPrice": 0,
                    "addTime": "2026-09-21 11:00:00",
                    "updateTime": "2026-09-21 11:00:00",
                    "deleted": False,
                }
            ],
        },
    },
    # 5. data 字段整个缺失：前端取 data.list 时会不会 undefined 崩溃
    "05-data字段缺失.json": {"errno": 0, "errmsg": "成功"},
    # 6. errno 未知值：看前端有没有兜底提示
    "06-未知错误码9999.json": {"errno": 9999, "errmsg": "未定义的错误码", "data": None},
    # 7. HTTP 500 但返回 HTML（网关挂掉的真实样子）
    "07-非JSON-HTML502.txt": (
        "<html>\r\n<head><title>502 Bad Gateway</title></head>\r\n"
        "<body bgcolor=\"white\">\r\n<center><h1>502 Bad Gateway</h1></center>\r\n"
        "</body>\r\n</html>\r\n"
    ),
}

for name, payload in FILES.items():
    path = os.path.join(HERE, name)
    if name.endswith(".txt"):
        with open(path, "w", encoding="utf-8") as f:
            f.write(payload)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    print(f"{os.path.getsize(path):>8} B  {name}")
