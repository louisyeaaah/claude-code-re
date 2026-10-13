# 沙箱：seatbelt profile 是怎么拼出来的、默认放行什么

> 补齐前面报告里"未完成"的一项：sandbox profile 的生成逻辑与默认放行集合。
> 对象仍然是 Claude Code v2.1.287；一手证据来自 JS 语料 `raw/chunks2/`（不是反汇编）。
> 相关：`06-quirks.md`（权限门 = JS 侧"要不要问用户"）、`REPORT-native.md`（CLI 自身无 App Sandbox entitlement）。

## 结论速览

1. **沙箱默认是关的**。设置项 `sandbox.enabled` 的原文描述是：`Run Bash commands inside the sandbox. Default: false.` —— 不开启时，文件读写规则完全不生效（见 §3 的两个 `if(!config)` 分支）。
2. profile **不是原生代码拼的，而是在 JS 侧拼成字符串数组**，再交给 macOS 的 `sandbox-exec` 执行；同一套代码在 Linux 上换用 `bwrap` + `seccomp`（后者本报告未展开）。
3. profile 骨架来自 **Chrome 的沙箱策略**：`(version 1)` + `(deny default (with message "<logTag>"))`，然后逐项白名单（进程、user-preference、指定 Mach 服务、指定 IOKit、指定 sysctl、特定 system-socket）。
4. **文件读**：没有配置就是 `(allow file-read*)`（全放行）；有配置时仍是"默认放行"，再叠加 `denyRead` 与例外 `allowRead`。
5. **文件写**：没有配置就是 `(allow file-write*)`（全放行）；有配置时变成"仅 `allowWrite` 允许"，再减去一份**内置禁写清单**——这才是真正值得抄的部分（§4）。
6. 内置禁写清单把"agent 不该改自己运行环境"写进了沙箱：shell 启动文件、git 配置、`.mcp.json`、`.vscode`/`.idea`、`.claude/commands`、`.claude/agents`、`.git/hooks`。
7. 某些字段**只在用户/企业管理/CLI `--settings` 生效，项目设置里的同名配置被忽略**——防止仓库自我提权。

## 1. 这套东西在哪、怎么被执行

- profile 生成函数：`raw/chunks2/0205__chunk-5vadtxaa.js` @730440 起（`PV({readConfig, writeConfig, httpProxyPort, socksProxyPort, needsNetworkRestriction, allowUnixSockets, allowAllUnixSockets, allowLocalBinding, allowMachLookup, allowPty, allowGitConfig, enableWeakerNetworkIsolation, allowAppleEvents, logTag})`）。
- 文件规则由三个函数生成：`OV(readConfig)`（读）、`BV(writeConfig)`（写）、`vV()`（内置禁写清单）。
- 拼接工具 `_a(kind, ops, set, msg)` 输出形如：

```scheme
(deny file-write*
 (subpath "/Users/me/project/.git")
 (with message "<logTag>"))
```

- 二进制里能同时看到 `sandbox-exec` / `sandbox_init` / `seatbelt` 与 Linux 侧的 `bwrap` / `seccomp` 字符串——**同一抽象两套后端**。

## 2. profile 骨架（逐字，按出现顺序节选）

```scheme
(version 1)
(deny default (with message "<logTag>"))

; Essential permissions - based on Chrome sandbox policy
; Process permissions
(allow process-exec)
(allow process-fork)
(allow process-info* (target same-sandbox))
(allow signal (target same-sandbox))
(allow mach-priv-task-port (target same-sandbox))

; User preferences
(allow user-preference-read)

; Mach IPC - specific services only (no wildcard)
(allow mach-lookup
 (global-name "com.apple.audio.systemsoundserver")
 (global-name "com.apple.distributed_notifications@Uv3")
 (global-name "com.apple.FontObjectsServer")
 (global-name "com.apple.fonts")
 (global-name "com.apple.logd")
 (global-name "com.apple.lsd.mapdb")
 (global-name "com.apple.PowerManagement.control")
 (global-name "com.apple.system.logger")
 (global-name "com.apple.system.notification_center")
 (global-name "com.apple.system.opendirectoryd.libinfo")
 (global-name "com.apple.system.opendirectoryd.membership")
 (global-name "com.apple.bsd.dirhelper")
 (global-name "com.apple.securityd.xpc")
 (global-name "com.apple.coreservices.launchservicesd")
)
```

可选追加项（默认关，按设置开）：

```scheme
; trustd.agent - needed for Go TLS certificate verification (weaker network isolation)
(allow mach-lookup (global-name "com.apple.trustd.agent"))
; Apple Events - opt-in; needed for open/osascript to talk to other apps (appleeventsd)
(allow appleevent-send)
```

其余还包括（节选）：`(allow ipc-posix-shm)`（共享内存）、`(allow ipc-posix-sem)`（Python multiprocessing 信号量）、`(allow iokit-open …)`、`(allow iokit-get-properties)`、`(allow system-socket (require-all (socket-domain AF_SYSTEM) (socket-protocol 2)))`（明确注释"不构成网络访问"）、`(allow sysctl-read …)` 白名单。

> 可学习：**默认拒绝 + 逐项白名单**，而且把"为什么需要这一项"写成注释（Chrome 策略来源、Go TLS 需要 trustd、Unix 语义需要共享内存）。这些都是以后排障时唯一的线索。

## 3. 读 / 写规则的默认行为（关键）

```js
function OV(e, r) {          // 读规则
  if (!e) return ["(allow file-read*)"];      // 没有配置 = 全放行
  ...
}
function BV(e, r, n = false) { // 写规则
  if (!e) return ["(allow file-write*)"];     // 没有配置 = 全放行
  ...
}
```

有配置时的构造顺序：

- **读**：先 `(allow file-read*)` → 叠加 `denyRead` → 叠加 `allowRead`（例外，优先于 deny）→ 用 glob↔路径交叉计算出的过滤规则 → 若 deny 覆盖了根或 `/` 则补 `(allow file-read* (literal "/"))` → 若存在 deny 则补 `(allow file-read-metadata (vnode-type DIRECTORY))`（保证目录还能列）→ 再叠加一份 unlink/create 限制。
- **写**：先只允许 `allowWrite` 里的路径 → 再叠加 `denyWithinAllow` → 再叠加**内置禁写清单** → 对若干目录级别补 `(deny file-write-unlink file-write-create …)`。

一个值得注意的细节：目录名较多时会被**分组压缩**（把同一父目录下的多个条目合成一个 `(subpath …)` 块，见 `RV()` 的 `groups`/`rest` 与 `fT`、`NV` 阈值），目的是控制 profile 长度——顺带说明这份 profile 有长度预算。

## 4. 内置禁写清单（逐字，最值得抄的部分）

```js
var pgn = [".gitconfig", ".gitmodules", ".bashrc", ".bash_profile",
           ".zshrc", ".zprofile", ".profile", ".ripgreprc", ".mcp.json"];
var ee  = [".git", ".vscode", ".idea"];
function fgn() { return [...ee.filter(e => e !== ".git"), ".claude/commands", ".claude/agents"]; }
```

展开成规则（相对 `process.cwd()`，同时生成 `**/` 变体）：

```js
for (const g of pgn)     { push(cwd/g);         push(`**/${g}`); }
for (const g of fgn())   { push(cwd/g);         push(`**/${g}/**`); }   // .vscode .idea .claude/commands .claude/agents
push(".git/hooks");      push("**/.git/hooks/**");
if (!allowGitConfig) {   push(".git/config");   push("**/.git/config"); }
```

也就是说，开启沙箱后 **agent 不能写**：shell 启动文件（`.bashrc`/`.zshrc`/…）、git 配置与模块、`.mcp.json`、VS Code/JetBrains 工程目录、`.claude/commands` 与 `.claude/agents`（即**它自己的指令与子代理定义**）、以及 `.git/hooks`（防止植入钩子）。

> 可学习：这份清单是"agent 能改自己"的攻击面枚举。**把自己的配置目录和命令定义列为禁写**，比在提示词里写"不要修改自己的配置"可靠得多。

## 5. 网络

```
需要限制网络时：不 push("(allow network*)")
  - 绑定/入站：本地任意端口      (allow network-bind/inbound (local ip "*:*"))
  - 出站：仅 localhost          (allow network-outbound (remote ip "localhost:*"))
  - Unix socket：全部或按目录白名单
  - 代理端口：HTTP/SOCKS 代理各允许 localhost:<port> 的 bind/inbound/outbound
不需要限制时：直接 (allow network*)
```

另外代码里有一个**网络违规记录器**：`wy(e, r, n, s)` 打印 `deny network-outbound <host>:<port> (<reason>)`，由 `(e, r) => xp.lookupFor(e)(...)` 包装——说明被拒绝的出站请求是被**逐条记录并回报**的，而不是静默失败。

还有一条 TLS 终止代理的配置（`NetworkConfigSchema`）：给 sandbox runtime 提供 CA 证书与私钥，用于在沙箱内终止 TLS，从而让**按请求的过滤**能看到 HTTPS 请求体；不提供则由 sandbox runtime 生成临时 CA。原文注释特别说明：Windows 上临时 CA 过不了信任检查，要用 `/sandbox install` 持久 CA。

## 6. 设置面与提权防护

`sandbox` 设置项（逐字摘要）：

| 字段 | 描述原文（节选） |
|---|---|
| `enabled` | `Run Bash commands inside the sandbox. Default: false.` |
| `failIfUnavailable` | `Exit with an error at startup if sandbox.enabled …` |
| `allowWrite` | `Additional paths to allow writing within the sandbox. Merged with paths from Edit(...) allow permission rules.` |
| `denyWrite` | `Additional paths to deny writing within the sandbox. Merged with paths from Edit(...) deny permission rules.` |
| `denyRead` | `Additional paths to deny reading within the sandbox. Merged with paths from Read(...) deny permission rules.` |
| `allowRead` | `Paths to re-allow reading within denyRead regions. Takes precedence over denyRead for matching paths.` |

提权防护（逐字）：**`Only honored from user, managed/policy, or CLI (--settings) settings — project settings (.claude/settings.json and .claude/settings.local.json) are ignored.`** ——仓库里的配置文件不能自己给自己开权限。

## 7. 与前面结论的关系

- `06-quirks.md` 讲的是 **JS 权限门**（"这个工具调用要不要问用户"），本报告讲的是**进程边界**（"跑起来之后能碰到什么"）。两层独立：前者可被设置/flag 改写，后者由 OS 强制。
- `REPORT-native.md` 已证：CLI 自身没有 App Sandbox entitlement，所以这层隔离是它**主动调用**的；如果沙箱没开（默认），Bash 子进程就只有 JS 权限门这一层约束。

## 8. 未完成 / 未验证

1. **Linux 侧的 `bwrap` + `seccomp` profile 生成逻辑未读**（二进制里有字符串，但本报告只覆盖 macOS 分支）。
2. `excludedCommands`、`enabledPlatforms`、`failIfUnavailable` 的完整语义与默认值未逐条读出。
3. profile 里 `mach-lookup` 白名单之外的可选项（`allowMachLookup` 从哪来）未追。
4. 没有实机开启沙箱跑一次验证（会改本机设置，按纪律不擅自做）。
5. 本文引用的是 JS 源码里的模板字面量与 settings schema 文本；**profile 的最终字符串**（拼接结果）未在运行时抓取。
