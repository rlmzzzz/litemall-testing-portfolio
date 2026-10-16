# API 接口自动化测试练习项目

> 一个用 `pytest` + `requests` 实现的**数据驱动接口自动化**小项目，纯练习用途，零外部依赖、可离线运行。

## 这个项目能讲什么（面试话术）

- **数据驱动**：测试逻辑只写一次，用例数据放在 `tests/data/cases.json`。加用例 = 往 JSON 加一行，不动代码。
- **覆盖维度**：CRUD（GET/POST/DELETE）、状态码断言（200/201/401/404）、鉴权（Bearer Token）、字段断言（支持 `data.id` 嵌套）、响应时间断言。
- **报告**：`pytest-html` 生成可视化 HTML 报告。
- **工程细节**：被测对象是我自己用标准库写的 mock 服务（`mock_api.py`），不依赖任何外部网络，保证练习随时可跑。

## 怎么运行

### 方式一：一键（推荐）

```powershell
cd 项目目录
& "C:\Users\李玉亭\.workbuddy\binaries\python\envs\litemall-auto\Scripts\python.exe" run_tests.py
```

它会自动启动 mock 服务、跑全部用例、生成 `reports/api-test-report.html`，结束自动关服务。

### 方式二：分开跑

```powershell
# 终端 1：启动 mock 服务
& "C:\Users\李玉亭\.workbuddy\binaries\python\envs\litemall-auto\Scripts\python.exe" mock_api.py

# 终端 2：跑测试
& "C:\Users\李玉亭\.workbuddy\binaries\python\envs\litemall-auto\Scripts\python.exe" -m pytest tests -v --html=reports/api-test-report.html --self-contained-html
```

## 怎么加一条用例

打开 `tests/data/cases.json`，复制一个对象、改字段即可，例如新增"查询慢接口超时断言失败"：

```json
{
  "name": "慢接口-响应时间应小于1000ms(故意失败演示)",
  "method": "GET",
  "path": "/api/slow",
  "expected_status": 200,
  "max_ms": 1000
}
```

> 注：`/api/slow` 服务端固定 sleep 1.5 秒，这条会把响应时间断言跑红——用来演示"红"长什么样，以及断言失败时报告怎么显示。

## 想测真实公开 API？

把 `BASE_URL` 指向公开测试服务（如 httpbin.org）并调整 `cases.json` 即可，框架不用改。
