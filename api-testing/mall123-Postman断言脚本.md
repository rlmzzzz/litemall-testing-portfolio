# mall123 的 Postman 断言脚本

> 用途：验证 mall123（权限范围＝只有品牌 + 分类）在后台各接口上的权限是否被正确拦截
> 所有期望值均来自 2026-09-20 实测，不是推测

---

## 零、凭证怎么传（先解决这个，否则后面结论全废）

### ⚠️ 第一个坑：把 token 放进 Params

**`http://127.0.0.1:8080/admin/dashboard?token=xxx` —— token 放在 Query Params 里，服务端根本不看。**

源码 `AdminWebSessionManager.java`：

```java
// 第 14 行：字段名写死
public static final String LOGIN_TOKEN_KEY = "X-Litemall-Admin-Token";

// 第 22 行：关掉「URL 里带 session id」这种方式
setSessionIdUrlRewritingEnabled(false);

// 第 27 行：只从请求头取值
String id = WebUtils.toHttp(request).getHeader(LOGIN_TOKEN_KEY);
```

全仓库搜索 `getParameter("token")` —— **零命中**。所以 `?token=` 只是个装饰品。

| 请求（**不带任何 cookie**） | 结果 |
|---|---:|
| 什么都不带 | errno=501 `{"errno":501,"errmsg":"请登录"}` |
| `?token=<有效的 mall123 token>` | **501** ← 有效 token 也没用 |
| `?token=<有效的 admin123 token>` | **501** |
| `?token=乱码` | **501** |

**结论：URL 里的 token 完全无效，服务端从头到尾没读过它。**

---

### ⚠️ 第二个坑（更隐蔽）：通过不是因为 token 对，而是 **cookie 替你开了门**

`?token=xxx` 能"过"，是 `JSESSIONID` cookie 在兜底。

**实测：先在同一个域名下登录过，之后哪怕 header 名字全写错，请求照样通**

| 请求（**带 cookie**） | errno |
|---|---:|
| 只用 cookie，不带任何 header | **0** |
| cookie + `?token=乱码` | **0** |
| cookie + Header 改名「`Token: 乱码`」 | **0** |

**为什么会有 cookie**：Postman 的 Cookie Jar 按域名保存。你在 `127.0.0.1:8080` 上发过 `POST /admin/auth/login`，`JSESSIONID` 就被存下来了，之后**所有**发往 `127.0.0.1` 的请求都会自动带上。

> **⚠️ 这条直接决定你越权结论的真假**：cookie 属于**最后一次登录的那个账号**。
> 如果你先用 admin123 登录过、再来跑 mall123 的越权用例，服务端认的是 **admin123**，
> 那"mall123 能看到全站数据"这个结论就是**假的**（虽然 Bug-7 本身是真的）。

---

### 服务端的两条凭证通道（实测还原的完整规则）

```
读 Header「X-Litemall-Admin-Token」
  ├─ 有值 → 只认它。查不到对应会话 = 未登录（501）
  │        副作用：同时会换发一个新的 JSESSIONID 给你
  └─ 空/没有 → 回落到读 Cookie「JSESSIONID」→ 有会话就认
```

| 场景 | 结果 |
|---|---|
| 有效 cookie + **乱码 header** | **501** ← header 优先，坏 header 会盖掉好 cookie |
| 有效 cookie + 有效 header | 0 |
| 有效 cookie + 空 header（`X-...-Token: `） | 0 ← 视为"没有"，回落 cookie |
| 乱码 header 请求一次后 | cookie 被换成新的匿名会话，**原来的 cookie 也失效了** |

**还有一个关键发现：token 和 JSESSIONID 是同一个值**

```
响应体里的 token       : 58bb6cd3-14c6-4ee5-a4f1-f2264905b569
Cookie 里的 JSESSIONID : 58bb6cd3-14c6-4ee5-a4f1-f2264905b569
                          ↑ 完全一致
```

**token 不是另造的一把钥匙，它就是 sessionId，只是换了个投递口。** 这也解释了为什么它 6 小时过期
（`setGlobalSessionTimeout(MILLIS_PER_HOUR * 6)`）—— 它本质上是 Shiro 的会话。

---

### 怎么彻底关掉 cookie 干扰（做完这一步，才叫接口测试）

**Postman → 右上角齿轮 Settings → General → 取消勾选 `Send cookies`**

关掉之后：

- 登录请求照样能拿到 token（token 在响应体里，不需要 cookie）
- 后续请求**只能**靠 `X-Litemall-Admin-Token` header，凭证完全由你显式控制
- 越权结论才站得住：你随时知道手上的身份是谁

其它做法（次选）：

| 做法 | 说明 |
|---|---|
| 点请求下方的 `Cookies (1)` → 删掉 127.0.0.1 的 JSESSIONID | 只清一次，之后登录又会写进去 |
| 换个域名（如 `localhost` ↔ `127.0.0.1`） | 能临时隔离，但你在两个域名都登录过之后就失效了 |

> 补充：cookie 是按域名隔离的 —— 拿 `localhost` 的 cookie 去请求 `127.0.0.1` 会得到 501。
> 所以"换域名"曾经能隔离，**但现在你在 `127.0.0.1` 上也登录过了，这招已经失灵**。

---

### ★ 最重要的规矩：每条越权用例前面，必须先过「身份自证」

**这是整个接口测试里最重要的一步，比断言本身更重要。**

你想证明的是「**mall123** 越权了」。但如果这一枪打出去、门开的时候，站在门口的是 admin123 —— 那你的结论、你的截图、你提的 Bug 单，**全都是废的**。

**做法**：在越权用例集的**最前面**放一个请求，专门自证身份。

| 项 | 值 |
|---|---|
| 方法 | `GET` |
| URL | `http://127.0.0.1:8080/admin/auth/info` |
| Header | `X-Litemall-Admin-Token: {{mallToken}}` |

```javascript
var jsonData = pm.response.json();

pm.test("【身份自证】我手上这个凭证确实是 mall123 的", function () {
    pm.expect(jsonData.data.name).to.eql("mall123");
});

pm.test("【身份自证】角色是商场管理员", function () {
    pm.expect(jsonData.data.roles).to.eql(["商场管理员"]);
});
```

**这两条断言绿了，后面的越权结论才算数。红了 → 立刻停下，先查凭证，别往下跑。**

> 这是接口测试里的专业习惯，业内叫**前置条件校验（precondition assertion）**。
> 面试时讲：**"我在越权用例前加了身份自证断言，确保我手上的凭证确实是被测账号的身份，避免用错身份得出假结论。"**

---

### 怎么一眼看出「身份是不是串了」

| 现象 | 说明 |
|---|---|
| 请求 200 OK，`errno=0`，`data.list` 里有数据 | **先别庆祝**，先去 `/admin/auth/info` 看 `name` 是谁 |
| 请求 200 OK，`errno=506` | ✅ 真的被拦了，这个身份没权限 |
| 请求 200 OK，`errno=501` | 凭证完全没送到，服务端认为你没登录 |
| 请求 200 OK，`errno=0` 且 `data.list` 首条里出现了**自己不该看到的账号** | 高危信号：身份串了，或真的越权了，必须用身份自证区分 |

**排查顺序（死记）：**

```
① 关掉 Send cookies（Settings → General）
② 打开 Console，看这一枪实际发出的 Headers 里有没有 X-Litemall-Admin-Token
   ← 变量为空时 Postman 会【不发】这个 header，只留一个空壳，看不出来
③ 跑身份自证请求，确认 name = mall123
④ 再跑越权用例
```

> ⚠️ **变量为空时 Postman 直接不发这个 header** —— 这是最容易骗过眼睛的一点。
> 看图看不出来（Headers 列表里那一行还在），必须去 **Console** 看实际发出的内容。

---

### token 的正确放法

| | 放哪 | 长什么样 |
|---|---|---|
| ❌ 错误 | Params / URL 查询字符串 | `?token=xxx` |
| ✅ 正确 | **Headers** | `X-Litemall-Admin-Token: {{mallToken}}` |

- **Header 名不区分大小写**：`x-litemall-admin-token` 同样有效（实测 errno=0）
- **但名字必须对**：`Token`、`Authorization: Bearer xxx` 全部 501（实测）
- **为什么不能放 URL**：URL 会进浏览器历史、书签、服务器访问日志、以及跳转时的 `Referer` 头 —— **token 放这里等于泄露**。业务参数（`page` / `limit` / `name`）才放 Params。

---

### 复现脚本

```powershell
cd "C:\Users\李玉亭\WorkBuddy\2026-09-15-16-30-32\litemall-测试实战\接口测试"
& "C:\Users\李玉亭\.workbuddy\binaries\python\versions\3.13.12\python.exe" probe_auth.py
```

一次跑完 5 组实验（token≈JSESSIONID、放法/名字对照、cookie 兜底、优先级与副作用、域名隔离），输出可直接截屏进测试记录。

---

## 一、实测权限基线（断言的依据）

用 mall123 的 token 逐个调接口，16 个接口实测结果：

| 接口 | errno | errmsg | 权限 |
|---|---:|---|---|
| `/admin/brand/list` | **0** | 成功 | ✅ 有权限（2087 字节） |
| `/admin/category/list` | **0** | 成功 | ✅ 有权限（25039 字节） |
| `/admin/goods/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| `/admin/user/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| `/admin/order/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| `/admin/coupon/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| `/admin/topic/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| `/admin/issue/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| `/admin/keyword/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| `/admin/ad/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| `/admin/role/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| `/admin/log/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| `/admin/comment/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| `/admin/aftersale/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| `/admin/groupon/list` | 506 | 无操作权限 | ❌ 正确拦截 |
| **`/admin/dashboard`** | **0** | 成功 | ★ **异常！应 506，实际放行（Bug-7）** |

**关键**：`errmsg` 逐字是 **`无操作权限`**（不是"无权限"，也不是英文）。断言字符串必须一字不差。

---

## 二、登录请求的断言脚本

**请求**：`POST http://127.0.0.1:8080/admin/auth/login`
**Body**：`raw` + `JSON` → `{"username":"mall123","password":"mall123"}`
**写在哪**：`Scripts` → `Post-response`（旧版叫 `Tests`）⚠️ **不是 Pre-request Script**

```javascript
// ============================================================
//  mall123 登录 —— 存 token + 4 条断言
//  变量名用 mallToken，不是 token！
//  原因：越权测试要同时持有 mall 和 admin 两个身份，
//        共用一个 token 变量会被后登录的账号覆盖掉。
// ============================================================

var jsonData = pm.response.json();

// ---- 存 token 到环境变量 ----
pm.environment.set("mallToken", jsonData.data.token);
console.log("mall123 token =", jsonData.data.token);

// ---- 断言 1：HTTP 层 ----
pm.test("HTTP 状态码是 200", function () {
    pm.response.to.have.status(200);
});

// ---- 断言 2：业务层 ----
pm.test("登录成功 errno = 0", function () {
    pm.expect(jsonData.errno).to.eql(0);
});

// ---- 断言 3：返回值存在且类型正确 ----
pm.test("返回了非空 token", function () {
    pm.expect(jsonData.data.token).to.be.a("string").and.not.empty;
});

// ---- 断言 4：确认拿到的是谁的身份 ----
pm.test("登录身份是 mall123", function () {
    pm.expect(jsonData.data.adminInfo.nickName).to.eql("mall123");
});
```

> **断言 4 为什么重要**：只断言"有 token"是不够的。如果账号密码表填错、环境配错，
> 你依然会拿到一个 token，但它的主人不是 mall123 —— 那后面所有权限结论都是错的。
> **验证返回值的存在 ≠ 验证返回值的正确。**

---

## 三、有权限的接口（品牌 / 分类）断言脚本

**请求**：`GET http://127.0.0.1:8080/admin/brand/list?page=1&limit=5`
**Headers**：`X-Litemall-Admin-Token` = `{{mallToken}}`

```javascript
var jsonData = pm.response.json();

pm.test("HTTP 状态码是 200", function () {
    pm.response.to.have.status(200);
});

pm.test("mall123 有品牌权限，errno = 0", function () {
    pm.expect(jsonData.errno).to.eql(0);
});

pm.test("返回了 list 数组", function () {
    pm.expect(jsonData.data.list).to.be.an("array");
});

pm.test("list 里有品牌数据", function () {
    pm.expect(jsonData.data.list.length).to.be.above(0);
});
```

分类接口同理，URL 换成 `/admin/category/list?page=1&limit=5`，
断言描述改成「mall123 有分类权限」。

---

## 四、无权限的接口断言脚本（正确拦截的 13 个）

**请求**：例如 `GET http://127.0.0.1:8080/admin/goods/list?page=1&limit=5`
**Headers**：`X-Litemall-Admin-Token` = `{{mallToken}}`

```javascript
var jsonData = pm.response.json();

// 注意：这条仍然是绿的 —— 因为 litemall 所有业务错误都返回 HTTP 200！
// 只断 HTTP 200 等于没测，所以下面才是关键。
pm.test("HTTP 状态码是 200", function () {
    pm.response.to.have.status(200);
});

pm.test("无权限接口应返回 errno = 506", function () {
    pm.expect(jsonData.errno).to.eql(506);
});

pm.test("提示语应为「无操作权限」", function () {
    pm.expect(jsonData.errmsg).to.eql("无操作权限");
});

pm.test("被拒绝时不应返回任何业务数据", function () {
    pm.expect(jsonData.data).to.be.null;
});
```

**这 13 个接口都用同一套断言**，只改 URL：

```
goods / user / order / coupon / topic / issue / keyword
ad / role / log / comment / aftersale / groupon
```

---

## 五、越权验证断言脚本（今天最重要的一条）

**请求**：`GET http://127.0.0.1:8080/admin/dashboard`
**Headers**：`X-Litemall-Admin-Token` = `{{mallToken}}`

```javascript
var jsonData = pm.response.json();

pm.test("HTTP 状态码是 200", function () {
    pm.response.to.have.status(200);
});

// ★ 这条断言会【变红】—— 而红色就是缺陷证据，不是你写错了脚本
pm.test("【期望 506】mall123 不应有统计面板权限", function () {
    pm.expect(jsonData.errno).to.eql(506);
});

// ★ 这条也会【变红】—— 无权限账号不该拿到任何经营数据
pm.test("【期望无数据】被拒绝时 data 应为 null", function () {
    pm.expect(jsonData.data).to.be.null;
});
```

**跑出来会是这样：**

| 断言 | 结果 | 含义 |
|---|---|---|
| HTTP 状态码是 200 | ✅ 绿 | 协议层正常 —— 所以只断 HTTP 200 抓不到这个 Bug |
| errno = 506 | ❌ **红** | 实际返回 0，权限没拦 |
| data 为 null | ❌ **红** | 实际返回了全站经营数据 |

**截图提禅道时，一定要把"红的两条 + 响应体"一起截**，这样才看得出：
断言是按"应该是什么"写的，而实际行为不符合预期。

**响应体（三条账号对比，直接贴进 Bug 单）：**

```
admin123      → {"errno":0,"data":{"goodsTotal":250,"userTotal":1,"productTotal":255,"orderTotal":0}}
mall123       → {"errno":0,"data":{"goodsTotal":250,"userTotal":1,"productTotal":255,"orderTotal":0}}
promotion123  → {"errno":0,"data":{"goodsTotal":250,"userTotal":1,"productTotal":255,"orderTotal":0}}
```

一字不差 —— mall123 的权限只有品牌和分类，却读到了全站商品数、用户数、订单数。

---

## 六、五条写断言的规矩（照着抄，别背）

1. **变量名按账号区分**：`adminToken` / `mallToken` / `promotionToken`。
   用共用的 `token` → 后登录的账号会覆盖前一个 → 权限结论全错。

2. **必须断 `errno`**：litemall 所有业务错误都返回 **HTTP 200**，
   只断 HTTP 200 会把"被拒绝"判成"通过"。

3. **期望值必须有依据**：来自接口文档、需求、或业务规则。
   **绝不能看着实际结果反着写** —— 那等于把 Bug 固化成"正确"。

4. **断"语义不变量"，不断"数据快照"**：
   - ✅ 可以断：`errno = 506`、`list` 是数组、条数 ≤ limit
   - ❌ 不要断：`total` 必须等于 250（你上架一个商品它就红了，可系统是好的）

5. **URL 用 `127.0.0.1`，别用 `localhost`**：
   `localhost` 上有浏览器留下的 `JSESSIONID` cookie，
   header 没生效时它会替你开门 → 权限测试结果不可信。

---

## 七、集合顺序（决定能不能一键跑通）

在 Collection Runner 里，请求必须按这个顺序排：

```
1. mall123 登录          ← 必须第一个，它负责写入 {{mallToken}}
2. 品牌列表（有权限）      ← 断言 errno = 0
3. 分类列表（有权限）      ← 断言 errno = 0
4. 商品列表（无权限）      ← 断言 errno = 506
5. 统计面板（越权）        ← 断言 errno = 506，预期变红 = Bug-7 证据
6. ...
```

**为什么登录必须排第一**：环境变量里存的是"运行时值"，
导出集合时**不带**（防止 token / 密码泄露）。
所以每次跑都必须**重新登录、重新写一次变量**，否则后面全部 501。
