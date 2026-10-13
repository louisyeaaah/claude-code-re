# 03 · 内置工具（Claude Code v2.1.287）

> 语料 `raw/chunks/cNNNN.js`（minified，字符串与模板字面量完整）。引用格式 `chunks/cNNNN.js @<chunk 内偏移>`。
> 英文一律逐字引用，`${X}` 原样保留表示运行时插值；引用块内 `…` 表示省略。未改动 `raw/`。

## 结论速览

1. 可定位到 **82 个 `Wt({…})` 工具定义对象**，其中能解析出明确工具名的约 70 个；核心工具集由 `c0583.js` 的 `D(e)`/`x(e)` 两个 Set 收敛（`chunks/c0583.js @9179`、`@8958`）。
2. 工具对象统一挂在 `Wt({…})` 下，字段固定：`name / searchHint / backgrounding / maxResultSizeChars / description() / prompt() / inputSchema / outputSchema / isReadOnly() / isConcurrencySafe()`（例 `chunks/c0682.js @897506`）。
3. **只读与并发是两个独立布尔**：Read/Glob/Grep/WebFetch/WebSearch/ToolSearch/LSP 均 `RO=!0 CS=!0`；Bash 动态判定 `isReadOnly(e){return !hx(Ue)&&rKe(e)}`、`isConcurrencySafe(e){return this.isReadOnly?.(e)??!1}`（`chunks/c0682.js @3991246`）；Edit/Write/NotebookEdit 两者都不声明，走逐文件权限判定。
4. 描述文案**双份**：`gx({model,leanPrompt})` 为真走 lean 版，否则走完整版（`chunks/c0682.js @968032` vs `@970920`；`chunks/c0330.js @99539`）。lean 版压缩成 3~5 条 bullet，但**保留会改变行为的事实**（如"输出只有你看见"）。
5. 万能工具的边界靠**指名替代 + 说明后果**写成：`IMPORTANT: Avoid using this tool to run ${w} commands, unless explicitly instructed or after you have verified that a dedicated tool cannot accomplish your task.`（`chunks/c0682.js @968288`）。
6. 失败路径**提前写进 prompt**：`or the call will fail`（`chunks/c0682.js @3824662`）；Edit 的 9 类 `errorCode` 各配一句含恢复动作的自然语言（`chunks/c0682.js @3832818` 附近）。
7. 授权/风险用**独立小节**承载：`This tool REQUIRES user approval - they must consent to entering plan mode`（`chunks/c0978.js @5897`）、AskUserQuestion 的 `z1o` 段（`chunks/c0522.js @3746`）。
8. TodoWrite（全量替换清单）与 TaskCreate/Get/Update/List（可寻址 + 依赖图）**两套并存**，前者明写 `## When NOT to Use This Tool`（`chunks/c1006.js @55978`）。

---

## 1. 工具清单全表

枚举法：全 chunk 扫 `Wt({`，括号配平截对象，读 `name:` 并把常量名解析回字符串。`RO`=isReadOnly，`CS`=isConcurrencySafe，`-` =**对象里未声明该字段**（默认值见 §5）。

### 1.1 文件 / shell / 检索

| 工具名 | 用途一句话 | 关键约束 | chunk 引用 |
|---|---|---|---|
| Bash | 执行 shell 命令并返回输出 | RO 动态；CS=RO；`backgrounding:"self"`、`enablesCodeExecution:!0`、`ruleContentField:"command"` | `chunks/c0682.js @3991246` |
| PowerShell | Windows 等价 shell | RO=`on(e)`、CS=RO、`backgrounding:"self"` | `chunks/c2084.js @95130` |
| Read | 读文件/图片/PDF/notebook | RO=!0 CS=!0；`maxResultSizeChars:1/0` | `chunks/c0682.js @897506` |
| Write | 创建或整体覆写 | 无 RO/CS；`strict:!0` | `chunks/c0682.js @714521` |
| Edit | 精确字符串替换 | 无 RO/CS；`validateInput` 9 类 give-up 反馈 | `chunks/c0682.js @3827219` |
| NotebookEdit | 改 notebook 单个 cell | 无 RO/CS；`shouldDefer:!0` | `chunks/c0682.js @3841803` |
| Glob | 按文件名 glob，结果按 mtime 排序、限 100 | RO=!0 CS=!0 | `chunks/c0682.js @925323` |
| Grep | ripgrep 内容搜索 | RO=!0 CS=!0；`ruleContentField:"pattern"` | `chunks/c0682.js @930576` |
| WebFetch | 抓 URL→markdown→小模型问答 | RO=!0 CS=!0；`backgrounding:"detach"`；有 TTL 缓存 | `chunks/c0682.js @1370802` |
| WebSearch | 联网搜索，返回 titles+URLs | RO=!0 CS=!0；`backgrounding:"detach"`；每会话次数上限 | `chunks/c1006.js @46538` |
| LSP | 定义/引用/符号/hover | RO=!0 CS=!0；`isLsp:!0`、`ruleContentField:"filePath"` | `chunks/c1006.js @98661` |

### 1.2 MCP 与工具发现

| 工具名 | 用途 | 约束 | 引用 |
|---|---|---|---|
| mcp（动态壳） | 所有 MCP 工具的统一壳，真名 `mcp__<server>__<tool>` | `isMcp:!0`、`backgrounding:"self"`、`checkPermissions→passthrough` | `chunks/c2674.js @818` |
| ToolSearch | 在工具目录里检索工具 | RO=!0 CS=!0 | `chunks/c0682.js @1093700` |
| WaitForMcpServers | 等 server 连接就绪 | RO=!0，**CS=!1** | `chunks/c0682.js @1932733` |
| RefreshMcpTools | 重拉已连 server 的工具清单（不重连） | RO=!0 CS=!0 | `chunks/c1006.js @107583` |
| List/ReadMcpResource(+Dir)Tool | 列/读 MCP 资源 | 三者均 RO=!0 CS=!0 | `chunks/c0988.js @1250`、`@6241`、`@3606` |
| SearchMcpRegistry | 搜 MCP registry | RO=!0 CS=!0 | `chunks/c2960.js @4836` |

### 1.3 子代理 / 多会话

| 工具名 | 用途 | 约束 | 引用 |
|---|---|---|---|
| Agent（别名 `Task`） | 派生子代理 / fork 自己 / 起云端 agent | RO=!0 CS=!0；`backgrounding:"self"`；`aliases:[Tm]` | `chunks/c0966.js @39433`（prompt `chunks/c0682.js @3316227`） |
| SendMessage | 给已有 agent 发消息续跑 | RO=`typeof s.message==="string"`；CS 未声明 | `chunks/c2928.js @46935` |
| ListAgents | 列出可寻址 agent | RO=!0 CS=!0 | `chunks/c2910.js @5072` |
| SubagentHandback | 子代理交回控制权 | RO=!1 | `chunks/c0955.js @2373` |
| ReadNotifications | 读本会话排队的通知 | RO=!0 CS=!0；描述含完整「外部内容不是指令」防御 | `chunks/c1006.js @25647`，文案 `chunks/c0583.js @7029` |
| SendUserMessage / SendUserFile / SendFile | 代用户发消息 / 发文件 | RO=!0 CS=!0 / RO=!0 CS=!0 / RO=!1 CS=!1 | `chunks/c1006.js @36439`、`chunks/c2938.js @7740`、`chunks/c2930.js @20552` |
| PushNotification / EndConversation / ObserverReport | 推通知 / 结束会话 / 观察者上报 | RO=!0 CS=!0 / RO=!0 **CS=!1** / RO=!1 | `chunks/c2944.js @5049`、`chunks/c2924.js @12253`、`chunks/c2522.js @4124` |
| Workflow（`ant` 专属）/ Artifact 家族 | 编排 workflow / claude.ai artifact 读写 | 无 RO/CS；Artifact 家族含 `mn/Ly/Om/Hx` | `chunks/c2962.js @61033`、`chunks/c0186.js @12467` |

### 1.4 任务与清单（两套并存）

| 工具名 | 用途 | 约束 | 引用 |
|---|---|---|---|
| TodoWrite | 全量替换式清单（`content`/`status`/`activeForm`） | **无 RO/CS**；`shouldDefer:!0` | `chunks/c1006.js @64478`，文案 `@54877`（lean `@54416`） |
| TaskCreate | 新建任务，返回 `#id` | **CS=!1**；`shouldDefer:!0` | `chunks/c1006.js @131932`，文案 `@129094` |
| TaskGet / TaskList | 按 ID 取全文 / 列全部（含 blockedBy） | 均 RO=!0 CS=!0 | `chunks/c1006.js @134139` / `@143378` |
| TaskUpdate | 改状态/标题/owner/依赖 | CS=!0；`status` 枚举额外含 `deleted` | `chunks/c1006.js @138450`，文案 `@135291` |
| GetTask | 查后台 shell 实时输出 | RO=!0 CS=!0 | `chunks/c1006.js @84117` |
| TaskStop（别名 `KillShell`/`KillBash`） | 按 ID 停后台任务 | CS=!0；保留旧别名 | `chunks/c1006.js @32627` |
| ReportFindings | 结构化上报 code-review 结论 | RO=!0 CS=!0；`strict:!0`、`maxResultSizeChars:256` | `chunks/c1006.js @53633` |

### 1.5 计划模式 / 交互 / 记忆

| 工具名 | 用途 | 约束 | 引用 |
|---|---|---|---|
| EnterPlanMode | 请求进入计划模式 | RO=!0 CS=!0；agent 上下文里 validateInput 直接拒绝 | `chunks/c0978.js @6309`，文案 `@2540` |
| ExitPlanMode | 提交计划请用户批准 | **RO=!1** CS=!0；`requiresUserInteraction(){return !0}` | `chunks/c0953.js @81272`，文案 `@78306` |
| AskUserQuestion | 向用户问多选题 | RO=!0 CS=!0 | `chunks/c0986.js @12253`，文案 `chunks/c0522.js @472`/`@1942` |
| Skill | 调用 skill / slash command | 无 RO/CS；`isEnabled(){return !Mh()}`；名字必须精确匹配 listing | `chunks/c0978.js @20090`，文案 `chunks/c0682.js @3271463` |
| StructuredOutput | 强制结构化输出 | RO=!0 CS=!0 | `chunks/c0458.js @22762` |
| memory_read / memory_write / memory_list | 记忆库读/写/列 | read、list RO=!0 CS=!0；write 未声明 | `chunks/c0682.js @941969`、`chunks/c0384.js @48460`、`chunks/c1006.js @67166` |

### 1.6 后台 / 定时 / worktree / 其余

| 工具名 | 约束要点 | 引用 |
|---|---|---|
| Monitor | CS=!0；`enablesCodeExecution:!0`；`maxResultSizeChars:1e4`；结果里明写 `do not poll or sleep` | `chunks/c0919.js @14238`，文案 `chunks/c0573.js @1550` |
| ScheduleWakeup | 无 RO/CS；`maxResultSizeChars:1000` | `chunks/c1006.js @40456` |
| CronList / CronCreate / CronDelete | List RO=!0 CS=!0；Create/Delete 未声明 | `chunks/c2954.js @4846` / `chunks/c2950.js @5398` / `chunks/c2952.js @4788` |
| RemoteTrigger | RO=`e.action==="list"||…`，CS=!0 | `chunks/c2958.js @15292` |
| EnterWorktree / ExitWorktree | 均无 RO/CS；`name`/`path` 互斥由 schema `.refine` 保证；Exit 的 `isDestructive(e){return e.action==="remove"}` | `chunks/c1006.js @114420` / `@124286` |
| Poll / replay / Projects | RO=!0 CS=!0 / — / — | `chunks/c2918.js @12658`、`chunks/c2543.js @3176`、`chunks/c2922.js @14602` |
| onboarding 与建议类：ShareOnboardingGuide(RO=!1 CS=!1)、ShowOnboardingRolePicker、ConnectGitHub、SuggestPluginInstall、SuggestSkills、propose_skills、SuggestConnectors、ListConnectors、ProposeGoal、FetchInboxMessage、SendFeedback、PermissionRequest | — | `chunks/c1006.js @27626`/`@31266`/`@77188`/`@65392`、`chunks/c0581.js @20`、`chunks/c2109.js @15881`/`@17862`、`chunks/c2940.js @15740`、`chunks/c2934.js @4821`、`chunks/c2936.js @5078`、`chunks/c2942.js @5835`、`chunks/c2154.js @6114` |
| self_hosted_runner_*（9 个） | `spawn_local`、`requeue_session` RO=!1，其余 RO=!0 CS=!0 | `chunks/c2956.js @4829`–`@15735` |

### 1.7 名字存在但**不是**本 build 的注册工具

- **改名表**：`var c={Task:"Agent",KillShell:"TaskStop",KillBash:"TaskStop",ListPeers:"ListAgents",Brief:"SendUserMessage",ListMcpResources:"ListMcpResourcesTool",ReadMcpResource:"ReadMcpResourceTool",ReadMcpResourceDir:"ReadMcpResourceDirTool"}`（`chunks/c0073.js @2436`）。
- **仅存在于权限规则分组**：`MultiEdit`、`NotebookRead`、`LS`（`chunks/c3520.js @17273`：`[…,Jr,"MultiEdit","LS"]`、`[…,"NotebookRead","LS",…]`）——**未找到**它们的工具定义对象。
- **已废弃名单**：`var Jhe=new Set(["Frame","FrameRead","TeamCreate","TeamDelete","SuggestBackgroundPR","AutofixPr","TaskOutput","AgentOutputTool","BashOutputTool","AgentOutput","BashOutput"])`（`chunks/c0682.js @1001038`）。
- `Schedule`、`Worktree`、`SlashCommand`、`MCP`（作工具名）：**未找到**工具定义对象；能力拆为 ScheduleWakeup/Cron*、EnterWorktree/ExitWorktree、Skill 承担 slash command 调用（推断）。

---

## 2. 逐字引用（8 个最有教学价值的描述）

### 2.1 Bash —— 用「专用工具优先」压住万能工具的滥用

完整版由 `Yht()` 拼接（`chunks/c0682.js @970920`）：

```text
Executes a given bash command and returns its output.

The working directory persists between commands, but shell state does not. The shell environment is initialized from the user's profile (bash or zsh).

IMPORTANT: Avoid using this tool to run ${w} commands, unless explicitly instructed or after you have verified that a dedicated tool cannot accomplish your task. Instead, use the appropriate dedicated tool as this will provide a much better experience for the user:

File search: Use ${co} (NOT find or ls)
Content search: Use ${Jr} (NOT grep or rg)
Read files: Use ${dt} (NOT cat/head/tail)
Edit files: Use ${Ot} (NOT sed/awk)
Write files: Use ${Sn} (NOT echo >/cat <<EOF)

While the ${Ue} tool can do similar things, it's better to use the built-in tools as they provide a better user experience and make it easier to review tool calls and give permission.

# Instructions
If your command will create new directories or files, first use this tool to run `ls` to verify the parent directory exists and is the correct location.
Always quote file paths that contain spaces with double quotes in your command (e.g., cd "path with spaces/file.txt")
Try to maintain your current working directory throughout the session by using absolute paths and avoiding usage of `cd`. You may use `cd` if the User explicitly requests it. In particular, never prepend `cd <current-directory>` to a `git` command — `git` already operates on the current working tree, and the compound triggers a permission prompt.
You may specify an optional timeout in milliseconds (up to ${iO()}ms / ${iO()/60000} minutes for a foreground command). By default, your command will timeout after ${qz()}ms (${qz()/60000} minutes).
```

（`${co}`=Glob、`${Jr}`=Grep、`${dt}`=Read、`${Ot}`=Edit、`${Sn}`=Write、`${Ue}`=Bash；`${w}` 在 macOS/Linux 展开为 `` `find`, `grep`, `cat`, `head`, `tail`, `sed`, `awk`, or `echo` ``。offset：`@968288`、`@974420`、`@974994`。）

**在做什么**：先承认能力重叠（"While the Bash tool can do similar things"），再把理由落到**用户体验与权限审查**（"easier to review tool calls and give permission"），而不是"你不许用"。`# Instructions` 每条都是真实踩过的坑。反例用括号就地否定 `(NOT find or ls)`，比另起一句省 token、也更难被跳过。

lean 版（`YYn()`，`chunks/c0682.js @968032`）只留 4 条，并且**换了取舍**——去掉工具导航，保留两条会改变行为的事实：

```text
Executes a bash command and returns its output.
- Working directory persists between calls, but prefer absolute paths — `cd` in a compound command can trigger a permission prompt. Shell state (env vars, functions) does not persist; the shell is initialized from the user's profile.
- Command output is displayed to you, not reliably to the user.
- `timeout` is in milliseconds: default ${qz()}, max ${iO()} for a foreground command.
```

同工具在 coordinator 角色下降权，把**理由与出口一起写**（`chunks/c0583.js`，模板串以 `${Ue} in the coordinator` 开头）：

```text
${Ue} in the coordinator runs only a command it can verify as read-only and that stays in the working directory (no cd, pushd or popd), with no input besides command, description and timeout (no run_in_background, no sandbox bypass, no other machine) — run anything else from a worker via the ${yt} tool.
```

### 2.2 Edit —— 失败前置 + 错误即教学

`Nfr()`（`chunks/c0682.js @3824547`，正文 `@3825704`）：

```text
Performs exact string replacements in files.

Usage:
- You must use your `${dt}` tool at least once in the conversation before editing. This tool will error if you attempt an edit without reading the file.
- When editing text from Read tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: ${s}. Everything after that is the actual file content to match. Never include any part of the line number prefix in the old_string or new_string.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.${g}
- Use `replace_all` for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance.
```

lean 版（`@3824662`）：

```text
Performs exact string replacement in a file.

- You must ${dt} the file in this conversation before editing, or the call will fail.
- `old_string` must match the file exactly, including indentation, and be unique — the edit fails otherwise. Strip the Read line prefix (${r?"line number + a single tab or `:`":"line number + tab"}) before matching.
- `replace_all: true` replaces every occurrence instead.
```

运行时错误文本（`chunks/c0682.js @3832818` 附近）——**每条都是给模型的下一步动作**：

```text
Found ${Ne} matches of the string to replace, but replace_all is false. To replace all occurrences, set replace_all to true. To replace only one occurrence, please provide more context to uniquely identify the instance.
String: ${b}
```

```text
String to replace not found in file.
String: ${b}
(note: Edit also tried swapping \uXXXX escapes and their characters; neither form matched, so the mismatch is likely elsewhere in old_string. Re-read the file and copy the exact surrounding text.)
```

另有：`File does not exist. … Did you mean ${Qe}?` / `Cannot create new file - file already exists.` / `File is a Jupyter Notebook. Use the ${jl} to edit this file.` / `No changes to make: old_string and new_string are exactly the same.` / `File is too large to edit (${pn(qe)}). Maximum editable file size is ${pn(Atn)}.`

**学习点**：① 失败前置（`or the call will fail`）把错误成本搬到决策点之前；② 反例必带修法（"加最小上下文 or 用 `replace_all`"）；③ `\uXXXX` 那条 note 把**排障思路**交出去，而不是报一个 mismatch。

### 2.3 Read —— 用乐观假设降低模型犹豫

`iWo()`（`chunks/c0330.js @99539`）：

```text
Reads a file from the local filesystem. You can access any file directly by using this tool.
Assume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- By default, it reads up to ${d2t} lines starting from the beginning of the file
- When you already know which part of the file you need, only read that part. This can be important for larger files.
- This tool allows Claude Code to read images (eg PNG, JPG, etc). When reading an image file the contents are presented visually as Claude Code is a multimodal LLM.
- This tool can read Jupyter notebooks (.ipynb files) and returns all cells with their outputs, combining code, text, and visualizations.
- This tool can only read files, not directories. To list files in a directory, use the registered shell tool.
- You will regularly be asked to read screenshots. If the user provides a path to a screenshot, ALWAYS use this tool to view the file at the path. This tool will work with all temporary file paths.
- If you read a file that exists but has empty contents you will receive a system reminder warning in place of file contents.
```

lean 版（`@99539` 起同函数）压成 5 条，最后一条把上面两段"读不到会怎样"合并成事实陈述：

```text
Reads a file from the local filesystem.

- `file_path` must be an absolute path.
- Reads up to ${d2t} lines by default.
- When you already know which part of the file you need, only read that part. This can be important for larger files.
- Reads images (PNG, JPG, …) and presents them visually. Reads PDFs via the `pages` parameter (e.g. "1-5", max 20 pages/request; required for PDFs over 10 pages). Reads Jupyter notebooks (.ipynb) as cells with outputs.
- Reading a directory, a missing file, or an empty file returns an error or system reminder rather than content.
```

### 2.4 Grep / Glob —— 把「用哪个工具」写成硬规则

Grep 完整版（`E6r()`，`chunks/c0330.js @103165`）：

```text
A powerful search tool built on ripgrep

  Usage:
  - ALWAYS use ${Jr} for search tasks. NEVER invoke `grep` or `rg` as a ${Ue} command. The ${Jr} tool has been optimized for correct permissions and access.
  - Supports full regex syntax (e.g., "log.*Error", "function\s+\w+")
  - Filter files with glob parameter (e.g., "*.js", "**/*.tsx") or type parameter (e.g., "js", "py", "rust")
  - Output modes: "content" shows matching lines, "files_with_matches" shows only file paths (default), "count" shows match counts
  - Pattern syntax: Uses ripgrep (not grep) - literal braces need escaping (use `interface\{\}` to find `interface{}` in Go code)
  - Multiline matching: By default patterns match within single lines only. For cross-line patterns like `struct \{[\s\S]*?field`, use `multiline: true`
```

Grep lean 版（同函数，`@103165`）：

```text
Content search built on ripgrep. Prefer this over `grep`/`rg` via ${Ue} — results integrate with the permission UI and file links.

- Full regex syntax (e.g. "log.*Error", "function\s+\w+"). Ripgrep, not grep — escape literal braces (`interface\{\}`).
- Filter with `glob` (e.g. "**/*.tsx") or `type` (e.g. "js", "py", "rust").
- `output_mode`: "content" (matching lines), "files_with_matches" (paths only, default), or "count".
- `multiline: true` for patterns that span lines.
```

Glob（`w6r()`，`chunks/c0330.js @102758`）：

```text
- Fast file pattern matching tool that works with any codebase size
- Supports glob patterns like "**/*.js" or "src/**/*.ts"
- Returns matching file paths sorted by modification time
- Use this tool when you need to find files by name patterns
- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the ${yt} tool instead (if available)
```

**学习点**：硬约束（`ALWAYS`/`NEVER`）**紧跟理由**；真实 bug 级细节（Go 的 `interface{}` 要转义、Glob 多轮搜索升级到 Agent）也写进去，省一整轮试错。

### 2.5 Agent —— 把「不要自欺」写成分节规范

`s0o()`（`chunks/c0682.js @3316227`）：

```text
## When to fork

Fork yourself (pass `subagent_type: "fork"`) when the intermediate tool output isn't worth keeping in your context. The criterion is qualitative — "will I need this output again" — not task size. Fork open-ended questions. If research can be broken into independent questions, launch parallel forks in one message. A fork beats a fresh subagent for this — it inherits context and shares your cache.

Forks are cheap because they share your prompt cache.

**Don't peek.** The tool result includes an `output_file` path — do not Read or tail it. You get a completion notification; trust it. Reading the transcript mid-flight pulls the fork's tool noise into your context, which defeats the point of forking.

**Don't race.** After launching, you know nothing about what the fork found. Never fabricate or predict fork results in any format — not as prose, summary, or structured output. The notification arrives as a user-role message in a later turn; it is never something you write yourself. If the user asks a follow-up before the notification lands, tell them the fork is still running — give status, not a guess.

**Writing a fork prompt.** Since the fork inherits your context, the prompt is a *directive* — what to do, not what the situation is. Be specific about scope: what's in, what's out, what another agent is handling. Don't re-explain background.
```

（`**Don't peek.**` `@3317187`，`**Don't race.**` `@3317446`；"Never delegate understanding" `@3318956`；成本敏感文案 `@3325107`；"Trust but verify" `@3329732`。）

```text
**Never delegate understanding.** Don't write "based on your findings, fix the bug" or "based on the research, implement it." Those phrases push synthesis onto the agent instead of doing it yourself. Write prompts that prove you understood: include file paths, line numbers, what specifically to change.
```

```text
**Do not spawn agents unless the user asks.** Each spawn starts cold and re-derives context you already have — it's the expensive path on this plan. A task with "multiple angles," "thorough," or several parts is not a request to spawn; handle it inline with your own tools. Only use this tool when the user explicitly says to use a subagent, or names one of the available agent types.
```

```text
## When not to use

If the target is already known, use the direct tool: ${dt} for a known path, ${Qe} for a specific symbol or string. Reserve this tool for open-ended questions that span the codebase, or tasks that match an available agent type.
```

```text
- Trust but verify: an agent's summary describes what it intended to do, not necessarily what it did. When an agent writes or edits code, check the actual changes before reporting the work as done.
```

**学习点**：判据锚死但允许自主（"qualitative … not task size"）；反幻觉写成**格式级禁令**（"not as prose, summary, or structured output"）并给正确动作；小标题本身就是禁令，扫描成本极低；`<example>` 里带 `<commentary>` 说明"这一步之后不该发生什么"。

### 2.6 TodoWrite —— 正例 / 反例 / reasoning 三段式

lean 版 `Bn`（`chunks/c1006.js @54416`）：

```text
Create and update a task list for the current session. The list is rendered to the user as your working plan.

- Each todo has `content`, `status` ("pending" | "in_progress" | "completed"), and `activeForm` (present-tense label shown while in progress).
- Send the full list each call; it replaces the previous one.
- Keep one item `in_progress` at a time and mark it `completed` when done.
```

完整版 `jn`（`@54877`，节选）：

```text
## When to Use This Tool

Use this tool proactively in these scenarios:

1. Complex multi-step tasks - When a task requires 3 or more distinct steps or actions
…
## When NOT to Use This Tool

Skip using this tool when:
1. There is only a single, straightforward task
2. The task is trivial and tracking it provides no organizational benefit
3. The task can be completed in less than 3 trivial steps
4. The task is purely conversational or informational

NOTE that you should not use this tool if there is only one trivial task to do. In this case you are better off just doing the task directly.
```

反例段（`@55978` 起）每个 `<example>` 后跟 `<reasoning>`：

```text
<example>
User: How do I print 'Hello World' in Python?
Assistant: In Python, you can print "Hello World" with this simple code:
…
<reasoning>
The assistant did not use the todo list because this is a single, trivial task that can be completed in one step. There's no need to track multiple tasks or steps for such a straightforward request.
</reasoning>
</example>
```

状态硬约束（`@62913`、`@63148`、`@63380`）：

```text
- Exactly ONE task must be in_progress at any time (not less, not more)
- ONLY mark a task as completed when you have FULLY accomplished it
- If you encounter errors, blockers, or cannot finish, keep the task as in_progress
- Never mark a task as completed if:
  - Tests are failing
  - Implementation is partial
  - You encountered unresolved errors
  - You couldn't find necessary files or dependencies
```

**学习点**：正反两侧对称展开且各带 reasoning；状态机写死并用括号堵住解释空间；"完成"被定义成 4 个可执行否决条件。

### 2.7 TaskCreate / TaskUpdate —— 允许文案重复，但把差异点写清

TaskCreate（`dr()`，`chunks/c1006.js @129094`）：

```text
## Task Fields

- **subject**: A brief, actionable title in imperative form (e.g., "Fix authentication bug in login flow")
- **description**: What needs to be done
- **activeForm** (optional): Present continuous form shown in the spinner when the task is in_progress (e.g., "Fixing authentication bug"). If omitted, the spinner shows the subject instead.

All tasks are created with status `pending`.

## Tips

- Create tasks with clear, specific subjects that describe the outcome
- After creating tasks, use TaskUpdate to set up dependencies (blocks/blockedBy) if needed
- Check TaskList first to avoid creating duplicate tasks
```

TaskUpdate（`kr`，`@135291`，节选）：

```text
## Status Workflow

Status progresses: `pending` → `in_progress` → `completed`

Use `deleted` to permanently remove a task.

## Staleness

Make sure to read a task's latest state using `TaskGet` before updating it.

## Examples

Mark task as in progress when starting work:
{"taskId": "1", "status": "in_progress"}
…
Set up task dependencies:
{"taskId": "2", "addBlockedBy": ["1"]}
```

**学习点**：`## Staleness` 一节专为多 agent 并发写——改之前先 `TaskGet`；示例用**最小可执行 JSON**，不写解释。

### 2.8 EnterPlanMode / ExitPlanMode / WebFetch / AskUserQuestion

EnterPlanMode（`_e()`，`chunks/c0978.js @2540`）：

```text
**Prefer using EnterPlanMode** for implementation tasks unless they're simple. Use it when ANY of these conditions apply:
…
### BAD - Don't use EnterPlanMode:
User: "Fix the typo in the README"
- Straightforward, no planning needed

User: "Add a console.log to debug this function"
- Simple, obvious implementation

User: "What files handle routing?"
- Research task, not implementation planning

## Important Notes

- This tool REQUIRES user approval - they must consent to entering plan mode
- If unsure whether to use it, err on the side of planning - it's better to get alignment upfront than to redo work
- Users appreciate being consulted before significant changes are made to their codebase
```

（受引段起点 `@2925`／`### BAD` `@5602`／`REQUIRES user approval` `@5897`。）

ExitPlanMode（`Ks`，`chunks/c0953.js @78306`，节选）——重点是消歧：

```text
## When to Use This Tool
IMPORTANT: Only use this tool when the task requires planning the implementation steps of a task that requires writing code. For research tasks where you're gathering information, searching files, reading files or in general trying to understand the codebase - do NOT use this tool.
…
**Important:** Do NOT use ${Gs} to ask "Is this plan okay?" or "Should I proceed?" - that's exactly what THIS tool does. ExitPlanMode inherently requests user approval of your plan.
```

（`@78306` 段内，`IMPORTANT: Only use…` `@78868`，`ExitPlanMode inherently…` `@79514`。）

WebFetch（`lWo()`/`El()`，`chunks/c0330.js @106037`/`@106873`）：

```text
IMPORTANT: WebFetch WILL FAIL for authenticated or private URLs. Before using this tool, check if the URL points to an authenticated service (e.g. Google Docs, Confluence, Jira, GitHub). If so, look for a specialized MCP tool that provides authenticated access.
…
Usage notes:
  - IMPORTANT: If an MCP-provided web fetch tool is available, prefer using that tool instead of this one, as it may have fewer restrictions.
  - The URL must be a fully-formed valid URL
  - HTTP URLs will be automatically upgraded to HTTPS
  - localhost and other hostnames without a dot are not supported; for a local server, use curl via Bash
  - This tool is read-only and does not modify any files
  - Results may be summarized if the content is very large
  - Includes a self-cleaning cache (entries expire after ${$Yn()}) for faster responses when repeatedly accessing the same URL
  - When a URL redirects to a different host, the tool will inform you and provide the redirect URL in a special format. You should then make a new WebFetch request with the redirect URL to fetch the content.
  - For GitHub URLs, prefer using the gh CLI via Bash instead (e.g., gh pr view, gh issue view, gh api).
```

AskUserQuestion（`BUr`，`chunks/c0522.js @1942`）：

```text
Use this tool only when you are blocked on a decision that is genuinely the user's to make: one you cannot resolve from the request, the code, or sensible defaults.

Usage notes:
- Users will always be able to select "Other" to provide custom text input
- Use multiSelect: true to allow multiple answers to be selected for a question
- If you recommend a specific option, make that the first option in the list and add "(Recommended)" at the end of the label

Plan mode note: To switch into plan mode, use ${lx} (not this tool). Once in plan mode, use this tool to clarify requirements or choose between approaches BEFORE finalizing your plan. Do NOT use this tool to ask "Is my plan ready?", "Should I proceed?", or otherwise reference "the plan" in questions — the user cannot see the plan until you call ${lb} for approval.
```

同文件 `z1o`（`chunks/c0522.js @3746`）：

```text
Reserve this for decisions where the user's answer changes what you do next — not for choices with a conventional default or facts you can verify in the codebase yourself. In those cases pick the obvious option, mention it in your response, and proceed.
```

Skill（`fXt`，`chunks/c0682.js @3271463`，末段）：

```text
Only names from the listing (or that the user typed explicitly) are valid. Built-in CLI commands (`/help`, `/clear`, …) aren't skills. If a `<${dp}>` block is already present this turn, the skill is loaded — follow it directly rather than calling again.
```

**学习点**：① `## BAD` 用**用户原话**当条目，比抽象描述更容易被匹配；② 用 `If unsure… err on the side of planning` 一个默认方向替代条件穷举；③ 明写两个易混工具的分工（ExitPlanMode vs AskUserQuestion）；④ `WILL FAIL`（而非 "may fail"）的确定性措辞减少试探；⑤ 每条限制必配出口（认证站→MCP、localhost→Bash curl、GitHub→`gh`）；⑥ 用**状态前置条件**防重复调用（skill 已加载就别再调）。

---

## 3. 工具描述里的写作手法清单

**统计口径**：语料 A = 24 个描述函数/字面量体内的全部字符串与模板字面量（≥12 字符）拼接，共 **52,451 字符**；语料 B = `grep -roF <pattern> raw/chunks/ | wc -l`（4060 chunk 全量）。

| 模式 | 语料 A | 语料 B | | 模式 | 语料 A |
|---|---|---|---|---|---|
| `IMPORTANT:` | 8 | 51 | | `"- "` 行首 bullet | 198 |
| `\bIMPORTANT\b` | 10 | — | | `"## "` 标题 | 13 |
| `NEVER` | 3 | 48 | | `When to/NOT to Use` | 8 |
| `ALWAYS` | 3 | 31 | | `e.g.` | 20 |
| `Do NOT` | 2 | 73 | | `Default`（任意形态） | 17 |
| `do not`/`Do not` | 11 | — | | `Only use` | 5 |
| `must`（不分大小写） | 19 | — | | `Prefer` | 5 |
| `MUST` | 4 | — | | `permission` | 11 |
| `instead of` | 3 | 387 | | `read-only`/`read only` | 3 |
| `FAIL`/`will fail`/`fails`/`will error` | 11 | — | | `absolute path` | 6 |
| `NOTE` | 2 | — | | `Use this tool` | 9（B:23） |

> 语料 B 的 `instead of` 含大量非工具文案（UI/错误提示），仅作量级参考。

**代表性原句 8 条**

1. 硬禁令 + 立即给理由：`ALWAYS use ${Jr} for search tasks. NEVER invoke `grep` or `rg` as a ${Ue} command. The ${Jr} tool has been optimized for correct permissions and access.`（`chunks/c0330.js @103789`）
2. 确定性失败预告：`IMPORTANT: WebFetch WILL FAIL for authenticated or private URLs.`（`chunks/c0330.js @106594`）
3. 前提条件防重复调用：`If a <${dp}> block is already present this turn, the skill is loaded — follow it directly rather than calling again.`（`chunks/c0682.js @3271463` 段末）
4. 反幻觉 + 正确动作：`Never fabricate or predict fork results in any format — not as prose, summary, or structured output. … give status, not a guess.`（`chunks/c0682.js @3317446`）
5. 小标题即禁令：`**Don't peek.**` / `**Don't race.**` / `**Never delegate understanding.**`（`@3317187`、`@3317446`、`@3318956`）
6. 完成定义可执行化：`Never mark a task as completed if: - Tests are failing - Implementation is partial - You encountered unresolved errors - You couldn't find necessary files or dependencies`（`chunks/c1006.js @63380`）
7. 授权写进描述：`This tool REQUIRES user approval - they must consent to entering plan mode`（`chunks/c0978.js @5897`）
8. 判据锚定：`The criterion is qualitative — "will I need this output again" — not task size.`（`chunks/c0682.js @3316227` 段内）

**手法表（可直接抄）**

| 手法 | 形式 | 为什么有效 |
|---|---|---|
| 硬约束三件套 | `ALWAYS` / `NEVER` / `IMPORTANT:` | 全大写在高密度文本里仍是视觉锚点；配理由后不易被当噪音丢弃 |
| 否决式小标题 | `## When NOT to Use This Tool`、`**Don't peek.**` | 先看到禁区，比埋在正向规则从句里命中率高 |
| 示例三段式 | `<example>` → 对话 → `<reasoning>` | reasoning 把"这次为什么不用"显式化，给出可迁移判据 |
| 失败前置 | `or the call will fail` / `WILL FAIL` | 把错误成本搬到决策点之前，省一次无效调用 |
| 错误即指令 | `Found N matches … set replace_all to true …` | 工具结果是下一步输入，写成"下一步动作"而非错误码 |
| 限制配出口 | `not supported; for a local server, use curl via Bash` | 每条禁止都给可行替代，避免卡死或绕路 |
| 状态机 + 括号消歧 | `Exactly ONE … (not less, not more)` | 堵住"多于一个行不行"的解释空间 |

---

## 4. input schema 的写法

统一用 `o()`=string、`C()`=number、`H()`=boolean、`B([...])`=enum、`T()`=array、`Ve({...})`=object，配 `.describe()`。**几乎每个字段都有 describe**，且同时写语义 + 默认值 + 字段间依赖 + 示例。

**Bash**（`Whr`，`chunks/c0682.js @3982194`，`grn` 在 `@3983788`）：

```text
command: o().refine(eO, jhr).describe("The command to execute")
timeout: CH(C().optional()).describe(`Optional timeout in milliseconds (max ${iO()} for a foreground command)`)
run_in_background: fT(H().optional()).describe(qdn())
dangerouslyDisableSandbox: fT(H().optional()).describe("Set this to true to dangerously override sandbox mode and run commands without sandboxing.")
_simulatedSedEdit: u({filePath:o(),newContent:o(),baseHash:o().optional()}).optional().describe("Internal: pre-computed sed edit result from preview")
```

- 校验失败文案直接讲安全理由：`jhr` = `"command contains control characters that would be hidden in the approval dialog"`（`chunks/c0682.js @3982108`）。
- `description` 字段的 describe 本身就是教程：`Clear, concise description of what this command does in active voice. Never use words like "complex" or "risk" in the description - just describe what it does.` + 正例 `ls → "List files in current directory"`、难解析命令正例 `git reset --hard origin/main → "Discard all local changes and match remote main"`。
- **schema 随环境变形**：`grn=f(()=>(Za()? mrn().omit({run_in_background:!0,_simulatedSedEdit:!0}) : mrn().omit({_simulatedSedEdit:!0})).superRefine(…)`——远程执行场景直接 `.omit()` 掉不允许的字段。

**Edit**（`QJ`，`chunks/c0682.js @710496`）：

```text
Ve({
  file_path: o().describe("The absolute path to the file to modify"),
  old_string: o().describe("The text to replace"),
  new_string: o().describe("The text to replace it with (must be different from old_string)"),
  replace_all: fT(H()).default(!1).optional().describe("Replace all occurrences of old_string (default false)"),
  ...sj()
})
```

约束三处一致：`.default(!1)` + `.optional()` + describe 的 `(default false)`；`(must be different from old_string)` 在 runtime 也有对应拒绝文案。

**Read**（`EKn`，`chunks/c0682.js @892123`）：

```text
Ve({
  file_path: o().describe("The absolute path to the file to read"),
  offset: CH(C().int().nonnegative().optional()).describe("The line number to start reading from. Only provide if the file is too large to read at once"),
  limit: CH(C().int().positive().optional()).describe("The number of lines to read. Only provide if the file is too large to read at once."),
  pages: o().optional().describe(`Page range for PDF files (e.g., "1-5", "3", "10-20"). Only applicable to PDF files. Maximum ${Y0e} pages per request.`),
  ...sj()
})
```

类型约束进 schema（`.int().nonnegative()`），**"什么时候才填"进 describe**（`Only provide if the file is too large to read at once`）——抑制无脑传参。同类写法见 Glob：`path: o().optional().describe('… IMPORTANT: Omit this field to use the default directory. DO NOT enter "undefined" or "null" - simply omit it for the default behavior. …')`（`chunks/c0682.js @923329`）。

**Grep**（`CVn`，`chunks/c0682.js @927515`，节选）：

```text
  pattern: o().describe("The regular expression pattern to search for in file contents"),
  glob: o().optional().describe('Glob pattern to filter files (e.g. "*.js", "*.{ts,tsx}") - maps to rg --glob'),
  output_mode: B(["content","files_with_matches","count"]).optional().describe('Output mode: … Defaults to "files_with_matches".'),
  "-B": CH(C().optional()).describe('Number of lines to show before each match (rg -B). Requires output_mode: "content", ignored otherwise.'),
  head_limit: CH(C().optional()).describe('Limit output to first N lines/entries, equivalent to "| head -N". … Defaults to 250 when unspecified. Pass 0 for unlimited (use sparingly — large result sets waste context).'),
  offset: CH(C().optional()).describe('Skip first N entries before applying head_limit, equivalent to "| tail -n +N | head -N". … Defaults to 0.'),
  multiline: fT(H().optional()).describe("Enable multiline mode where . matches newlines and patterns can span lines (rg -U --multiline-dotall). Default: false."),
```

每个字段标注与 rg 的对应（`(rg -B)`）；`Requires output_mode: "content", ignored otherwise.` 在 5 个字段上**刻意重复**，防止组合出无效参数；`Pass 0 for unlimited (use sparingly — …)` 用括号里的理由压制"传 0 更保险"。

**Agent**（`Io`/`amr`，`chunks/c0966.js @10295`、`@11663`）：

```text
name: o().regex(L4o,{message:"name must start with a letter or digit and contain only letters, digits, underscores, or hyphens (max 64 chars)"})
     .refine((e)=>e!==eg,{message:`"${eg}" is reserved — SendMessage routes it to the main conversation`})
     .refine((e)=>!nO(e),{message:'name must not be a reserved name ("main", "team-lead", "user" or "system", in any spelling) or have the shape of an agent id — those already address an agent directly'})
     .optional().describe("Name for the spawned agent. Makes it addressable via SendMessage({to: name}) while running.")
isolation: B(["worktree","remote"]).optional().describe('Isolation mode. "worktree" creates a temporary git worktree so the agent works on an isolated copy of the repo. "remote" launches the agent in a remote cloud environment (always runs in background; availability is gated).')
cwd: o().optional().describe('Absolute path to run the agent in. … Mutually exclusive with isolation: "worktree".')
run_in_background: H().optional().describe("Agents run in the background by default; you will be notified when one completes. Set to false only when your very next action depends on this agent's result and nothing else could usefully happen while it runs — otherwise leave it in the background so the user can hand you other work.")
```

校验消息面向模型而非开发者（明说替代路径 `SendMessage routes it to the main conversation`）；互斥关系写进 describe；`amr` 里 schema **随 feature flag 裁剪**：`CLAUDE_CODE_SUBAGENT_MODEL_FORCE? h.omit({model:!0}) : h`、`h=e? n.omit({run_in_background:!0}) : …`。

**TaskCreate / TaskUpdate**（`Ns` `@131558`、`js` `@137593`）：

```text
subject: o().describe("A brief title for the task"),
description: o().describe("What needs to be done"),
activeForm: o().optional().describe('Present continuous form shown in spinner when in_progress (e.g., "Running tests")'),
metadata: de(o(),se()).optional().describe("Arbitrary metadata to attach to the task")
```

```text
taskId: o().describe("The ID of the task to update"),
status: e.optional().describe("New status for the task"),
addBlocks: T(o()).optional().describe("Task IDs that this task blocks"),
addBlockedBy: T(o()).optional().describe("Task IDs that block this task"),
metadata: de(o(),se()).optional().describe("Metadata keys to merge into the task. Set a key to null to delete it.")
```

`(e.g., "Running tests")` 一个例子锁死"现在进行时"；删除语义写在字段说明里（`Set a key to null to delete it.`）；`status` 用 `vRe().or(x("deleted"))` 拼装，对应描述里那句 `Use deleted to permanently remove a task.`

**共性套路**：① 每字段必有 describe；② 必填靠"不加 `.optional()`"；③ 枚举一律 `.optional()` + 在 describe 点名默认分支；④ 互斥/依赖明写，不靠推断；⑤ schema 是活的（`.omit/.extend/.refine/superRefine` 按 flag、平台、远程能力裁剪）；⑥ 校验失败消息写给模型看。

---

## 5. 未验证 / 读不到的部分

1. **`Wt` 包装器本体未定位**：`Wt` 从 `/$bunfs/root/chunk-1b21she7.js` 导入（见 `chunks/c2674.js` 头部），carve 出的 chunk 无法直接映射到 bun 内部 chunk 名，故 `isReadOnly`/`isConcurrencySafe` **未声明时的默认值无法确认**；表中这类一律标 `-`。
2. **`Schedule`/`Worktree`/`SlashCommand`/`MCP` 作工具名**：全语料未找到对应工具定义对象，表中未列。
3. **`MultiEdit`/`NotebookRead`**：只出现在权限规则分组与兼容名单（`chunks/c3520.js @17273`），**不能确认**在本 build 注册为工具（倾向历史名保留，属推断）。
4. **Artifact 家族**：`mn="Artifact"`、`Ly="ArtifactComments"`、`Om="ArtifactData"`、`Hx="ArtifactCheck"` 四者的名字在 `chunks/c0186.js @12467` 定死，但只有 Artifact 的工具对象位置较明确，其余三个的对象未逐个定位（`chunks/c0682.js @996223` 的遥测映射中出现）。
5. **工具总数口径**：`Wt({` 共 93 处，82 处可配平截出对象，约 70 个能解析出工具名。"实际注册数"还受 `isEnabled()`、`shouldDefer`、企业版/`ant` 分支、平台（`O()==="windows"`）影响，**本表不等于运行时下发给模型的最终工具列表**。
6. `chunks/c2956.js` 的 9 个 `self_hosted_runner_*` 只在该 chunk 出现，**未验证**其 UI/权限接线。
7. 语料 A 的统计依赖"描述体"的人工定位，若某工具描述由多处拼接（如 Bash 的 `Yht` 走 `Sm()` 组装），统计只覆盖模板/字符串字面量本身，**不含运行时插入内容**。

---

## 6. 对我们的启发

1. **抄「工具对象 + 双份描述」结构**：固定 `name / searchHint / description / prompt / inputSchema / isReadOnly / isConcurrencySafe / backgrounding`，描述分 lean 与 full（`chunks/c0682.js @968032` vs `@970920`）。同一真理源切粗细，不维护两套文案。
2. **抄 `IMPORTANT: Avoid using this tool to run X … Instead, use the appropriate dedicated tool`**：万能工具最容易吃掉专用工具使用率；把替代关系**逐条列出**（`Read files: Use Read (NOT cat/head/tail)`）比系统提示里泛泛一句有效得多（`chunks/c0682.js @968288`）。
3. **抄「失败前置」+「错误即下一步」**：Edit 把 9 类失败写成含恢复动作的自然语言（`chunks/c0682.js @3832818` 附近）。写工具时把 error message 当 prompt 写。
4. **抄 `When NOT to Use This Tool` 对称结构 + `<example>/<reasoning>`**：reasoning 是把判据显式化的关键，成本极低（`chunks/c1006.js @55978` 起）。
5. **抄「小标题即禁令」**：`**Don't peek.**`、`**Don't race.**`、`**Never delegate understanding.**`（`chunks/c0682.js @3317187`、`@3317446`、`@3318956`），用于所有异步/并发场景的反幻觉条款。
6. **抄「限制必配出口」**：WebFetch 每条限制后跟替代方案（认证站→MCP、localhost→Bash curl、GitHub→`gh`）（`chunks/c0330.js @106594`、`@106873`）。禁止而不给出口会让 agent 空转。
7. **抄「用默认方向替代条件穷举」**：`If unsure whether to use it, err on the side of planning`（`chunks/c0978.js @5897` 附近）；`If you recommend a specific option, make that the first option in the list and add "(Recommended)"`（`chunks/c0522.js @1942`）。
8. **抄「schema 是活的」**：同一工具 schema 按平台/远程/flag 用 `.omit()/.extend()/.refine()` 变形（`chunks/c0682.js @3983788`、`chunks/c0966.js @11663`），而不是在描述里写"某些情况下此字段无效"。
