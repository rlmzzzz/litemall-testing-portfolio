# -*- coding: utf-8 -*-
"""
把接口测试阶段的 4 个缺陷单通过禅道 API v1 提交到产品 1（项目练习）。

用法：
    python submit_zentao_bugs.py            # 提交全部 4 个
    python submit_zentao_bugs.py --dry      # 只看 payload，不提交
    python submit_zentao_bugs.py --only 7 8 # 只提交指定编号

字段依据（禅道 22.5 源码）：
    api/v1/entries/bugs.php  post()  -> requireFields('title,pri,severity,type,openedBuild')
    module/bug/lang/zh-cn.php        -> severity/pri 取值 1~4；typeList 取值 codeerror/security/...
"""
import sys, json, base64, argparse, urllib.request, urllib.error

sys.stdout.reconfigure(encoding='utf-8')

BASE      = 'http://127.0.0.1/zentao/api.php/v1'
BASIC     = 'Basic ' + base64.b64encode(b'zentao:123456').decode()
PRODUCT   = 1      # 项目练习
PROJECT   = 1      # litemall电商系统
MODULE    = 0      # 产品下暂无 Bug 模块树
OS        = 'win11'
BUILD     = ['trunk']   # 影响版本 = 主干


def h(text):
    """转义，防止正文里的 < > & 破坏富文本结构"""
    return (str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def block(title, lines, ordered=True):
    """把一段文字包成 <p><strong>标题</strong></p> + 列表"""
    tag = 'ol' if ordered else 'ul'
    out = ['<p><strong>【%s】</strong></p>' % h(title), '<%s>' % tag]
    for ln in lines:
        out.append('<li>%s</li>' % h(ln))
    out.append('</%s>' % tag)
    return ''.join(out)


def para(text):
    return '<p>%s</p>' % h(text)


def code(text):
    return '<pre>%s</pre>' % h(text)


# ---------------------------------------------------------------- Bug 定义

BUGS = []

BUGS.append(dict(
    key='7', severity=2, pri=2, type='security',
    title='【系统管理】/admin/dashboard 未做权限校验，低权限角色可越权查看全站经营数据',
    steps=(
        block('前置条件', [
            '后端已启动：http://127.0.0.1:8080',
            'Postman 已关闭 cookie 自动携带（Settings → General → 取消勾选 Send cookies）',
            '已知低权限账号：mall123 / mall123（角色：商场管理员，仅品牌管理 + 类目管理权限）',
        ]) +
        block('复现步骤', [
            '用低权限账号登录取 token：POST http://127.0.0.1:8080/admin/auth/login，'
            '请求头 Content-Type: application/json，'
            '请求体 {"username":"mall123","password":"mall123"}，'
            '响应 {"errno":0,"errmsg":"成功","data":{"token":"<TOKEN>",...}}，记下 data.token',
            '【身份自证】先证明手上的 token 确实是 mall123 的：GET http://127.0.0.1:8080/admin/auth/info，'
            '请求头 X-Litemall-Admin-Token: <步骤1的TOKEN>。'
            '实测响应 name=mall123，roles=["商场管理员"]，perms 共 10 条且全部为 brand / category 相关，'
            '其中没有任何一条与 dashboard / 统计 / 看板相关',
            '用同一个 token 请求统计面板：GET http://127.0.0.1:8080/admin/dashboard，'
            '请求头 X-Litemall-Admin-Token: <步骤1的TOKEN>',
            '观察响应：HTTP 200，errno=0，成功返回全站经营数据',
            '【对照实验】用同一个 token 请求其它无权限接口，验证拦截是生效的：'
            'GET /admin/order/list?page=1&limit=5、GET /admin/user/list?page=1&limit=5、'
            'GET /admin/admin/list?page=1&limit=5、GET /admin/role/list?page=1&limit=5，'
            '实测均返回 {"errno":506,"errmsg":"无操作权限"}',
            '【换账号再验一次】用 promotion123 / promotion123（角色：推广管理员，仅推广模块权限）重复步骤 1-4，结果相同',
        ]) +
        block('实际结果', [
            '步骤 3 的实际响应（HTTP 200，103 字节）：'
            '{"errno":0,"data":{"goodsTotal":250,"userTotal":1,"productTotal":255,"orderTotal":0},"errmsg":"成功"}',
            'mall123 与 promotion123 均成功获取到全站经营统计数据（商品总数、用户总数、SKU 总数、订单总数）。',
            '注：数据条数会随环境数据变化（此前实测为 userTotal=13 / orderTotal=5）。'
            '判断依据是 errno=0 且返回了经营数据，不是具体数字。',
        ]) +
        block('预期结果', [
            'mall123 与 promotion123 均不具备统计面板权限，应返回 {"errno":506,"errmsg":"无操作权限"}',
            '依据1（身份与授权范围）：/admin/auth/info 返回的权限清单里，mall123 只有 10 条 brand/category 权限，没有一条与 dashboard 相关',
            '依据2（对比法）：同一账号访问其它 13 个无权限接口全部正确返回 506，说明系统的细粒度权限校验机制本身是正常工作的',
            '依据3（数据范围）：统计面板返回的是全站经营数据（订单总数、用户总数），远超 mall123 的授权范围（品牌 + 类目）',
        ]) +
        block('影响范围', [
            '后台任意一个已登录账号（哪怕权限最小）都能读取全站经营数据',
            '前端侧边栏不显示“统计面板”菜单只是隐藏入口，不构成防护：用 Postman / 浏览器直连接口即可获取',
            '属于纵向越权（权限提升 / 敏感信息泄露），按等保与常见安全基线应判定为缺陷',
        ]) +
        block('定位分析', [
            'litemall-admin-api/src/main/java/org/linlinjava/litemall/admin/web/AdminDashbordController.java 第 19-35 行',
        ]) +
        code('@RestController\n@RequestMapping("/admin/dashboard")\n@Validated\npublic class AdminDashbordController {          // ← 类上无 @RequiresPermissions\n    ...\n    @GetMapping("")\n    public Object info() {                       // ← 方法上也无 @RequiresPermissions\n        int userTotal = userService.count();\n        ...') +
        block('定位分析（对照写法）', [
            '对照 AdminBrandController.java 的正常写法：@RequiresPermissions("admin:brand:list") + '
            '@RequiresPermissionsDesc(menu={"商场管理","品牌管理"}, button="查询")',
            '结论：/admin/dashboard 未添加 @RequiresPermissions 注解，Shiro 不执行权限校验，任何已登录用户均可访问。',
            '建议修复：为 info() 方法补充 @RequiresPermissions("admin:dashboard:list") 及对应的 @RequiresPermissionsDesc。',
        ]) +
        block('系统性排查（证明非偶发）', [
            '对 litemall-admin-api 全部 30 个 Controller 做静态扫描，统计 @RequiresPermissions 注解数量：',
            'AdminAuthController（0 个）合理：登录/登出/验证码本身不能要求权限',
            'AdminProfileController（0 个）合理：有 @RequiresAuthentication，只返回自己的数据',
            'AdminRegionController（0 个）可接受：省市区基础数据，非敏感',
            'AdminDashbordController（0 个）← 本缺陷',
            '其余 26 个 Controller 均有 1~8 个权限注解，配置正常',
            '补充：4 个无权限注解的接口在不带任何凭证时均返回 {"errno":501,"errmsg":"请登录"}（实测），'
            '说明登录校验是全局生效的，缺的只是细粒度权限校验',
        ]) +
        para('附注：浏览器字段留空——本缺陷在接口层复现，不涉及浏览器差异。')
    ),
))

BUGS.append(dict(
    key='8', severity=3, pri=3, type='codeerror',
    title='【商品管理】/admin/goods/list 的 limit=0 时分页失效，一次返回全量 250 条（1.5 MB）',
    steps=(
        block('前置条件', [
            '后端已启动：http://127.0.0.1:8080',
            '已用 admin123 / admin123 登录并取得 token（POST /admin/auth/login）',
        ]) +
        block('复现步骤', [
            '请求商品列表，分页参数 limit 设为 0：GET http://127.0.0.1:8080/admin/goods/list?page=1&limit=0，'
            '请求头 X-Litemall-Admin-Token: <TOKEN>',
            '观察响应体中 data.list 的条数、以及响应体总大小',
            '【对照实验】把 limit / page 换成其它值再请求同一接口：'
            'limit=5 / limit=-1 / limit=abc / limit=10000 / page=9999&limit=5',
        ]) +
        block('实际结果', [
            'page=1&limit=5      → errno=0，返回 5 条，page 回显 1，limit 回显 5，pages 回显 50，响应 1,813 字节',
            'page=1&limit=0      → errno=0，返回 250 条（全表），page 回显 0，limit 回显 0，pages 回显 0，响应 1,514,715 字节（1.5 MB）',
            'page=1&limit=-1     → errno=0，返回 0 条，limit 回显 -1，响应 90 字节',
            'page=1&limit=abc    → errno=402，参数值不对（正确）；响应 40 字节',
            'page=1&limit=10000  → errno=0，返回 250 条，响应 1,514,719 字节（无上限保护）',
            'page=9999&limit=5   → errno=0，返回 5 条，page 回显 50（静默收敛到末页），响应 42,821 字节',
            '关键点：请求写的是 page=1，响应回显的却是 page=0；limit=0 时 pages 也回显为 0。响应中的分页字段与请求不一致。',
        ]) +
        block('预期结果', [
            'limit=0 属于非法分页参数，应满足以下任一（建议第 1 种）：',
            '（1）返回参数错误：{"errno":402,"errmsg":"参数值不对"}',
            '（2）按语义返回 0 条数据（list 为空数组）',
            '不应返回全量 250 条数据。',
            '依据1（业务语义）：limit = 每页条数，取值为 0 或负数没有业务含义',
            '依据2（源码）：AdminGoodsController.list() 中 @RequestParam(defaultValue = "10") Integer limit，'
            '默认值 10 说明正常取值为正整数',
            '依据3（内部对比法）：同一接口传 limit=abc 能正确返回 402 参数值不对，说明系统本身有参数校验机制，'
            '只是漏掉了数值边界（0 / 负数 / 超大值）',
        ]) +
        block('附带问题（同一成因，建议一并修复）', [
            'limit=10000 无上限保护，同样返回全量 250 条',
            'page=9999 时越界页被静默收敛为第 50 页，但响应中 page 字段回显 50 而非请求的 9999，'
            '调用方无法感知自己的参数被改写了',
        ]) +
        block('影响范围', [
            '单次请求返回全表数据，商品量增长后带来明显的性能与内存压力（当前 250 条已 1.5 MB，1 万条商品时约 60 MB）',
            '若上游（前端 / 第三方调用方 / 脚本）传入未校验的分页值，会触发大结果集响应，'
            '极端情况下可被用于接口层资源消耗攻击',
        ]) +
        block('定位分析', [
            'litemall-admin-api/src/main/java/org/linlinjava/litemall/admin/web/AdminGoodsController.java 的 list() 方法：'
            '@RequiresPermissions("admin:goods:list") + @GetMapping("/list") + '
            'public Object list(..., @RequestParam(defaultValue = "10") Integer limit, ...)',
            'limit 仅提供了默认值 10，未做取值范围校验，直接透传给分页组件；当 limit=0 时未启用分页，导致全表返回。',
            '建议修复：在 Controller 或 Service 层统一做分页参数边界校验，例如 limit 限制在 1~100、page 限制为 ≥1，'
            '非法值返回 errno=402。',
        ]) +
        block('为什么这 1.5 MB 这么大（影响放大分析）', [
            '同一接口 page=1&limit=5 只返回 1,813 字节，limit=0 却返回 1,514,715 字节。逐字段拆解：',
            '全部字段合计 1,509,453 字节（约 6,038 字节/条）',
            '其中 detail 字段（商品详情富文本）1,276,650 字节（平均 5,107 字符/条），占响应体 84.3%',
            '去掉 detail 后 183,973 字节（约 736 字节/条），仅占 12.2%',
            '同参数不同页的对比：page=1&limit=5 为 1,813 字节，page=50&limit=5 为 42,821 字节（23.6 倍），'
            '差异全部来自 detail 字段的内容',
            '说明：本条不单独提单（goods 有 detail、topic 有 content、category 有 children，属项目一致的实现风格，'
            '属设计选择而非实现缺陷），此处仅作为本单危害被放大 8 倍的直接原因一并说明。',
        ]) +
        para('附注：浏览器字段留空——本缺陷在接口层复现，不涉及浏览器差异。')
    ),
))

BUGS.append(dict(
    key='9', severity=3, pri=3, type='security',
    title='【用户管理】/admin/user/list 响应中返回会员密码哈希字段 password',
    steps=(
        block('前置条件', [
            '后端已启动：http://127.0.0.1:8080',
            '已用 admin123 / admin123 登录并取得 token',
        ]) +
        block('复现步骤', [
            '请求会员列表：GET http://127.0.0.1:8080/admin/user/list?page=1&limit=5，'
            '请求头 X-Litemall-Admin-Token: <TOKEN>',
            '查看响应体 data.list[0] 的字段列表',
            '对比前端「会员管理」列表页实际展示的列（无密码列）',
        ]) +
        block('实际结果', [
            'HTTP 200，errno=0，data.list 每条会员记录包含 16 个字段，其中含 password 字段，'
            '值为 BCrypt 哈希（60 字符，$2a$10$ 开头），实测值（已脱敏不完整）：$2a$10$lTu9qi0hr19OC800Db.eludFr0AXuJUSrMHi/iPYhKRlPFeqJxlye',
            '同时返回的还有 sessionKey、weixinOpenid 等会话 / 凭据类字段',
        ]) +
        block('预期结果', [
            '会员列表接口的响应中不应包含 password 字段'
            '（行业惯例：密码等凭据类字段永不下发到任何响应体，包括接口层与日志）。',
            '依据1（业务语义）：会员列表页只需要 id / username / nickname / mobile / avatar / status / addTime，'
            '密码哈希对任何业务逻辑都无用',
            '依据2（最小权限原则 / 数据最小化）：接口应只返回调用方需要的数据；密码哈希属凭据类敏感数据',
            '为什么定为“一般”而不是“严重”：泄露的是不可逆的 BCrypt 哈希（非明文），且访问需要管理员权限，'
            '实际可利用性有限。但字段本身不应出现，属应修复项。',
        ]) +
        block('影响范围', [
            '管理员账号被窃取 / 会话被劫持后，可批量拉取全量会员密码哈希，用于离线暴力破解',
            '哈希一旦外泄无法撤回（会员改密码前的历史泄露永久存在）',
            '响应体与前端日志、浏览器缓存、代理日志中会留下哈希副本',
        ]) +
        block('定位分析', [
            'litemall-admin-api/src/main/java/org/linlinjava/litemall/admin/web/AdminUserController.java 第 36-44 行',
        ]) +
        code('@GetMapping("/list")\npublic Object list(String username, String mobile, ...) {\n'
             '    List<LitemallUser> userList = userService.querySelective(username, mobile, page, limit, sort, order);\n'
             '    return ResponseUtil.okList(userList);       // ← 直接返回数据库实体 LitemallUser\n}') +
        block('修复建议', [
            '方案1（最小改动）：在 LitemallUser 的 password / sessionKey 字段上加 @JsonIgnore',
            '方案2（推荐）：改用 VO（UserVo）只输出列表页需要的字段，同时解决同类“字段冗余”问题',
            '方案3：对 password / sessionKey 等字段做统一脱敏，避免同类问题在其它接口复现',
        ]) +
        para('附注：浏览器字段留空——本缺陷在接口层复现，不涉及浏览器差异。')
    ),
))

BUGS.append(dict(
    key='6', severity=3, pri=3, type='codeerror',
    title='【商品管理】/admin/goods/detail 查询不存在的商品 id 返回 502 系统内部错误',
    steps=(
        block('前置条件', [
            '后端已启动：http://127.0.0.1:8080',
            '已用 admin123 / admin123 登录并取得 token',
        ]) +
        block('复现步骤', [
            '请求一个数据库中确定不存在的商品 id：GET http://127.0.0.1:8080/admin/goods/detail?id=99999999，'
            '请求头 X-Litemall-Admin-Token: <TOKEN>',
            '观察响应的 errno 与 errmsg',
            '【对照实验】把 id 换成其它取值再请求：id=0 / id=-1 / id=99999999999 / id=abc / id=1181009 / 不传 id',
        ]) +
        block('实际结果', [
            'id=99999999（合法但不存在）→ errno=502，系统内部错误 ← 本缺陷',
            'id=0 → errno=502，系统内部错误 ← 本缺陷',
            'id=-1 → errno=502，系统内部错误 ← 本缺陷',
            'id=99999999999（超出 int 范围）→ errno=402，参数值不对（正确）',
            'id=abc（类型非法）→ errno=402，参数值不对（正确）',
            'id=1181009（存在）→ errno=0，成功（正确）',
            '不传 id → errno=402，errmsg="arg0must not be null"（见下方附带问题）',
        ]) +
        block('预期结果', [
            '“商品不存在”属于可预期的业务场景，不是系统异常，应返回业务错误码与中文提示：'
            '{"errno":611,"errmsg":"商品不存在"}',
            '依据1（业务语义）：查询一个不存在的 id 是正常业务路径（用户手输 URL、商品被删除后书签失效），'
            '不是系统故障，不应报“系统内部错误”',
            '依据2（对比法）：同一接口的其它非法输入（id=abc、id=99999999999、不传 id）都能正确返回 402 并给出提示，'
            '说明该接口本身有参数校验；唯独“ID 合法但查不到记录”走到了 502，说明是查询结果为 null 后未判空导致的',
        ]) +
        block('附带问题（建议一并修，不单独提单）', [
            '不传 id 时 errmsg 返回 arg0must not be null：一是英文，二是 arg0 与 must 之间缺空格，明显是拼接错误。'
            '属于提示信息不规范，用户看不懂。',
        ]) +
        block('影响范围', [
            '用户在前端打开一个已删除的商品详情页时，会看到“系统内部错误”，无法区分是“商品没了”还是“系统坏了”',
            '502 会被前端与监控统一归类为服务端故障，造成告警噪音，掩盖真实的服务端异常',
        ]) +
        block('定位分析', [
            'litemall-admin-api/src/main/java/org/linlinjava/litemall/admin/web/AdminGoodsController.java 第 102-106 行',
        ]) +
        code('@RequiresPermissions("admin:goods:read")\n'
             '@RequiresPermissionsDesc(menu = {"商品管理", "商品管理"}, button = "详情")\n'
             '@GetMapping("/detail")\n'
             'public Object detail(@NotNull Integer id) {\n'
             '    return adminGoodsService.detail(id);        // ← 未判空，null 继续往下走\n}') +
        block('修复建议', [
            'Service 查询返回 null 后未判空即被后续逻辑取值，触发空指针，被全局异常处理器兜底成 502。',
            '建议在 detail 中增加判空：if (goods == null) return ResponseUtil.fail(GOODS_NOT_EXIST, "商品不存在");',
        ]) +
        para('附注：浏览器字段留空——本缺陷在接口层复现，不涉及浏览器差异。')
    ),
))


# ---------------------------------------------------------------- API 封装

def api(path, method='GET', data=None, token=None):
    hdr = {'Authorization': BASIC}
    if token:
        hdr['Token'] = token
    body = None
    if data is not None:
        hdr['Content-Type'] = 'application/json'
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=body, headers=hdr, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=40)
        return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, str(e).encode()


def get_token(account, password):
    s, b = api('/tokens', 'POST', {'account': account, 'password': password})
    if s not in (200, 201):
        raise SystemExit('取 token 失败 HTTP=%s %s' % (s, b[:300].decode('utf-8', 'replace')))
    return json.loads(b)['token']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true', help='只打印 payload，不提交')
    ap.add_argument('--only', nargs='*', help='只提交指定编号，如 --only 7 9')
    ap.add_argument('--account', default='admin')
    ap.add_argument('--password', default='5408lyT@')
    ap.add_argument('--token', default=None, help='直接给 token，跳过登录')
    args = ap.parse_args()

    todo = BUGS
    if args.only:
        todo = [b for b in BUGS if b['key'] in args.only]

    payloads = []
    for b in todo:
        payloads.append({
            'title':       b['title'],
            'project':     PROJECT,
            'execution':   0,
            'module':      MODULE,
            'pri':         b['pri'],
            'severity':    b['severity'],
            'type':        b['type'],
            'os':          OS,
            'browser':     '',
            'openedBuild': BUILD,
            'steps':       b['steps'],
        })

    if args.dry:
        for p in payloads:
            print('=' * 78)
            print('title     :', p['title'])
            print('severity  :', p['severity'], ' pri:', p['pri'], ' type:', p['type'],
                  ' module:', p['module'], ' build:', p['openedBuild'])
            print('steps 长度:', len(p['steps']), '字符')
            print('steps 前 300 字:', p['steps'][:300].replace('\n', ' '))
        return

    token = args.token or get_token(args.account, args.password)
    print('token =', token)
    print()

    results = []
    for p in payloads:
        # 防重复：先按标题查一遍
        s, b = api('/products/%d/bugs?limit=100' % PRODUCT, token=token)
        exist = None
        if s == 200:
            for x in json.loads(b).get('bugs', []):
                if x.get('title') == p['title']:
                    exist = x['id']
                    break
        if exist:
            print('[跳过] 已存在同标题单 #%s  %s' % (exist, p['title']))
            results.append((exist, p['title'], 'EXIST'))
            continue

        s, b = api('/products/%d/bugs' % PRODUCT, 'POST', p, token=token)
        try:
            d = json.loads(b)
        except Exception:
            d = {}
        if s == 201:
            print('[成功] #%s  %s' % (d.get('id'), p['title']))
            results.append((d.get('id'), p['title'], 'NEW'))
        else:
            print('[失败] HTTP=%s  %s' % (s, b[:400].decode('utf-8', 'replace')))
            results.append((None, p['title'], 'FAIL: %s %s' % (s, b[:160].decode('utf-8', 'replace'))))

    print()
    print('=' * 78)
    print('结果汇总：')
    for rid, title, st in results:
        print('  #%-6s %-10s %s' % (rid or '-', st, title[:60]))

    import io
    with io.open(r'C:\Users\李玉亭\WorkBuddy\2026-09-15-16-30-32\.workbuddy\zt_submit_result.json',
                 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print('\n结果已写入 .workbuddy/zt_submit_result.json')


if __name__ == '__main__':
    main()
