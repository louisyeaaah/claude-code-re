# 步骤 2 · 动态验证：抓一次真实请求，与静态还原对照

> 目的：静态分析给出的是"装配代码 + 各块原文"，本步骤用**真实发出去的请求体**验证它，并抓出静态推断错的地方。
> 产物：`verify/captured/`（原始请求体）、`verify/comparison.json`、本报告。

## 1. 方法（不碰真实凭据、不产生任何外部请求）

```bash
# 1) 本地拦截服务器：只落盘请求体，然后返回 400，不转发
python3 verify/capture_server.py 18787 captured

# 2) 用独立配置目录 + 假密钥 + 指向本地的 base URL 跑一次 CLI
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
  CLAUDE_CONFIG_DIR=.../verify/cfg \
  ANTHROPIC_BASE_URL=http://127.0.0.1:18787 \
  ANTHROPIC_API_KEY=sk-ant-dummy-key ANTHROPIC_AUTH_TOKEN=dummy-token \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_TELEMETRY=1 DISABLE_ERROR_REPORTING=1 \
  ~/.local/share/claude/versions/2.1.287 -p "reply ok"
```

安全边界：`CLAUDE_CONFIG_DIR` 指向工作区内的空目录（读不到 `~/.claude` 的凭据与配置）；密钥是假串；`ANTHROPIC_BASE_URL` 指向 127.0.0.1，**请求从未离开本机**（服务器收到即返回 400）。CLI 侧的报错就是 `API Error: 400 captured locally; not forwarded`。

## 2. 抓到了什么

| 变体 | 触发方式 | system 块 | system 字符数 | 工具数 |
|---|---|---|---|---|
| **lean**（默认） | 直接 `-p` | 3 | 5,789 | 20 |
| **full** | 加 `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT=0` | 3 | 26,950 | 20 |

两者模型字段都是 `claude-opus-5-5`（本机 CLI 默认模型），请求体约 66~76 KB，含 `context_management`、`thinking`、`safeguards`、`output_config` 等字段。

**两次请求的三个 system 块**（顺序与 cache_control 完全一致）：

```
block0        74 B  cache_control=None          'x-anthropic-billing-header: cc_version=2.1.287.1f9; cc_entrypoint=sdk-cli;'
block1        62 B  cache_control={ephemeral}   "You are a Claude agent, built on Anthropic's Claude Agent SDK."
block2  5,681/27,078 B  cache_control={ephemeral}  '\nYou are an interactive agent that helps users ...'
```

即：**最易变的计费头单独成第一块且不缓存**、身份单独一块、其余全部合进第三块——与静态分析（05 §2）一致。

## 3. lean / full 的开关就写在代码里，并被实机验证

装配处（`raw/chunks2/0374__chunk-mphp7acd.js` @1447722）：

```js
be = g ? [["lean_body", Wao(j,n)]]
       : [["intro",Iao(j)],["system",Lao(n)],["doing_tasks",…Nao()],["actions",Fao()],["tools",Bao(z)],["tone",jao()]];
```

`g = AG(model)`，而 `Ao()` 的判定里有 `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT`：真值 → lean，`"0"/"false"/"no"/"off"` → 强制 **full**。实机结果与代码预测一致（5,789 → 26,950 字符）。

## 4. 逐条对照结果

### 4.1 命中（动态确认了静态结论）

| 静态结论 | 动态证据 |
|---|---|
| 6 个静态块的存在与标题 | full 版实测出现 `# System`、`# Doing tasks`、`# Executing actions with care`、`# Using your tools`、`# Tone and style`，标题与顺序与装配代码一致 |
| 身份三变体 | block1 实测为 SDK 变体 `You are a Claude agent, built on Anthropic's Claude Agent SDK.`（`-p` 非交互路径），CLI 变体 `Qw` 未出现——与代码分支一致 |
| 安全基线（vMe）逐字存在 | ✓ 逐字命中 |
| 计费头单独成首个不缓存块 | ✓ block0 无 `cache_control` |
| 工具描述**双份**（lean/full） | ✓ 同一批 20 个工具、描述长度随模式变化：Bash 1,097 → 9,438、Agent 1,668 → 6,926、Read 790 → 1,782、WebFetch 469 → 1,608、WebSearch 334 → 1,344（其余不变） |
| `# Harness` 属于 lean 体 | ✓ 只出现在 lean 版；full 版无 `# Harness`，对应内容并入 `# System` |
| `# Context management` / `# Environment` / `# auto memory` 是动态块 | ✓ 两个版本里都有（`# auto memory` 带 6 个子节） |
| `# Text output` 是条件块 | ✓ 仅 full 版出现 |
| 工具清单受开关裁剪 | ✓ 只有 20 个工具；静态语料里存在的 `TodoWrite/TaskCreate/TaskUpdate/TaskList`（`CLAUDE_CODE_ENABLE_TODO_TOOLS` 关闭）、`Glob/Grep`、`EnterPlanMode/ExitPlanMode`、`AskUserQuestion` 等均未下发 |

### 4.2 纠正（静态推断错了的地方）

**system-reminder 说明的第三档变体，触发条件不是"协调器/后台模式"。**

真实请求里 `# System` 的对应句是：

```
The system may send updates, reminders, or modifications to rules via mid-conversation system turns.
These are system-controlled, unlike function results.
```

静态代码是 `function Dao(e){return p8(e)&&!xQn(e)&&!ujo(Be(e))}`，其中 `p8(e)` 读的是模型的 `midConversationSystem` 能力位、`ujo(e)` 排除 `claude-opus-4-8`。也就是说这一档由**模型是否支持"中途系统消息"**决定，与 coordinator/后台无关。原先 `01-system-prompt.md` §3.1 的归因已按此更正。

### 4.3 未出现但已解释

- `# Writing for the user`（"No em-dashes, no parentheticals, no arrows" 那一套）在两种模式下都没出现——它是按客户端/载体条件注入的，`-p` 场景不满足。
- `# Focus mode`、`# Background Session`、`# Machines`、`# Language`、自主运行追加块等未出现，符合"按运行形态注入"的设计。
- 个人化的 `# Session-specific guidance` 与 `# Memory` 内容随配置目录（空配置）而不同。

## 5. 覆盖度量化

把 `extracted/01-system-prompt.md` 里所有 fenced 引用块中的英文原文行（129 行）与本次 full 请求逐字比对：**70 行逐字命中（54%）**；未命中的 59 行集中在三类：① `# Writing for the user` 整块（本场景不注入）；② 只在 lean 体出现的 `# Harness` 各条；③ 被 `...` 省略或含 `${}` 插值的行。命中率受场景影响，不能用它衡量还原正确性；**正确的判据是"该出现的都出现了、该缺席的都有缺席理由"**。

## 6. 未能验证的部分

- **交互式 TUI 模式**：沙箱禁止 `openpty`（`script: openpty: Operation not permitted`），无法跑真正的交互式会话；因此 CLI 变体身份句（`Qw`）与交互路径下的完整块组合**未实测**。
- **`scope:"global"` 缓存档**：本机 base URL 指向 localhost，不属于 first-party（`gr` 为假），实测只出现 `{type:"ephemeral"}`，与代码预测一致，但 global 档本身未被触发。
- 模型/账号相关分支（如 `claude-opus-4-8` 排除项）无法在本机遍历。

## 7. 复现

```bash
cd verify
python3 capture_server.py 18787 captured &          # 本地拦截
# 另开一个终端，按 §1 的命令跑两次：一次默认（lean）、一次带 CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT=0（full）
ls captured/full/86400                                # 原始请求体
python3 compare_prompt.py                             # 生成 comparison.json
```

原始请求体（`captured/*.body.json`）已脱敏：其中只有假密钥与本地地址，无任何真实凭据。
