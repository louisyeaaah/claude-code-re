# Claude Code v2.1.287 · function hooks（插件 API）分析报告

**对象**：v2.1.287（`GIT_SHA:"3c446a1b98aceb99a6cdee0f84a8bea42f4a8937"`、`BUILD_TIME:"2026-10-01T16:02:06Z"`）里的 function hooks 子系统 —— 一套用 TS/JS 写插件、向主循环挂 hook 并绘制 UI 的 API。

**素材**：`work/assets/asset-044-asset.txt`（14 914 行，API 的 TypeScript 声明全文，头部写明 `// Claude Code function hooks: the plugin API's TypeScript declarations.`）／`asset-045-asset.txt`（2 232 行，`claude plugin test` 套件源码）／`asset-050-Function-hooks-the-long-form.md`（官方长文）／`asset-051-plugin-authoring.md`（官方 SKILL.md）／`raw/chunks2/*.js`（2 174 个模块）／`extracted/06-quirks.md`（早前一轮产出，下称「06 文档」）。引用格式：`work/assets/asset-044-asset.txt:4791`（行号）或 `raw/chunks2/0374__chunk-mphp7acd.js@1268258`（字节偏移，`grep -b -o` 定位）。证据分级：原文 = 直接读到的字节；推断 = 由符号名/调用点推出；未找到 = 明确没找到。

---

## 0. 结论速览

1. **这是真正接线的子系统，不是只写了类型。** 插件模块跑在独立 Bun Worker 里（`raw/chunks2/0374__chunk-mphp7acd.js@1268258`），worker 侧实现在 `raw/chunks2/0150__x-thepluginsenvironmentwasunloaded.js`。开关 `tengu_plugin_hooks_modules` **默认开**（`raw/chunks2/0329__chunk-110gm4an.js:24` 逐字 `var mUt=!0;`）。
2. **二进制里已带 10 个用这套 API 写的内置插件**（`raw/chunks2/1651…1661`，6 个导出 `registerPlugin`），含 `cc-plugin-claude-test`、`cc-plugin-telemetry`、`cc-plugin-sec-default`、`cc-plugin-mermaid`、`cc-plugin-agents-md`、`cc-plugin-responsive-mode`、`cc-plugin-mods-guide`。
3. **沙箱是 VM 级的、可验证的**：模块以 `vm.SourceTextModule` 在 `vm.createContext(nullProto, {codeGeneration:{strings:!1,wasm:!1}})` 里求值，全局恰好 13 个名字，`import()` 被运行时注入的 `importModuleDynamically` 拒绝 —— 逐条对上类型声明里「no DOM, no Node」那段。
4. **hook 点数比 06 文档记的 33 大一个量级**：33 只是 settings hook 的 `classic.*` 一档；本版按名可挂的事件共 **136** 个（引擎自有 43 + classic 33 + `$` 调用 60）。
5. **`$.ui.mount` 不在插件的 `$` 上，在测试的 `$` 上**（`asset-044-asset.txt:14039-14054`）；**`plugin test` 是早期访问且默认隐藏**（`earlyAccess:"hooksModules"`，`raw/chunks2/0766__chunk-ywkfhf88.js:1`），未受信工作区里模块被扣住直到用户接受信任（`raw/chunks2/1245__chunk-f5w4pbxy.js@9695`）。
6. **06 文档 §1.6 的空白已补上**：原文写「worker 的 IPC 协议、生命周期、超时策略**未找到**」（`extracted/06-quirks.md:581`）；本轮两半都找到了（§5.2）。

---

## 1. 这个 API 是什么

### 1.1 一个 mod 由什么构成

头部自述（`asset-044-asset.txt:1-7`，节选）：

```
// Claude Code function hooks: the plugin API's TypeScript declarations.
//
// EARLY ACCESS: this surface may change between releases without notice.
// Written by the engine each time it loads a mod from a folder the person
// owns, beside that mod as .claude-plugin/types/claude-code/index.d.ts; ...
```

作者侧看到的三文件形状（`asset-051-plugin-authoring.md:6-10`）：

```
WHERE TO WRITE IT. Write each mod in its own child folder of `${CLAUDE_DEV_MODS_DIR}`: `${CLAUDE_DEV_MODS_DIR}/<mod-name>/`, three files written directly:

- `.claude-plugin/plugin.json`: `{ "name": "<mod-name>", "version": "0.1.0", "description": "<one line>" }`
- `hooks/hooks.json`: `{ "modules": ["./register.tsx"] }`, one path, relative to that file
- `hooks/register.tsx` (or `.ts`): the hooks module, `export const register: Register = (on, options) => { ... }`, the type imported from `'claude-code'`
```

一个插件**只有一个** hooks 模块，导出 `register(on, options)`（`asset-050-Function-hooks-the-long-form.md:14`）；用了 `$.state` 就多一个 `types/index.d.ts` 契约文件（`asset-051:12`）。**测试夹具反过来证实这个形状**：`claude plugin test` 现造插件时写的就是这三个文件（`raw/chunks2/0769__x-CHILD_ARGV_LENGTH.js@13818` 附近的 `ue(e,n,r)`）—— `plugin.json` 只写 `{"name":"…"}`，`hooks.json` 写 `{"modules":["./register.js"]}`，第三个文件写 `export function register(on) { … }`。

### 1.2 manifest 长什么样

**`hooks/hooks.json`** 的 zod schema（`raw/chunks2/0055__chunk-hrhfcbdv.js@131757`）逐字给出四个字段与两条硬约束：

```
hooks:    "The hooks provided by the plugin, in the same format as the one used for settings"
modules:  max 1 — "hooks.json `modules` names one hooks module per plugin; a second entry is refused"
          "The hooks module: one path, relative to this hooks.json, of a module exporting register(on).
           The module, and every file it imports from the plugin, is named like code (...)
           and is an ES module whatever its suffix. What it hooks and calls is read from its source
           before it loads; `claude plugin validate` shows the result."
surface:  'hooks.json `surface` is gone: name the module in the Client element, `Client({ module: "./board.tsx", key })`'
```

refine 规则：``"hooks.json must have `hooks` (the hook matchers) or `modules` (hooks modules), or both"``。

**`plugin.json`** 的字段（`asset-050:62`、`asset-051:8/12`、`asset-044-asset.txt:7153-7165`）：`name`、`version`、`description`、`types`（该插件给 `$` 加的名词的契约 `.d.ts`）、`dependencies`（依赖插件的契约会被铺到 `.claude-plugin/types/<plugin>/index.d.ts`）、`userConfig`（用户填的选项）、`hooks`、`mcpServers`、`evals`。选项的落点与校验（`:7153-7160`）：来自 `userConfig` 声明的字段、默认值已填，存在 `settings.json` 的 `pluginConfigs[<plugin>].options`（敏感项进 secure storage），**在模块加载前**按声明的 `type` 校验；必填项缺值就加载失败并指名该字段。

### 1.3 hooks 模块如何被加载

**（a）运行时环境：独立 Worker。** 宿主侧工厂逐字：

```js
// raw/chunks2/0374__chunk-mphp7acd.js@1268258
function geo(){ let e=new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT*vts),
                    n=new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT*Ets);
  return { worker: new Worker(Nvt(), Ovt(e,n)), stamp: new Int32Array(e), marks: new Int32Array(n) } }
```

worker URL 由 `Nvt()`（`@1267204`）解析：打包后取构建常量 `HOOKS_WORKER_URL`（`/$bunfs/root/src/plugins/functionHooks/hooks-worker/hooks-worker.js`），开发态退化为 `new URL("../../../hooks-worker/hooks-worker.ts", import.meta.url)`。日志逐字 ``"hooks worker spawned (one for every plugin)"``（`@1728382`）——**一个进程一个 worker，服务所有插件**。

**（b）允许的文件后缀：8 个**（`raw/chunks2/0055__chunk-hrhfcbdv.js@75380`）：`pnr={".ts":"ts",".tsx":"tsx",".jsx":"jsx",".js":"js",".mjs":"js",".cjs":"js",".mts":"ts",".cts":"ts"}`，`var oZe=Object.keys(pnr);` —— 键集合逐字是 `.ts .tsx .jsx .js .mjs .cjs .mts .cts`，与散文描述一致（`asset-044-asset.txt:19-21`）：「The module, and every file it imports from the plugin, is named `.ts`, `.tsx`, `.jsx`, `.js`, `.mjs`, `.cjs`, `.mts` or `.cts`（a file named otherwise is not loaded）」。

**（c）ES module，无 `require`，`import()` 不加载**（`asset-044-asset.txt:21-23`）：

```
// otherwise is not loaded) and is an ES module whatever its suffix: there
// is no `require`. A file of the plugin is imported with an `import`
// declaration. A module holding `import()` does not load.
```

两处独立实现：**静态扫描** `raw/chunks2/0374__chunk-mphp7acd.js` 的 `var UIe=/\bimport\s*\(/;`（模块与它 linked 的每个文件都过一遍）；**运行时兜底** `raw/chunks2/0146__chunk-hhxhpvxp.js@152175` 注入一个永远抛的 `importModuleDynamically`：

```
'import() is not available: a hooks module imports its own files ' +
  'with an import declaration',
```

再以 `new Kn.SourceTextModule(vJn,{context:o,identifier:S7e,importModuleDynamically:c})`（`0146@152847`）求值。

**（d）沙箱约束：逐条核实。**

| 原文声称 | 出处 | 核实 |
|---|---|---|
| no DOM, no Node | `:19`、`:13706-13707` | ✅ 强制。`raw/chunks2/0146__chunk-hhxhpvxp.js@206807-206945`：`var Lf=Object.freeze({strings:!1,wasm:!1}); var Ff=Object.freeze({codeGeneration:Lf}); function mzo(){let e=ip(),t=$f.createContext(e,Ff); …}`，而 `ip=()=>Object.create(null)`（`0146@158956`）—— 上下文是 null 原型对象，宿主只填 13 个名字 |
| no code generation（`eval`/`new Function` 抛，无 `WebAssembly`） | `:13707-13709` | ✅ 强制，就是上面 `codeGeneration:{strings:!1,wasm:!1}` 这两个 `vm` 选项 |
| 全局只有 `h`、`Fragment`、JSX 命名空间与 web API | `:15-19`、`:13714-13838` | ✅ 精确匹配。`0146` 的引导源码里 `define('…')` 恰好 13 次：`AbortSignal, AbortController, TextEncoder, TextDecoder, URL, URLSearchParams, atob, btoa, structuredClone, crypto, performance, h, Fragment` |
| 没有 timers（hooks 用 `$.clock`，surface 模块用 `surface.every`） | `:13711-13712` | ✅ 13 个名字里没有 `setTimeout`/`setInterval` |
| no fs / no network / no process（测试环境同款） | `:30` | ✅ API 事实：13 个全局里没有任何 I/O，文件/网络/进程只能走 `$` |

**（e）surface 模块（`Client`）的环境**：同一套沙箱加一个 `console`。`raw/chunks2/0764__chunk-ybjnt5d8.js@4015` 逐字：`let {sandbox:u,context:f}=mzo()` … `Object.assign(u,{console:KGo(S,`[${c}] surface`)})`，与 `asset-044-asset.txt:13710-13712` 吻合。

### 1.4 加载的门

1. **总开关**：`raw/chunks2/0329__chunk-110gm4an.js` 全文 25 行，逐字：

```js
var RYe="tengu_plugin_hooks_modules";
var mUt=!0;
var YJ=()=>k(RYe,mUt);
var _Ue=()=>YJ()&&!Gr("hooks")&&!yr();
var zgn=()=>_Ue()&&!Wb()&&!Ty();
```

`mUt=!0` = **默认开**；`Gr("hooks")`、`yr()`、`Wb()`、`Ty()` 是 `disableAllHooks`/`allowManagedHooksOnly`/策略一类地面闸门（别名见 `raw/chunks2/0799__x-HOOKS_MODULES_FLAG.js`：`canLoadUserHooksModules`、`canLaunchLoadUserHooksModules`）。

2. **工作区信任**：未受信会话里模块被扣住直到用户接受。`raw/chunks2/1245__chunk-f5w4pbxy.js@9695` 的 post-trust 回调里逐字调用 `loadHooksModulesHeldForTrust(T,x)`；`@8155` 的分支文案是 ``"continuing as an untrusted session (hooks and project settings env stay off)"``。
3. **tier 与顺序**：五个 tier，外层权限更大 —— `asset-044-asset.txt:11875`：`const TIERS: readonly ["prepend","user","append","builtin","core"];`，注释（`:11857-11864`）说 `prepend`/`append` 是管理员列的托管插件，`user` 是人装的，`builtin` 是编进二进制的，`core` 是引擎最内环。
4. **`plugin.register` 否决**（`asset-044-asset.txt:7204-7221`）：核心回 `{ allow: true }`，任何上方 hook 可回 `{ refuse: reason }`，模块就不加载 ——「no step, no hooks, no tools or commands」。

**扫描是精确的、且是准入依据**（`asset-044-asset.txt:7223-7269`，`PluginRegisterUses`）：宿主在加载前从源码读出注册的模式、`$` 上被调用的 `noun.method`、`$.env` 的字面量变量名、`$.state` 的 `{plugin,key}` 字面量。注释：「Exact, since a module that spells `on`, `$`, `$.env` or a `$.state` reference other than literally does not load.」运行时确实按这份清单拒绝：`0374@1274791` 的 `Wne()` 抛 ``"its hooks module does not call it (host rule; the scan lists …)"``。

---

## 2. 能力面

### 2.1 `Register` / `On` / `EngineInterface`

```ts
// asset-044-asset.txt:8641
export type Register = (on: On, options: PluginOptions) => unknown;
// asset-044-asset.txt:4854-4856
export type HooksModule = { register: Register };
// asset-044-asset.txt:6319-6322
export type On = {
    <P extends Pattern>(pattern: P, hook: NoInfer<HookFor<P>>): Registration<HookFor<P>>;
    <P extends Pattern, const M extends MatcherFor<P>>(pattern: P, matcher: M, hook: NoInfer<MatchedHook<P, M>>): Registration<MatchedHook<P, M>>;
};
```

`On` 的语义（`asset-044-asset.txt:6308-6318`）：`pattern` 是一个事件名、命名空间通配（`classic.*`）、全部（`*`）或排除（`!tool.*`）；同一事件的多个注册按加载顺序嵌套，**先注册的在外层**；重复注册抛错。`Registration.catch`（`:8651-8660`）给失败的 hook 一次宽限重试，一个注册只能挂一个。

`EngineInterface`（`:4192-4193`）是个**空接口** `extends CoreEngineInterface {}` —— 供插件用 declaration merging 往 `$` 加名词；插件名词不能是 `tool`/`session`/`ui` 这些引擎自有命名空间（`:7147-7151`）。`HookFor`（`:4840`）把 `*`、单事件、glob 收敛到**一个**泛型签名，注释解释了为什么不用 overload 集合：`as an overload set the language service offers no tool-name completions inside e.tool === "`。

### 2.2 全部 hook 点

事件名 = `CoreEventOf & NounEventOf`，而 `CoreEventOf = EngineEventOf & ClassicEventOf & OpEventOf`（`:3397`）。本版**没有任何插件名词被声明**，`NounEventOf` 为空（`:6275`：「Empty until a plugin declares a noun」）。

| 档 | 数量 | 定义位置 | 例 |
|---|---|---|---|
| 引擎自有事件 `EngineEventOf` | **43** | `:3714-4192` | `tool.call`、`ui.render`、`session.append`、`prompt.compose`、`turn.step`、`engine.create` |
| classic（settings hook）`ClassicEventOf` | **33** | `:1076-1083`，联合在 `:4842` | `classic.PreToolUse`、`classic.Stop`、`classic.SessionStart` |
| `$` 调用事件 `OpEventOf` | **60** | `:6381-6710` | `fs.write`、`http.fetch`、`clock.every`、`tool.register`、`ui.open` |
| 插件名词事件 `NounEventOf` | **0**（本版） | `:6280-6282` | — |
| **合计可按名挂** | **136** | | |

**流式事件只有两个**（`:11445`）：`export type StreamingEventName = 'turn.step' | 'process.spawn';` —— 其 hook 必须是 `async function*`（`:11447-11453`、`asset-050:29-30`）。

43 个引擎事件（`:3723-4178`，声明顺序）：`tool.call` `tool.check` `ui.render` `ui.resolve` `ui.press` `ui.input` `ui.select` `ui.message` `ui.scroll` `ui.focus` `agent.offer` `agent.spawn` `prompt.submit` `prompt.fill` `prompt.suggest` `prompt.edit` `prompt.section` `prompt.context` `prompt.compose` `prompt.attachment` `tool.describe` `command.run` `command.describe` `config.set` `config.describe` `telemetry.log` `telemetry.mark` `skill.prompt` `attribution.text` `session.start` `session.receive` `session.append` `session.send` `session.compact` `session.attach` `session.detach` `session.measure` `session.end` `plugin.register` `turn.start` `turn.step` `turn.complete` `engine.create`。

33 个 classic 事件（`:4842` 的 `HookInput` 联合，按声明顺序）：`PreToolUse` `PostToolUse` `PostToolUseFailure` `PostToolBatch` `PermissionDenied` `Notification` `UserPromptSubmit` `UserPromptExpansion` `SessionStart` `SessionEnd` `Stop` `StopFailure` `SubagentStart` `SubagentStop` `PreCompact` `PostCompact` `PreModelSwitch` `PostModelSwitch` `PermissionRequest` `Setup` `TeammateIdle` `TaskCreated` `TaskCompleted` `Elicitation` `ElicitationResult` `ConfigChange` `InstructionsLoaded` `WorktreeCreate` `WorktreeRemove` `CwdChanged` `FileChanged` `DirectoryAdded` `MessageDisplay`。

60 个 `$` 调用事件（`:6386-6700`）：`model.complete/classify/fork`、`audio.play/speak`、`mcp.call/connect`、`session.cwd/root/model/turns/id/messages/repo/surface/surfaces/authorize/usage/version`、`turn.abort`、`prompt.read`、`tool.list/register`、`command.list/register`、`config.list`、`agent.list/register`、`ui.toast/status/log/notice/invalidate/open/close/panes/copy/blit`、`fs.read/write/list/exists/stat/ancestors`、`store.get/set/delete/keys`、`state.get/set`、`clock.now/sleep/after/every`、`http.fetch`、`process.run/spawn`、`settings.read`、`env.get/set`。

**为什么 `$` 的调用也算事件**（`:6373-6379`）：「The calls on `$` the host serves, as events … every one is hookable by name and by `on("*")`. A hook above the caller passes it on, rewrites it, refuses it with `{ deny }` or answers with `{ value }`; core is the host's implementation. The calling hook alone is skipped, and `next.origin` names the caller.」——**一个插件调 `$` 时别的插件能拦它**。

### 2.3 `$` 上的命名空间与方法

`CoreEngineInterface`（`:2130-3385`）共 **21 个命名空间**：

| 命名空间 | 方法 / 成员 | 位置 |
|---|---|---|
| `plugin` | `name`、`root` | :2134-2143 |
| `ui` | `notice` `invalidate` `blit` `resolve` `log` `ask` `toast` `status` `open` `close` `panes` `scroll` `focus` `copy` | :2148-2365 |
| `model` | `complete` `fork` `classify` | :2369-2438 |
| `audio` | `play` `speak` | :2439-2474 |
| `mcp` | `call` `connect` | :2475-2515 |
| `session` | `messages` `cwd` `root` `model` `turns` `id` `repo` `surface` `surfaces` `usage` `version` `append` `authorize` | :2516-2695 |
| `turn` | `abort` | :2696-2714 |
| `prompt` | `read` `fill` | :2715-2780 |
| `tool` | `list` `register` | :2781-2833 |
| `command` | `list` `register` | :2834-2874 |
| `config` | `list` | :2875-2905 |
| `telemetry` | `log` `mark` | :2906-2943 |
| `agent` | `list` `register` | :2944-2996 |
| `fs` | `read` `write` `list` `exists` `stat` `ancestors` | :2997-3117 |
| `store` | `get` `set` `delete` `keys` | :3125-3151 |
| `state` | `get` `set` | :3158-3191 |
| `clock` | `now` `sleep` `after` `every` | :3200-3239 |
| `http` | `fetch` | :3243-3265 |
| `process` | `run` `spawn` | :3272-3328 |
| `settings` | `read` | :3337-3353 |
| `env` | `get` `set` | :3362-3384 |

**能力边界（原文要点）**：`$.fs` 读写超 4 MiB 拒绝、网络位置拒绝、保留系统 errno（`:2994-2995`）；`$.http.fetch` 走宿主而非插件自己的网络，`auth` 句柄只走 https 且只到一方主机（`:3245`、`:3249-3250`）；`$.process` **CLI only**，无 shell、默认 30 s、最多 10 分钟、每流前 4194304 字节（`:3267`、`:3274-3285`）；`$.settings.read` **read only**（`:3330-3331`）；`$.env.get/set` 的变量名必须是字符串字面量，所以模块读写了哪些变量能从源码读出（`:3358-3360`）；`$.session.messages` 最多 4096 条（`:2527`）；`$.session.append` 只能写文本块、只能追加插件自己发起的行（`asset-050:115`）。
### 2.4 hook 的输入输出契约与预算

- **签名** `($, e, next)`（`:4489-4494`）：`$` 冻结且每次调用同一对象；`e` 逐层冻结（改写要传副本）；`next` 是「链的剩余部分」，经 `$` 发起的新调用会跳过本 hook 而跑其他所有 hook（递归跳闸）。
- **`e` 是纯数据**：`asset-044-asset.txt:4465-4467`「Plain data, frozen to every depth.」跨 worker 传输时逐条 clone，非纯数据直接抛（见 §5.3）。
- **`next` 的成员**（`:6094-6167`）：`next(e)`、`next.to(e, tier)`（跳到自己 tier 与目标 tier 之间）、`next.signal`（dispatch 被放弃时 abort）、`next.is(pattern, e)`、`next.event`、`next.origin`（谁发起：插件名 + tier；引擎读作 `{plugin:"engine",tier:"core"}`）、`next.trace`（链上每一环的结果）、`next.budget`。
- **预算**（`:4782-4808`）：

```ts
readonly ms: 10_000;        // 每次 dispatch 给这个 hook 自己的时间
readonly catchMs: 1_000;    // .catch 处理器的宽限
readonly lingerMs: 5_000;   // next.signal abort 后还能跑多久
```

关键语义（`:4775-4777`）：「Each bounds the hook's OWN time: the clock stops while a `next(e)` call or any `$` call of the hook's is in flight（a `$.clock` wait excepted）」。超预算 = 该 hook 缺席（除非有 `.catch`），链继续。失败形状 `HookFailure.kind` 是 `'throw' | 'timeout'`（`:4818-4830`）。

---

## 3. UI 模型

### 3.1 元素从哪来：`$.ui.resolve(e)`，不是全局

`asset-044-asset.txt:24-26` 明说元素不是全局：

```
// The elements a
// render hook draws with (`Box`, `Text`, `Button`, ...) are not globals:
// they come from the surface's table,
//   const { Box, Text } = $.ui.resolve(e)
```

`$.ui.resolve` 的语义（`:2195-2210`）是要点：**它是一次读，不是一次 dispatch** ——「the engine ran `ui.resolve` (the other hooks, then core) at load, per surface and component」。`e.surface` 被收窄时给出那张表，否则给并集（所以同名元素能通过类型检查）。元素是「从 props 到冻结纯数据元素的构造函数」（`:3550-3558`）：`<Box gap={1}>…</Box>` 编译成 `h(Box,{gap:1},…children)`，表里的构造函数**就是** JSX 标签；`h` 与 `Fragment` 是环境里仅有的两个 JSX 全局（`:13726-13735`）。

### 3.2 四个 surface 的表

总述在 `:3568-3574`，四张表在 `:3576-3643`：

| surface | 元素 |
|---|---|
| `terminal` | `Box` `Text` `Button` `Input` `Select` `Link` `Code` `Markdown` `Client` `Raster` `Image` |
| `desktop` | 上述去掉 `Raster`/`Image`，加 `Svg` |
| `mobile` | `Box` `Text` `Button` `Svg` `Link` `Code` `Markdown`（**无 `Input`/`Select`**；原文：mobile app 还没画字段，不是设备或协议的限制） |
| `vscode` | desktop 表去掉 `Client`（原文：`ui_client_module`、`ui_client_press`、`ui_message` 目前不认 surface） |

`RenderSurface = 'terminal' | 'desktop' | 'mobile' | 'vscode'`（`:9663`）。可画的**组件** 15 个（`:8680`）：`AskUserQuestion` `UserMessage` `AssistantMessage` `ToolUse` `ToolResult` `ToolGroup` `ToolProgress` `CommandOutput` `Spinner` `TurnDuration` `InfoNotice` `SessionMode` `PromptHint` `AbovePrompt` `Pane`。权限对话框**不在**其中 —— 引擎独占绘制，插件只能用 `$.ui.notice` 补一行（`:8676-8678`）。绘制返回 `RenderElement`（`:8682-8690`）：「a plain-data tree of elements … Props are an allowlisted subset of Ink's Box/Text props … a tree with any other prop fails validation **as a whole** and the engine's own component is drawn with the original props.」

### 3.3 `$.ui.mount` 的语义（在测试侧）

**`$.ui.mount` 不在插件的 `$` 上。** `CoreEngineInterface.ui` 的方法表（`:2148-2365`）里没有 `mount`；它只出现在 `claude-code/testing` 的 `Engine` 类型里：

```ts
// asset-044-asset.txt:14039-14053
export type EngineMount = {
    mount: <P extends RenderSurface, C extends RenderComponent>(target: MountTarget<P, C>) => Promise<Mounted<P, C>>;
};
```

语义（`:14040-14052`）：「Raises the plugins' drawing of the component on the surface and holds it, as that surface showing the instance does. Resolves once the tree validated and every `Client` in it drew once.」`surface` 必须显式给（**没有默认值**，`asset-045:1358-1366` 的运行时文案：`${RENDER_SURFACE_NAMES.join(', ')}; there is no default`）；返回的 `Mounted` 按该 surface 的表裁掉不存在的动作（`:14500-14510`：「no `input` on `mobile`, no `key` on `vscode`」）。头部注释的范式（`:45-58`）：

```ts
test('notes add up on every surface that takes input', async $ => {
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ plugin: 'notes', surface, ...BAND })
    await ui.input({ key: 'new', text: 'milk' })   // expect((await ui.find({ key: 'count' }))?.text).toBe('1 note')
```

`:41-43` 给这套测试定性：它只考插件的 hook、各 surface 规则下返回的树、以及它自己的 `Client` 模块，「**never a surface's paint** (Ink's, the desktop page's)」。

### 3.4 绘制契约的硬点

`Pane` 是唯一由插件主动开的组件（`$.ui.open`，`:2270-2291`）：**问了人**（人敲的命令/提示/按键）任意宽度放置，**没问**要 ≥144 列（问过一次的 110 列），低于此**等待不画**。`Button` 是 leaf，`onPress` 闭包留在插件环境里，宿主只持句柄（`:8691-8698`）。`Raster`/`Image` 是 terminal 独占，`$.ui.blit` 不重跑 render 就能重绘（`:2174-2194`）。渲染 hook 里**不能写** `$.state`（`:3175-3181`「Refused while a `ui.render` hook draws」），重绘靠 `$.ui.invalidate` 或 `state.get` 的订阅（`:2154-2156`）。

---

## 4. 测试与校验

### 4.1 `claude-code/testing` 契约

声明自 `asset-044-asset.txt:13842` 起，导出五个东西：

```ts
export const describe: (name: string, body: () => void) => void;   // :13928
export const test: (name: string, ...rest: TestRest) => void;      // :14855
export const expect: Expect;                                      // :14125
export const mock: Mock;                                          // :14441
export const tier: (tier: PluginTier) => void;                    // :14906
```

- **`test`**（`:14844-14855`）：「One test: it passes when its body returns or resolves, and fails when it throws, rejects or outlasts its time（**5000 ms**, or `timeoutMs`）. The body gets the engine's `$` and an `on` whose hooks sit beneath every plugin」。`TestBody = ($: Engine, on: On) => unknown`（`:14864`），`TestOptions = { plugins?, timeoutMs?, options? }`（`:14872-14887`）。
- **`tier`**（`:14900-14906`）：「Says which tier the plugin under test loads in, **once, at the top of the file**: `prepend`, `user` (when unsaid), `append` or `builtin`.」
- **`describe`**（`:13921-13928`）：「its body runs **at once**, while the file loads.」
- **`expect`**：`Expecting & Matching`（`:14116`），断言表自 `:14215`；`AsyncMatchers` 让同一组检查也作用于 promise（`:13880-13886`）。
- **`$.classic`**：测试的 `$` 上还有 `classic`（`:14001-14003`），如 `await $.classic.SessionStart({ source: 'clear' })`；`PreToolUse` 例外，它骑在 `$.tool.call` 上（`:13896-13996`）。测试的 `$` 另有 `ui.press`/`ui.input`/`ui.select`/`mount`（`:13979`）。
### 4.2 `mock` 的 clock / store / env 语义

```ts
// asset-044-asset.txt:14403-14431
export type Mock = {
    clock: (on: On, options?: MockClockOptions) => MockClock;
    store: (on: On, entries?: Readonly<Record<string, unknown>>) => void;
    env: (on: On, variables: Readonly<Record<string, string>>) => void;
};
```

三者**都不是**替换全局，而是在测试自己的 `on` 上注册 hook 向下回答（`:14400-14401`：「The world beneath the plugins, mocked noun by noun: each member registers hooks of the test's `on`, visible where the test calls it.」）。asset-045 的实现逐字：

```js
// asset-045-asset.txt:1112-1118（mockClock）
on('clock.now', () => ({ value: clock.now() }));
on('clock.sleep', hold); on('clock.after', hold); on('clock.every', hold);
// :1187-1190（mockEnv）
on('env.get', ($, e) => { const value = held[e.name]; return { value: typeof value === 'string' ? value : undefined }; });
// :1204-1213（mockStore）
on('store.get', ($, e) => ({ value: held.get(e.key) }));   // set / delete / keys 同理
```

`MockClock` 的五个动作（`:14447-14491`）：`now()`、`advance(ms)`（按到期顺序逐个唤醒，每次唤醒后让事件循环安定）、`set(ms)`、`settle()`（= `advance(0)`）、`sleep(ms)`。被挂起的等待在 dispatch abort 时丢弃，超过 10 s 真实时间就放行（当作 hook 超时）。实现里单次推进有 10 000 次上限（`asset-045:1016`），到了就抛「an interval shorter than the advance?」。

### 4.3 `claude plugin test` 做什么

命令表（`raw/chunks2/0766__chunk-ywkfhf88.js:1`）：

```js
test:{usage:"plugin test [dir]",description:"Run a mod's tests",earlyAccess:"hooksModules"}
```

`earlyAccess` 决定它是否出现在帮助里（同表 `plugin eval` 用 `earlyAccess:"pluginEval"`）。注册处（`raw/chunks2/1435__x-registerPluginCommands.js@20608`）是 `n.command("test [dir]",{hidden:!0})`，非 `claude plugin test` 拼法打印 ``"claude plugin test: not run from this spelling. Use `claude …`"``。入口分派（`raw/chunks2/0006__x-inntypeofn.js@5164`）先算拒绝理由，非空就 `process.exitCode=1` 返回，否则 `import("/$bunfs/root/chunk-01653fey.js")` 取 `pluginTestMain` 跑 `t.slice(2)`：

```js
let [{loadFastPathPolicy:e},i,{pluginTestRefusal:o}]=await Promise.all([...]),
    s=o({helperError:await e(l),isRolloutOn:i.hooksModulesRolloutOn(),canLoadUserModules:i.canLoadUserHooksModules()});
if(t[2]==="--file"&&s!==void 0){ ... REPORT_MARK ... }
if(s!==void 0){ process.stderr.write(`claude plugin test: ${s}\n`),process.exitCode=1; return }
```

被拒的两种理由（`raw/chunks2/0768__chunk-9d5bhh5t.js`）：``"hooks modules are turned off in this process: the rollout switch served off, and a plugin's tests run only while it is on"`` / ``"hooks modules are turned off here (disableAllHooks, allowManagedHooksOnly or a policy)"``。

**测试套件本身**（`raw/chunks2/0769__x-CHILD_ARGV_LENGTH.js`，即 bun 的 `chunk-01653fey`）：`test()`/`describe()`/`tier()` 只往 `collector` 塞 case（`asset-045:10-59`），`collector.close()` 后不许再注册；`run()` 顺序跑完每个 case 并 `JSON.stringify`（`asset-045:1893-1901`），结果以 `REPORT_MARK = "claude-plugin-test-report "` 打头（`raw/chunks2/0765__chunk-vvhdd9fn.js:11`）；每个 case 先 `openSeat(plugins, tier, options)` 开「座位」，再 `timed(body, timeoutMs)` 加超时（`asset-045:1819-1828`、`1867-1888`）。座位把引擎面交出来：`openSeat` 调 `host.open` / `host.call` / `host.mount` / `host.pressed` 等（`asset-045:1573-1617`）。

- **`claude-code/testing` 是虚拟模块**：`re="claude-code/testing"`，在 `vm` 上下文里用 `new ht.SourceTextModule(...)` 求值（`raw/chunks2/0769__x-CHILD_ARGV_LENGTH.js@36000-37000`）；套件自身模块根是 `he="@/src/plugins/functionHooks/plugin-test/testing"`，越界 import 被拒：``"the kit's ${n} imports ${e}, which is outside the kit"``。
- 套件必须被显式安装：`asset-045:921-922` —— ``"'claude-code/testing' runs under claude plugin test; nothing here installed it"``。

### 4.4 `claude plugin validate` 做什么

命令表逐字（`raw/chunks2/0766__chunk-ywkfhf88.js:1`）：

```js
validate:{usage:"plugin validate <path>",description:"Validate a plugin or marketplace manifest, or the skills, agents, and commands in a directory"}
```

两个选项在注册处（`raw/chunks2/1435__x-registerPluginCommands.js@13750`）：`--strict`（「Treat warnings as errors (exit 1). Use in CI …」）与 `--json`。定位见 `asset-044-asset.txt:8-11`：「reads a plugin's manifest and its hooks module's source the way the engine will and reports what the module hooks and calls and everything the engine would refuse, before any session loads it.」

报告内容 = `PluginRegisterUses`（`:7230-7269`）：`events`（`on(...)` 写的模式，按注册顺序）、`calls`（`noun.method`，排序去重）、`env.reads`/`env.writes`、`state.reads`/`state.writes`。它同时校验 types 契约（`asset-050:62`：「`claude plugin validate` checks the contract」）与 `$.state` 的键是否在契约里（`asset-051:12`）。

---

## 5. 与主 harness 的关系

### 5.1 在产物里的位置

构建常量漏出了源码路径（`raw/chunks2/0374__chunk-mphp7acd.js@1267204`）：

```js
HOOKS_WORKER_URL:"/$bunfs/root/src/plugins/functionHooks/hooks-worker/hooks-worker.js"
```

同族字符串随版本常量在 `raw/chunks2/1330__x-update.js` 等处重复（它被打进每个模块共用的那个冻结字面量）。类型声明引用的源路径也都是 `src/plugins/functionHooks/...`，如 `raw/chunks2/0055__chunk-hrhfcbdv.js@555636` 的 `"src/plugins/functionHooks/types/render/render-component.ts"` 与套件的 `@/src/plugins/functionHooks/plugin-test/testing`。**推断**：`src/plugins/functionHooks/` 是这个子系统的源码根。

### 5.2 worker 的启动与两半协议

**宿主半**（`raw/chunks2/0374__chunk-mphp7acd.js`）：`geo()` 造 `Worker` + 两块 `SharedArrayBuffer`（`stamp`/`marks`，跨线程进度戳，`@1268258`）；全局句柄 `$vt()` 暴露 `setSpawner / spawnWorker / setReloader / reloadModule / setLoadedNotifier / notifyLoaded`；**一个 worker 服务所有插件**（`@1728382`）；心跳 `ping`/`pong` 超时判定「wedged (a hook spinning without yielding)」→ 归因到具体插件 → 卸载它 → 重启 worker（`UO()` `@1705533`、`$Pt()`、`FPt()`）；`OAe()`（`@1264941`）加载一个模块，`WIe()` 热重载，`hB()` 卸载一组，`PPt()` 是整批装载状态机。

**worker 半**（`raw/chunks2/0150__x-thepluginsenvironmentwasunloaded.js`，全文 11 939 字节）：`import{workerData as S}from"worker_threads"`（`@4895`），`self.onmessage` 收宿主消息，`K(self)` 收尾（`@11930`）。协议逐条：

| 宿主 → worker | worker → 宿主 |
|---|---|
| `ping` `load` `unload` `build` `resolve` `call` `dispatch` `dispatch_stream` `stream_pull` `stream_close` `next_result` `next_error` `next_step` `abort` `press` `press_release` | `pong` `loaded` `load_error` `built` `built_error` `resolved` `resolve_error` `call_result` `call_error` `result` `error` `stream_step` `press_result` `press_error` `log` `hook_failed` `unhandled` |

worker 与单个插件环境之间还各走一条 `MessagePort`（`0150` 的 `case"load"` 分支拿到 `port`），端口上的消息是 `next` `next_abort` `next_pull` `next_close` `op` `op_abort` `op_pull` `op_close`（worker → 插件）与 `flush` `op_result` `op_abort`（插件 → worker）。`op` 就是 `$.<noun>.<method>` 的远程调用，参数走 `args`、结果走 `value`。

**这填补了 06 文档的空白。** `extracted/06-quirks.md:581` 原文：

```
2. **hooks-worker.js 本体**：只有构建期路径常量（`chunks/c0682.js @32968`）与测试/作者侧代码（`chunks/c1409.js`、`chunks/c3083.js`）。worker 的 IPC 协议、生命周期、超时策略**未找到**——"存在"是一手证据，"如何工作"未知。
```

现状：**worker 本体仍未作为可 carve 模块出现在 `raw/chunks2/`**（它是 bun 打包进 `$bunfs` 的独立入口，只被 URL 引用）—— 这一层仍未找到；但 **worker 侧实现代码找到了**（`0150`），**宿主的 IPC、生命周期与超时策略也找到了**（`0374`）。结论从「存在」升级为「机制清楚」。

### 5.3 插件 hook 的输入输出契约

跨 worker 的 I/O 契约可以精确到「什么过线、什么不过线」：

- **事件载荷**：宿主把 `e` 序列化进 `dispatch` 消息；worker 侧 `d.dispatch({id,event,payload,environments,leftOut,origin,raise,floors,cutAt}, …)`。
- **返回值**：worker 回 `{type:"result",id,…}`；不可克隆时报 ``"result not cloneable: …"``。
- **流式**：`dispatch_stream` / `stream_pull` / `stream_step` / `stream_close`，chunk 同样必须纯数据（``"a chunk that is not plain data: …"``）。
- **`next` 的远程往返**：worker → 宿主 `{type:"next",id,nextId,argument,floors}`，宿主回 `next_result`/`next_error`；abort 走 `{type:"next_abort",…}`。
- **`$` 调用**：worker → 宿主 `{type:"call",callId,environmentId,call,callers}`，宿主回 `call_result`/`call_error`；错误文案里带 ``"$.${a.name}.${a.method} returned a value that is not plain data"``。
- **准入是「扫描即白名单」**：调用 `$.X` 前先查该插件的扫描结果（`0374@1274791` 的 `Wne()`），不在 `calls` 里直接拒绝。
- **少数操作只能插件调**：`0374@1274791` 附近的 `var aoe=new Set(["ui.open","ui.toast","ui.status","ui.log","ui.notice","ui.ask","tool.register","command.register","agent.register","prompt.fill","prompt.suggest"]);` —— 这一组在底层 host check 目录里被特殊对待（`D=aoe.has(e)` 决定是否对参数做一次变换）。**推断**：这是请求/UI 型操作的白名单。
- **同线程旁路**：`0374@1712522` 有 `a.CLAUDE_CODE_HOOKS_SAME_THREAD?"same-thread":"worker"`；`xPt()` 用它判断能否复用已加载模块（`@1712575`）。给内置插件/调试用，不是普通插件路径。
- **强制重载的事件**：`0374@1710573`：`var wPt=["engine.create","plugin.register"];` —— 模块挂这两个事件之一就不能增量复用，必须整批重折。

### 5.4 与 06 文档那 33 个 hook 事件的关系

**是子集关系，不是同一个东西。**

- 06 文档说的 33 个，是 **settings hook**（`hooks` 配置里的 command/http/mcp_tool/script/prompt/agent）的事件集，来自 `hook_event_name` 的联合。本版它就是 `asset-044-asset.txt:4842` 的 `HookInput` 联合，**数出来正好 33 个**。
- function hooks 把它们**原样暴露成 `classic.<Event>`**（`:1066`：``export type ClassicEventName = `classic.${ClassicHookEvent}`;``），`e` 就是那个 hook 在 stdin 上收到的东西（`:1069-1074`）。`classic.PreToolUse` 形状不同：`e` 是 `ToolCallEnvelope`。
- 链的顺序（`:1072-1073`）：「The chain is [managed settings hooks, …hooks modules, the other settings hooks as core], so a managed block ends it above every module.」**托管 settings hook 最外，插件模块居中，其余 settings hook 作为 core 在最内。**
- 在这 33 之外，function hooks 又加了 **43 + 60 = 103** 个新事件点（§2.2）。
- 两条 06 文档记的硬细节在 function hooks 里也成立：`classic.PreToolUse` 不能作为独立调用（`raw/chunks2/0769__x-CHILD_ARGV_LENGTH.js@~14300` 逐字抛 ``"$.classic.PreToolUse is no call on the engine's $: the engine raises it inside tool.call, so a test calls $.tool.call"``）；matcher 能对 `e.props.origin.kind` 这类字段收窄（`asset-050:103`）。
- 06 文档 §1.6 记的灰度开关本次逐字确认，只是当时没读到 `mUt=!0` 的含义 —— **是默认开**。

---

## 6. 判断：接线状态

**这版里是真正接线可用的子系统，不是「只写了类型声明」。** 依据四层：

**（1）灰度开关默认开。** `raw/chunks2/0329__chunk-110gm4an.js:24` 逐字 `var mUt=!0;`；`YJ=()=>k(RYe,mUt)` 从 GrowthBook 取 `tengu_plugin_hooks_modules`，取不到就是 `!0`。关掉它的路径也被枚举（`raw/chunks2/0330__chunk-98jdspgk.js` 的 `HOOKS_MODULES_FLAG_SOURCE`：`override` / `payload` / `disk` / `disabled` / `fallback`）。

**（2）有真实调用点，且分布合理。** 至少：信任接受后加载（`raw/chunks2/1245__chunk-f5w4pbxy.js@9695`）；worker 具现化与重生（`0374@1268258`、`@1728382`、`@1724606`）；远程 surface 的渲染请求（`raw/chunks2/0105__chunk-xep95vq1.js@570097` 的 `hooked:` 字段、`@570771` 的 `client_modules`）；CLI 命令（`0006__x-inntypeofn.js@5164`、`1435__x-registerPluginCommands.js@13750`/`@20608`）；插件目录监听与热重载（`0374` 的 `bIt()` 去抖与 `SIt()` 熔断、`OIt()` 的 `watchPlugins`/`release`）。

**（3）二进制里已有 10 个用它写的插件。** `raw/chunks2/1651…1661` 每个都出现 `hooksModule:` 字段（形状 `eS({name:…,hooksModule:iU(import.meta.dir,<module>,()=>name())})`），其中 6 个还导出 `registerPlugin`；内建加载器要求模块**必须**导出 `registerPlugin`，否则抛错（`raw/chunks2/0095__chunk-sthe7p0e.js@66491`：``"a built-in module has no registerPlugin function: …"``）。名字可确认的：`claude-test`（1651/1654）、`cc-plugin-mermaid`（1653）、`cc-plugin-responsive-mode`（1654）、`cc-plugin-sec-default`（1657，带 `seat(` 与 `decidesClassicEvent` —— 政策插件坐在 `prepend`/`append` tier，能裁决 classic 事件）、`cc-plugin-agents-md`（1658）、`cc-plugin-telemetry`（1659，闭包里同时出现 `"anthropic"` 与 `"collector"` 两个流）、`cc-plugin-mods-guide`（1661）。

**（4）有一等公民的文档与技能。** `assets/` 里有完整的 `asset-050`（长文）与 `asset-051`（`plugin-authoring` SKILL.md），并会把类型文件写到 mod 目录旁边（`asset-051:14`）。

**但仍处 EARLY ACCESS，有明确的半成品痕迹**：类型声明头部自述 `EARLY ACCESS: this surface may change between releases without notice.`（`:3`）；`plugin test` 是 `earlyAccess:"hooksModules"` 且命令 `{hidden:true}`；`hooks.json` 里一个已死字段被显式改成报错（`surface: bbt({error: 'hooks.json \`surface\` is gone: …'})`，`raw/chunks2/0055__chunk-hrhfcbdv.js@131757` 附近）；surface 表里有明确的「还没做」（`mobile` 无 `Input`/`Select`，`:3610-3614` 原文「The table grows when the app draws them」；`vscode` 无 `Client`，`:3625-3631`）；**`hooks-worker.js` 本体仍未找到**（§7）。

**一句话**：类型声明是「写给人的契约」，但契约背后的机器（worker、沙箱、生命周期、扫描准入、内置插件、CLI、热重载、UI wire 协议）在这版二进制里**全部存在且被调用**；它没被藏起来，只是被一个默认开的灰度开关和一个默认隐藏的 CLI 子命令包着。
---

## 7. 未找到 / 待验证

- **`hooks-worker.js` 本体**（`HOOKS_WORKER_URL` 指向的 `$bunfs` 入口自身）：**未找到**。只有 URL 常量与 worker 内部的桥接代码（`0150`）。
- **`CLAUDE_CODE_HOOKS_SAME_THREAD` 的完整语义**：**部分**。`0374@1712522` 有该分支，但同线程下模块在哪个上下文求值、是否跳过 `vm` 沙箱**未找到**。- **13 个沙箱全局之外是否还有偷偷注入的名字**：**推断为否**（`ip()=Object.create(null)` + 13 次 `define`）；但 `FBe(t,pbe)`（`0146@206978`）往上下文里装了什么**未逐字读完**。**`aoe` 白名单（11 个操作）的业务理由**同理：**推断**是请求/UI 型操作没有可枚举的 host check，原文没写理由。
- **`cc-plugin-diff` / `cc-plugin-tips` / `cc-plugin-plugin-authoring` / `cc-plugin-claude-test` 与那 10 个 `hooksModule:` 文件的精确对应**：**部分**，靠字符串共现推断，未逐个反解。**插件侧绕过 `ui.render` 的「直接画」旁路**：**未找到**，所有绘制都过 `ui.render` + `$.ui.resolve`。

---

## 附录：引用索引

**类型声明（`work/assets/asset-044-asset.txt`）**：`:1-11` 头部与 EARLY ACCESS · `:19-26` 环境/后缀/`import()`/元素来源 · `:30-31` 测试环境 · `:1066-1091` classic 事件名与输入 · `:2130-3385` CoreEngineInterface（21 命名空间） · `:3397` CoreEventOf 组成 · `:3546-3648` 元素表与四个 surface · `:3714-4192` 43 个引擎事件 · `:4192-4205` EngineInterface/Built · `:4398-4457` EventCalls · `:4463-4498` EventName/EventOf/Events · `:4782-4830` HookBudget/HookFailure · `:4842` 33 个 classic 输入联合 · `:4854-4856` HooksModule · `:6094-6193` Next/NextBudget · `:6258-6306` NounEvent · `:6308-6322` On · `:6371-6710` OpEventOf（60 个） · `:7147-7269` PluginNoun/PluginOptions/PluginRegister* · `:8641-8660` Register/Registration · `:8680-8690` RenderComponent/RenderElement · `:9663` RenderSurface · `:11445` StreamingEventName · `:11857-11875` Tier/TIERS · `:13696-13838` globals 与 13 个名字 · `:13842-14914` claude-code/testing 全文。

**测试套件（`work/assets/asset-045-asset.txt`）**：`:10-59` collector · `:114` TIMEOUT_MS=5000 · `:911-935` install/handover · `:1016` FIRES_PER_ADVANCE_MAX · `:1112-1126` mockClock · `:1182-1214` mockEnv/mockStore · `:1216-1224` mock · `:1340-1413` mount/mounted · `:1566-1618` openSeat · `:1813-1888` runCase/timed · `:1890-1917` run/test/tier。

**JS 实现（`raw/chunks2/`）**：`0006__x-inntypeofn.js@5164` plugin test 分派 · `0055__chunk-hrhfcbdv.js@75380` 后缀表 · `@131757` hooks.json schema · `0146__chunk-hhxhpvxp.js@58914` 全局引导源码 · `@152175` `import()` 拒绝器 · `@152847` SourceTextModule · `@158956` `ip()` · `@202514` `kVr()` · `@206807-206945` codeGeneration 与 `mzo()` · `0150__x-thepluginsenvironmentwasunloaded.js` worker 半（全文） · `0329__chunk-110gm4an.js` 灰度开关（全文） · `0330__chunk-98jdspgk.js` 开关来源枚举 · `0374__chunk-mphp7acd.js@1262700` 原生模块拒绝 · `@1264941` `OAe()` · `@1267204` `Nvt()` · `@1268258` `geo()` · `@1274791` `aoe` + 扫描准入 · `@1705533` worker 死亡 · `@1710573` `wPt` · `@1712522` same-thread · `@1724606`/`@1728382` 重生与具现化 · `0764__chunk-ybjnt5d8.js@4015` surface 沙箱 + console · `0765__chunk-vvhdd9fn.js:11` REPORT_MARK · `0766__chunk-ywkfhf88.js:1` CLI 命令表与 earlyAccess · `0768__chunk-9d5bhh5t.js` pluginTestRefusal · `0769__x-CHILD_ARGV_LENGTH.js@13325` pluginTestMain · `@13818` 三文件夹具 · `@36000-37000` 虚拟模块 vm 求值 · `0799__x-HOOKS_MODULES_FLAG.js` 导出别名 · `0095__chunk-sthe7p0e.js@66491` 内建模块 registerPlugin 校验 · `1245__chunk-f5w4pbxy.js@8155`/`@9695` 信任门 · `1435__x-registerPluginCommands.js@13750` validate 注册 · `@20608` test 注册 · `1651-1661` 10 个内置 hooks 模块插件 · `1923__x-marketplaceAddHandler.js@17949` validate 处理器。

**官方散文**：`asset-050-Function-hooks-the-long-form.md`（`:9-31` 是什么与事件面、`:33-62` 类型与契约、`:64-75` 开发与 `plugin test`、`:77-103` `ui.render` 细节、`:105-120` `session.append`、`:122-135` 长任务、`:137-144` 注册工具与 agent 类型） · `asset-051-plugin-authoring.md`（`:6-18` 三文件与类型落点、`:20-41` 形态表、`:42-48` 校验与排错）。

**前一轮产出**：`extracted/06-quirks.md:5` 33 个 hook 事件 · `:18-126` §1 hooks 系统 · `:125-126` §1.6 hooks-worker 与 functionHooks · `:557` 灰度开关表 · `:581` 「worker 的 IPC 协议未找到」。
