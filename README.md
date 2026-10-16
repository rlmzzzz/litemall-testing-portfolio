# litemall 开源电商系统 · 测试实战作品集

> **被测对象**：[litemall](https://github.com/linlinjava/litemall) 开源电商系统（Spring Boot + Vue + MySQL）
> **我的角色**：独立承担测试全流程（个人项目）
> **测试周期**：2026.09 – 2026.10

本仓库记录了我对一个真实开源电商系统做的一次**完整测试实践**：从测试计划、用例设计，到接口测试、权限专项、性能测试、UI 自动化与 Python 接口自动化。**所有产出物与原始测试报告都在仓库里，可直接打开查看。**

---

## 一、项目背景

litemall 是一个前后端分离的开源电商系统，包含**用户端商城（H5）**、**后台管理系统**和**接口服务**三部分。项目本身**没有提供任何测试文档和测试环境**。

为了完整走一遍软件测试流程、产出可追溯的测试资产，我独立完成了：

```
环境部署 → 需求梳理 → 测试计划 → 用例设计 → 功能测试 → 接口测试 → 权限专项
        → 性能测试 → UI 自动化 → Python 接口自动化 → 缺陷跟踪 → 测试报告
```

---

## 二、测试范围与产出物

| 阶段 | 主要工作 | 产出物 | 位置 |
|---|---|---|---|
| 测试计划 | 梳理后台 **8 个功能模块**，明确测试范围与策略 | 测试计划、测试环境说明 | [`docs/`](docs/) |
| 用例设计 | 设计并执行测试用例 **80 条**，覆盖功能、边界、异常、权限 | 用例集（Excel） | [`testcases/`](testcases/) |
| 接口测试 | Postman 设计 **5 个集合（57 请求 / 241 断言）**，Newman 命令行执行 | 集合 + HTML 报告 | [`api-testing/`](api-testing/) |
| 权限专项 | **16 个接口 × 3 个角色**权限矩阵实测 | 权限验证报告 | [`api-testing/reports/`](api-testing/reports/) |
| 性能测试 | JMeter 梯度加压（20/50/100 并发）+ A/B 对照压测 | jmx 脚本 + HTML 看板 | [`performance-testing/`](performance-testing/) |
| UI 自动化 | Selenium IDE 录制核心流程 + side-runner 批量回放 | .side 脚本 + 回归报告 | [`ui-automation/`](ui-automation/) |
| Python 接口自动化 | requests + pytest 数据驱动框架 | 源码 + 测试报告 | [`api-automation-python/`](api-automation-python/) |
| 缺陷管理 | 提交缺陷单并跟踪至关闭（接口测试阶段 **4 单**） | 缺陷单 | [`api-testing/`](api-testing/) |

---

## 三、关键测试结果

### 1. 越权缺陷（严重级）
通过「**16 个接口 × 3 个角色**」的权限矩阵实测，发现**统计面板接口未做权限校验**——任意低权限角色可越权读取全站经营数据。

### 2. 分页参数边界缺陷
使用 Fiddler 在真实请求上改包验证：`limit=0` 时服务端**未做参数边界校验**，一次返回全量 **250 条 / 1.5 MB** 数据。

### 3. A/B 对照压测，量化缺陷影响
针对上述缺陷做 A/B 对照压测（**同一脚本、同一压力量，只改分页参数**）：

| 分组 | 分页参数 | 吞吐量 | 平均响应时间 | 结果 |
|---|---|---|---|---|
| 基准组 | `limit=20` | 195.6 TPS | 97 ms | 正常 |
| 异常组 | `limit=0` | 85.3 TPS | 221 ms | 吞吐**下降约 56%** |

用数据说明「一个参数校验缺失」的实际业务影响——不只是"返回的数据变多了"，
而是直接把接口吞吐砍掉一半以上。

### 4. 性能基线
JMeter 对后台核心链路梯度加压 **20 / 50 / 100** 并发：

| 并发数 | 吞吐量 (TPS) | 平均响应时间 | 90% 响应时间 | 错误率 |
|---|---|---|---|---|
| 20 | 242.6 | 78 ms | 164 ms | 0% |
| 50 | 234.6 | 191 ms | 315 ms | 0% |
| 100 | 219.3 | 412 ms | 545 ms | 0% |

> 三档加压下吞吐量保持稳定（220–243 TPS），响应时间随并发近似线性增长，错误率全程 0%，
> 说明系统在该压力区间内未出现瓶颈或雪崩。

### 5. 接口自动化断言
5 个集合 / 57 个请求 / **241 条断言**，其中 4 条失败断言全部定位为真实缺陷。

### 6. 缺陷管理
接口测试阶段共提交 **4 个缺陷单**（1 个严重级越权、1 个敏感信息字段泄露、1 个分页参数校验缺失、
1 个异常查询返回 502），并在禅道中跟踪状态。缺陷单全文（含复现步骤、预期结果依据与附件说明）见
[`api-testing/13-禅道Bug单（接口测试阶段）.md`](api-testing/)。

---

## 四、目录导航

```
litemall-测试作品集/
├── docs/                       测试计划、环境说明、需求基线、数据库手册
├── testcases/                  测试用例集（Excel）
├── api-testing/                接口测试：Postman 集合、脚本、Newman 报告、Bug 单
│   ├── postman/                5 个 Postman 集合 + 环境变量
│   ├── scripts/                token 获取、批量执行、证据校验等脚本
│   └── reports/                Newman 生成的 HTML 测试报告
├── performance-testing/        性能测试
│   ├── scripts/                JMeter 测试计划（.jmx）
│   ├── tools/                  批量压测与结果对比脚本
│   └── reports/                JMeter HTML 看板（梯度加压 + A/B 对照）
├── ui-automation/              UI 自动化
│   ├── scripts/                Selenium IDE 脚本（.side）
│   ├── tools/                  回归执行器与报告生成器
│   └── reports/                回归测试报告 + 执行截图
├── api-automation-python/      Python 接口自动化
│   ├── 接口自动化/             requests + pytest 测试用例与夹具
│   └── api-test-practice/      Mock 接口 + 数据驱动练习项目
└── evidence/                   抓包/测试证据截图
```

---

## 五、怎么查看这些报告

| 想看什么 | 打开哪个文件 |
|---|---|
| JMeter 性能报告（梯度加压） | `performance-testing/reports/steady_100/index.html` |
| JMeter A/B 对照报告 | `performance-testing/reports/limit_0/index.html` vs `limit_20/index.html` |
| Newman 接口测试报告 | `api-testing/reports/*报告.html` |
| Selenium 回归测试报告 | `ui-automation/reports/回归测试报告.html` |
| Python 接口自动化报告 | `api-automation-python/接口自动化/reports/接口自动化报告.html` |
| 缺陷清单 | `api-testing/13-禅道Bug单（接口测试阶段）.md` |
| 测试用例集 | `testcases/03-后台测试用例集（实测版）.xlsx` |

> 这些都是**离线 HTML**，下载后双击即可在浏览器打开，不依赖网络。

---

## 六、环境与工具

| 类别 | 使用内容 |
|---|---|
| 被测系统 | litemall（Docker 部署：MySQL + 后端服务 + 管理后台） |
| 功能/接口测试 | Postman、Newman、Fiddler |
| 性能测试 | Apache JMeter 5.6.3 |
| UI 自动化 | Selenium IDE + selenium-side-runner、Selenium 4 |
| 接口自动化 | Python 3、requests、pytest、pytest-html |
| 缺陷管理 | 禅道（缺陷全生命周期跟踪） |
| 数据库 | MySQL（SQL 校验操作前后数据一致性） |

---

## 七、另一个独立项目：Mock 接口自动化练习项目

为了有一个**可控、可离线演示**的接口自动化作品，我用 Python 标准库自建了一个 Mock REST 服务当被测对象，并配套写了数据驱动的测试框架：

- **被测对象**：`http.server` 自建 Mock REST 服务，覆盖 7 个场景（商品增删查、登录鉴权、管理接口鉴权、慢接口）
- **测试框架**：requests + pytest，用例数据与测试逻辑分离（用例写在 JSON，加用例不改代码）
- **断言维度**：HTTP 状态码、响应字段（含嵌套取值）、Token 鉴权、响应时间
- **成果**：10 条用例全部通过，pytest-html 输出可视化报告，**零外部依赖、可离线运行**

位置：[`api-automation-python/api-test-practice/`](api-automation-python/api-test-practice/)

---

## 说明

本仓库仅用于个人测试实践与作品展示，被测系统 litemall 为开源项目（作者 [linlinjava](https://github.com/linlinjava/litemall)），本仓库不含其源码，仅包含我个人的测试产出物。
