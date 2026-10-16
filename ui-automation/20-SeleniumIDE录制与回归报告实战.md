# 20 · Selenium IDE 录制 + side-runner 出回归报告（实操版）

> 本篇是 `17-阶段六-Selenium自动化指南.md` 里「第 2~7 步」的落地版。
> **文档里的每一条命令和参数，都是 2026-09-24 在这台机器上实跑过的**，不是凭记忆抄的文档。

---

## 零、先说结论：你的工具链已经是好的

实测结果（2026-09-24）：

| 检查项 | 实测值 | 结论 |
|---|---|---|
| node | v24.20.0 | ✅ |
| npm | 11.19.0 | ✅ |
| `selenium-side-runner` | **4.0.13，已全局安装** | ✅ 不用装 |
| Chrome | 153.0.8010.53 | ✅ |
| chromedriver | 不在 PATH | ✅ **不用管** —— Selenium Manager 会自动下载匹配版本 |
| 实跑一次冒烟脚本 | `Tests: 1 passed`、退出码 0、耗时 4.3 s | ✅ 链路完全通 |

**这意味着：你不需要做任何安装配置，直接开始录。**

> 唯一卡住的是：**Docker Desktop 当前没启动**，`localhost:9527` 和 `8080` 都不通。所以第 0 步先把它拉起来。

---

## 第 0 步：把被测环境拉起来（5 分钟，不做这步后面全白搭）

```powershell
# 1. 先手动双击启动 Docker Desktop，等它右下角图标变成 running
# 2. 然后启动三个容器
docker start mysql litemall litemall-admin-web
docker ps --format "{{.Names}}\t{{.Status}}"
```

**验收**：浏览器打开 `http://localhost:9527` 能出现登录页。打不开就别往下走。

### ⚠️ 交叉坑：录制前必须关掉 Fiddler 的伪造响应

上一阶段你在 Fiddler 里开了 AutoResponder 的 `Enable rules`。**录制前一定要取消勾选**，否则你录到的是「假数据下的页面行为」，脚本在真实环境跑就全红。

> 这是两个测试阶段互相污染的典型例子：抓包工具开着的时候，不能做自动化录制。

---

## 第 1 步：确定录什么（3 条，不要多）

沿用 17 号文档的筛选标准（高频 + 高价值 + 结果可断言）。建议这 3 条：

| # | 流程 | 为什么值得录 | 断言什么（关键） |
|:--:|---|---|---|
| 1 | **登录 → 进入首页** | 最高频，挂了全站不可用；也是所有脚本的前置 | 登录后页面出现用户名/菜单元素 |
| 2 | **商品列表查询** | 核心业务读路径，回归必跑 | 表格出现数据行、总条数变化 |
| 3 | **曾出过 Bug 且已修的流程** | 自动化的经典价值 = **防止再犯** | 按当时那个 Bug 的现象反着断言 |

**一条铁律**：没有断言的脚本 = 没写脚本。只 `open` 一下页面不算测试，那叫"能打开"。

---

## 第 2 步：录制（Selenium IDE 插件里做）

1. Chrome 装 **Selenium IDE** 扩展 → 打开 → **Create a new project**，命名如 `litemall-核心回归`
2. **Base URL 填 `http://localhost:9527`** ← 填错后面命令行跑会全跑飞
3. 点 **REC**（右上角红点）→ 在页面里正常操作一遍 → 停录
4. **录完立刻点 ▶ Run 试跑一次** —— 录的时候能过 ≠ 回放能过（Vue 页面尤其如此）
5. **Save 成 `.side` 文件**，放到：
   ```
   litemall-测试实战\自动化测试\scripts\
   ```

### ★ 命令名的坑（我实测踩到了）

**`assert title` 是非法命令，会报 `Unknown command assert title`。**

Selenium IDE 的命令是**驼峰、无空格**的，别按自然语言写：

| 错误写法 | ✅ 正确写法 |
|---|---|
| `assert title` | `assertTitle` |
| `assert text` | `assertText` |
| `wait for element visible` | `waitForElementVisible` |
| `assert element present` | `assertElementPresent` |

**通用做法**：命令一律从 IDE 命令输入框的**下拉候选里点选**，不要手打。下拉里选不到的命令名，就是不存在。

---

## 第 3 步：改造脚本（录完必做的三件事）

录出来的脚本只能算"半成品"，必须改三处才能进回归：

### ① 加等待 —— Vue 页面不加必挂

在每次点击/跳转**之后**、断言**之前**，插一条：

```
waitForElementVisible | css=你要断言的那个元素 | 10000
```

原因：Vue 是异步渲染的，脚本执行速度远快于页面渲染。不加等待 = "元素还没出来就断言" = 偶发失败（跑 3 次挂 1 次那种，**最难查**）。

### ② 加断言 —— 把"看到页面"升级成"验证内容对"

```
assertText  | css=某个元素 | 期望看到的文字
assertTitle | 期望的标题
```

断言要挑**稳定不变**的内容（业务数据别写死，比如商品名会变）。

### ③ 参数化 —— 账号密码不要写死在脚本里

```
store | admin123 | username      ← 定义变量
type  | id=username | ${username}
```

这样同一套脚本换角色跑（admin123 / mall123 / promotion123），只改变量不改脚本。

---

## 第 4 步：命令行跑（selenium-side-runner）

### 真实可用的参数（来自本机 `--help` 实测）

| 参数 | 作用 | 建议值 |
|---|---|---|
| `-c, --capabilities` | 指定浏览器 | `browserName=chrome` |
| `-o, --output-directory` | **结果写成 JSON** 到指定目录 | `reports/` |
| `-z, --screenshot-failure-directory` | **失败自动截图** ← 很有用 | `reports/screenshots/` |
| `-r, --retries` | 失败重跑 N 次 | 稳定性差的脚本先用 `1` 顶着 |
| `-t, --timeout` | 单个元素定位超时（默认 15000） | `20000` |
| `-T, --jest-timeout` | 单个用例超时（默认 60000） | `120000` |
| `-f, --filter` | 按正则只跑部分套件 | `--filter 登录` |
| `--base-url` | **覆盖 IDE 里录的 base URL** | `http://localhost:9527` |
| `-w, --max-workers` | 并发数 | 默认=核数 |
| `-n, --config-file` | 用 `.side.yml` 固化配置 | 熟练后用 |

### 一条命令跑完（已经给你封装好了）

```powershell
cd "C:\Users\李玉亭\WorkBuddy\2026-09-15-16-30-32\litemall-测试实战\自动化测试"
python tools\run_regression.py                      # 跑 scripts/ 下所有 .side
python tools\run_regression.py scripts\01-xxx.side  # 只跑某一个
python tools\run_regression.py --headless           # 不弹浏览器，跑得快
python tools\run_regression.py --filter 登录         # 只跑名字含"登录"的套件
```

`run_regression.py` 帮你做了四件事：**跑脚本 → 失败截图 → JSON 转 HTML 报告 → 自动打开报告**。

（Python 用这个路径：`C:\Users\李玉亭\.workbuddy\binaries\python\versions\3.13.12\python.exe`）

### 换浏览器跑（Chrome 卡 / 想用 Edge）

**实测可用（2026-09-24）**：

```powershell
python tools\run_regression.py --browser edge      # 用 Edge 跑，实测 1 passed / 退出码 0
python tools\run_regression.py --browser chrome    # 默认，用 Chrome
```

| 浏览器 | `-c` 里要写的名字 | 易错点 |
|---|---|---|
| Chrome | `browserName=chrome` | — |
| **Edge** | `browserName=**MicrosoftEdge**` | ⚠️ **不是 `edge`**！写 `edge` 起不来 |
| Firefox | `browserName=firefox` | 需本机装了 Firefox |

**🚨 2026-09-24 更正 —— 官方 Selenium IDE 的 Chrome 扩展已下架，Edge 也装不到**

- Chrome 应用商店里**搜不到它**（搜出来的 Katalon Recorder / TestCase Studio / Ui.Vision / FlowMacro 全是第三方竞品，**导出的格式与 `.side` 不通用，别装**）
- 直链 `chromewebstore.google.com/detail/selenium-ide/...` 已作废
- 依据：官方仓库 issue #1894 / #1900、Google Groups 官方讨论帖 —— 官方已停止 Chrome 商店分发（Manifest V3 政策收紧 + 维护停摆）
- **可用路径**：录制用 **Firefox + 官方 Selenium IDE**（AMO 商店在架，实测可达）；回放仍用 Edge + side-runner
  - AMO 链接：`https://addons.mozilla.org/zh-CN/firefox/addon/selenium-ide/`
  - ⚠️ 回放**不要**用 `--browser firefox`：Firefox 需要 geckodriver，它托管在 GitHub（本机不通）。`.side` 跨浏览器通用，照旧用 `--browser edge`
- ⚠️ 任何第三方 "crx 下载站" 的 Selenium IDE 一律不要装（扩展权限极高，来源无法验证）

> **Edge 启动时控制台会刷一堆 ERROR**（`LoadEnclaveImageW failed`、`QQBrowser user data path not found`）——
> **这是 Edge 自身的噪音日志，不影响测试**。实测它一边刷 ERROR 一边 `1 passed`。别被吓到，以报告结论为准。

### ⚠️ `--base-url` 会强制覆盖脚本里录的 URL

实测发现：传了 `--base-url http://localhost:9527` 后，脚本里原本录的 `https://example.com` 被顶掉，直接跑去开 litemall 首页了。

所以 `run_regression.py` **默认不传**这个参数（用脚本自己录的 URL），只在你需要统一改指向时才显式传：
```powershell
python tools\run_regression.py --base-url http://localhost:9527
```

---

## 第 5 步：报告

### 一个必须知道的事实

**`selenium-side-runner` 官方只有 JSON 输出，没有 HTML 报告选项。**
`-o` 参数生成的就是 `reports/results-<时间戳>.json`（标准 Jest JSON 格式）。

所以想给面试官看，得自己转一层 —— 我已经写好了：

```powershell
python tools\jest_json_to_html.py --latest reports reports\回归测试报告.html
```

生成的 HTML 报告包含：**结论徽章（全部通过/存在失败）+ 用例总数/通过/失败/通过率 概览卡片 + 每条用例的耗时与失败原因（可点击展开堆栈）+ 失败截图目录说明**。

### 报告里要盯的三个数

| 指标 | 说明 |
|---|---|
| **通过率** | 不能只看"有没有红"，要看比例趋势 |
| **失败原因** | `Unknown command xxx` = 命令名写错；`Unable to locate element` = 等待没加够或选择器失效 |
| **耗时** | 单条超过 30 s 说明等待策略有问题 |

---

## 第 6 步：稳定性（完成标志）

**连续跑 3 次，3 次全绿，才算这条脚本"能用"。**

跑 1 次过是运气，跑 3 次都过才是脚本。偶发失败的修法优先级：

1. 加 / 加长 `waitForElementVisible`（90% 的偶发失败都是等待问题）
2. 换更稳的选择器（**优先级：`id` > `name` > `css` > `xpath`**，xpath 最容易随页面改版失效）
3. 最后才考虑 `--retries 1`（这是掩盖问题，不是解决问题，用了要在报告里说明）

---

## 交付物清单（做完这阶段你手上会有什么）

```
litemall-测试实战\自动化测试\
├── scripts\          ← 你录的 .side 脚本（≥1 个，建议 3 条核心流程）
├── reports\
│   ├── results-<时间戳>.json   ← runner 原始结果（留档）
│   ├── 回归测试报告.html        ← 给面试官看的成品
│   └── screenshots\            ← 失败自动截图（Bug 单附件）
└── tools\
    ├── run_regression.py        ← 一键跑 + 出报告
    └── jest_json_to_html.py     ← JSON → HTML 报告转换器
```

---

## 踩坑表（含 2026-09-24 实测新增）

| # | 坑 | 现象 | 解法 |
|:--:|---|---|---|
| 1 | **命令名写成带空格** | `Unknown command assert title` | 用驼峰 `assertTitle`；从下拉候选里选，别手打 |
| 2 | **Docker 没开就跑脚本** | 全部用例红、页面打不开 | 先 `docker start`，验收 9527 能开再说 |
| 3 | **Fiddler AutoResponder 没关** | 录到假数据，真实环境全红 | 录制前取消 `Enable rules` |
| 4 | Vue 页面不加等待 | 偶发失败，时好时坏 | 点击后插 `waitForElementVisible` |
| 5 | 以为有 HTML 报告 | 只看到 JSON，以为失败了 | 官方只有 JSON，用 `jest_json_to_html.py` 转 |
| 6 | chromedriver 版本不匹配 | 驱动报错 | **不用管** —— Selenium Manager 自动下载匹配版本（实测 Chrome 153 直接跑通） |
| 7 | 退出码非 0 但页面看着没问题 | 用例其实失败了 | 以报告为准，不看浏览器 |
| 8 | **`--base-url` 强制覆盖脚本 URL** | 脚本跑去开别的站，断言全红 | 默认别传；要改指向才显式传（见上一节） |
| 9 | **Edge 刷一堆 ERROR 日志** | `LoadEnclaveImageW failed` 等 | Edge 自身噪音，**无害**，以报告结论为准 |
| 10 | Edge 的 browserName 写成 `edge` | 浏览器起不来 | 必须是 `MicrosoftEdge` |

---

## 面试话术（做完这阶段就能讲）

> "环境是用 Docker 部署的 litemall，我用 Selenium IDE 录制了 3 条核心业务流程的回归脚本，
> 包括登录、商品查询，以及一条曾经出过缺陷、修复后用来防回归的流程。
> 脚本里加了显式等待和断言，账号做了参数化，可以用不同角色跑。
> 执行上接了 selenium-side-runner，一条命令批量跑，失败自动截图，
> 官方只出 JSON，我自己写了个脚本把它转成 HTML 报告，方便归档和汇报。
> 稳定性上要求连续跑 3 次全绿才算通过。"

**加分点**：主动说出"官方只有 JSON 我自己转了一层"—— 说明你不是只会点工具。
**别说过头**：Selenium IDE 是录制工具，别写"精通自动化测试"。

---

## 自检题（做完要能答）

1. 为什么录完必须在点击后加 `waitForElementVisible`？
2. `assert` 和 `verify` 的区别是什么？（答不出就查，面试会问）
3. 选择器优先级为什么是 id > name > css > xpath？
4. 连续跑 3 次全绿这个要求，是为了解决什么问题？
5. 为什么自动化要优先选"曾经出过 Bug"的用例？
