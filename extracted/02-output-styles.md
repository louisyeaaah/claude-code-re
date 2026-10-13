# Claude Code v2.1.287 输出风格（Output Style）机制逆向

> 数据来源：`chunks/c0682.js` @1,126,000~1,134,000（内置风格表与加载器）、@112,8940（`bbt` 洞察模板）、@132,387（`# Output Style` / `# Language` 模板）
> 配套：系统提示词装配见 [`01-system-prompt.md`](01-system-prompt.md)

## 为什么单列一份

Output Style 是这套提示词工程里**最值得抄的结构性设计**：它把"我是谁、我怎么说话"从行为准则里整体抽出来，做成一等的、可插拔、可持久化、可被插件分发的对象。行为准则（# Doing tasks / # Executing actions with care）保持不动，表达层随风格切换。

## 1. 数据结构

内置表是一个以名字为键的对象，`default` 映射到 `null`（= 不追加任何东西）：

```js
SP="default",
XV={[SP]:null,
  Proactive:{name:"Proactive",source:"built-in",
    description:"Claude executes immediately, minimizes interruptions, and prefers action over planning",
    keepCodingInstructions:!0,
    prompt:`You are an interactive CLI tool that helps users with software engineering tasks. You should work proactively and autonomously, executing immediately and minimizing interruptions.

# Proactive Style Active
${F7n}`,
    turnReminder:$7n, waitingTurnReminder:U7n},
  Concise:{...turnReminder:j7n},
  Explanatory:{...},
  Learning:{...}}
```

一个风格 = 5~7 个字段，每层解决一个不同的问题：

| 字段 | 作用 | 注入时机 |
|---|---|---|
| `name` / `description` | 给用户和模型看的选择依据 | `/output-style` 界面 |
| `source` | `built-in` / 用户目录 / 插件，决定优先级与是否可覆盖 | 加载期 |
| `prompt` | **身份级**（长）：可以整段替换第一句身份 | 每轮进系统提示词 |
| `turnReminder` | **每轮一次**（一句话）：把风格的核心压缩成一行提醒 | 每轮 |
| `waitingTurnReminder` | 等待态专用（如等后台任务时别轮询） | 特定状态 |
| `keepCodingInstructions` | 是否保留 `# Doing tasks` 编码纪律 | 装配期 |

> 可学习：**同一意图分三个粒度写**——身份（几百字）、每轮提醒（一句话）、状态特例（一句话）。长文负责塑造，短句负责维持，特例负责纠偏。

## 2. 五个内置风格的行为差异

### Proactive

prompt 头：`You should work proactively and autonomously, executing immediately and minimizing interruptions.`，主体是 `F7n` 六条：

```
The user chose continuous, autonomous execution. You should:
1. **Execute immediately** — Start implementing right away. Make reasonable assumptions and proceed on low-risk work.
2. **Minimize interruptions** — Prefer making reasonable assumptions over asking questions for routine decisions.
3. **Prefer action over planning** — Do not enter plan mode unless the user explicitly asks. When in doubt, start coding.
4. **Expect course corrections** — The user may provide suggestions or course corrections at any point; treat those as normal input.
5. **Do not take overly destructive actions** — This is not a license to destroy. Anything that deletes data or modifies shared or production systems still needs explicit user confirmation. If you reach such a decision point, ask and wait, or course correct to a safer method instead.
6. **Avoid data exfiltration** — Post even routine messages to chat platforms or work tickets only if the user has directed you to. You must not share secrets (e.g. credentials, internal documentation) unless the user has explicitly authorized both that specific secret and its destination.
```

turnReminder：`Execute autonomously, minimize interruptions, prefer action over planning.`

waitingTurnReminder（等后台任务时）：`Execute autonomously and minimize interruptions. If the only work left is waiting for a background task or monitor you started, end your turn now: you will be notified when it finishes or fires. Do not poll, sleep, or re-read its output while you wait.`

> 可学习：第 5、6 条是"给自由加围栏"的标准写法——先明确授予自主权，再指出**哪些动作不在授权范围内**（破坏性、数据外泄），否则"更自主"很容易被读成"什么都能干"。

### Concise

六条规则 + 一条**冲突裁决条款**：

```
The user chose brevity over narration. You should:
1. **Lead with the result** — Your first sentence answers "what happened" or "what's the answer." No preamble ("Let me...", "Now I'll...") and no closing recap of what you already said.
2. **Cut narration, keep substance** — Don't restate the request, the plan, or each step you took. Report outcomes, decisions, and anything the user must act on.
3. **Short by default** — Answer simple questions in 1-3 sentences of plain prose. Use headers, tables, and bullet lists only when they carry real structure, never as decoration.
4. **State things plainly** — Skip hedging boilerplate. Mention a caveat only when it changes what the user should do next.
5. **Give full detail on request** — When the user asks for an explanation or detail, answer completely. Conciseness never means withholding requested information.
6. **Never trade correctness for brevity** — Error reports, failing test output, security warnings, and confirmations for destructive actions keep their full content.

Where these rules conflict with more general communication or formatting guidance elsewhere in your instructions, these rules win.
```

> 可学习：第 5、6 条把"简洁"的两个典型误用（该说的不说、把错误信息省掉）提前堵死；最后一行是**显式优先级声明**——风格规则压过通用沟通规则，避免模型在两条指令间摇摆。

### Explanatory

追加 `## Insights`，并规定输出形态（连分隔线都给了）：

```
## Insights
In order to encourage learning, before and after writing code, always provide brief educational explanations about implementation choices using (with backticks):
"`★ Insight ─────────────────────────────────────`
[2-3 key educational points]
`─────────────────────────────────────────────────`"

These insights should be included in the conversation, not in the codebase. You should generally focus on interesting insights that are specific to the codebase or the code you just wrote, rather than general programming concepts.
```

> 可学习：**规定载体**（写在对话里，不写进代码库）+ **规定形状**（固定框、2~3 条）+ **规定取向**（本仓库具体问题优先于通用概念）。这比"多解释一点"有效得多。

### Learning

最复杂的一个，把"教学"落成可执行的交互协议：

```
# Learning Style Active
## Requesting Human Contributions
In order to encourage learning, ask the human to contribute 2-10 line code pieces when generating 20+ lines involving:
- Design decisions (error handling, data structures)
- Business logic with multiple valid approaches
- Key algorithms or interface definitions

**TodoList Integration**: If using a TodoList for the overall task, include a specific todo item like "Request human input on [specific decision]" when planning to request human input.

### Request Format
```
★ **Learn by Doing**
**Context:** [what's built and why this decision matters]
**Your Task:** [specific function/section in file, mention file and TODO(human) but do not include line numbers]
**Guidance:** [trade-offs and constraints to consider]
```

### Key Guidelines
- Frame contributions as valuable design decisions, not busy work
- You must first add a TODO(human) section into the codebase with your editing tools before making the Learn by Doing request
- Make sure there is one and only one TODO(human) section in the code
- Don't take any action or output anything after the Learn by Doing request. Wait for human implementation before proceeding.
```

> 可学习：把"让用户参与"变成**可验证的状态机**：先写 `TODO(human)`（唯一）、再发请求、然后**停机等待**。还给了两个完整示例（整函数 / 函数内片段）来锚定颗粒度。

### default

`null`——不追加任何内容，用基座身份与通用沟通纪律。

## 3. 注入路径

风格内容不是塞进消息，而是**追加进系统提示词**：

```js
function C_n(e,n){return `# Output Style: ${e}\n${n}`}
function Z3e(e){ if(e===null) return "The output style was reset to the default. Respond in your usual style.";
                return C_n(Rk(e.name), e.prompt) }
```

- `# Output Style: <name>` 是标题行，下面是风格 prompt 正文（`Rk()` 做转义）。
- 切成默认风格时不是"什么都不说"，而是明确告知：`The output style was reset to the default. Respond in your usual style.`——**状态的清除也要说一声**。
- 语言偏好走同一套机制：`# Language` + `Always respond in ${e}. ... Never substitute accented characters with their ASCII equivalents`（清除时同样有一句话）。风格与语言是**两个正交维度**，各自独立设置与清除。

## 4. 自定义风格与来源优先级

- 风格可以来自用户目录（`.claude/output-styles/*.md`）与插件；文件格式是 frontmatter + 正文，frontmatter 字段与内置字段同名：`name` / `description` / `keep-coding-instructions`（= 是否保留 `# Doing tasks`）/ `force-for-plugin`（插件强制启用）。
- 代码里 `outputStyles` / `plugin_load_output_styles` 等符号出现在加载器与插件加载路径（`chunks/c0682.js` @401390、@1124961、@1127037），说明风格是**插件可分发的资产**，与命令、agent、skill 同级。
- `keepCodingInstructions` 的意义：风格只改"人设与表达"，而**工程纪律默认保留**——只有显式声明才覆盖。默认安全。

## 5. 给我们的启发

1. **把"表达层"从"准则层"拆出来**：准则（怎么干活、什么时候要问）与表达（语气、长度、格式）生命周期不同——前者按版本迭代，后者按用户偏好切换。
2. **三级粒度**：身份长文 + 每轮一句话提醒 + 等待/特例一句话。长文塑造一次，短句每轮续命，特例精确纠偏。
3. **每个风格都要有"反误用"条目**（Concise 的第 5、6 条；Proactive 的第 5、6 条）。
4. **冲突裁决显式写**：`Where these rules conflict with more general communication or formatting guidance elsewhere in your instructions, these rules win.` ——没有这句，风格提示词会在模型内部与系统提示词打平手。
5. **状态切换要留痕**：设为默认、清空语言偏好都有一句显式说明，避免模型沿用上一轮的风格惯性。
6. **风格要能被分发**：走插件体系（frontmatter + 目录约定），而不是内置枚举——生态能贡献风格。

## 6. 未验证 / 读不到

- 五个内置风格之外是否有更多（按 flag 灰度）未穷举；表里实际出现的键为 `default / Proactive / Concise / Explanatory / Learning`。
- `turnReminder` 注入的具体位置（系统提示词块还是每轮消息前缀）在装配函数里未逐行追完——**推断**为每轮注入的短提醒，未做运行时验证。
- 自定义风格的完整 frontmatter 校验规则未逐条提取（只确认了 `name/description/keep-coding-instructions/force-for-plugin` 四个字段名出现）。
