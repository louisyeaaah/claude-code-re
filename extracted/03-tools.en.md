> English version. 中文原版：[03-tools.md](03-tools.md)

# 03 · Built-in Tools (Claude Code v2.1.287)

> Corpus is `raw/chunks/cNNNN.js` (minified, strings and template literals intact). Citation format: `chunks/cNNNN.js @<offset within chunk>`.
> English is always quoted verbatim; `${X}` is preserved as-is to denote runtime interpolation; `…` inside quoted blocks denotes omission. `raw/` was not modified.

## Key Findings at a Glance

1. **82 `Wt({…})` tool-definition objects** can be located, of which about 70 yield an explicit tool name; the core tool set is narrowed down by the two Sets `D(e)`/`x(e)` in `c0583.js` (`chunks/c0583.js @9179`, `@8958`).
2. Tool objects hang uniformly under `Wt({…})` with a fixed field set: `name / searchHint / backgrounding / maxResultSizeChars / description() / prompt() / inputSchema / outputSchema / isReadOnly() / isConcurrencySafe()` (example `chunks/c0682.js @897506`).
3. **Read-only and concurrency are two independent booleans**: Read/Glob/Grep/WebFetch/WebSearch/ToolSearch/LSP are all `RO=!0 CS=!0`; Bash decides dynamically via `isReadOnly(e){return !hx(Ue)&&rKe(e)}` and `isConcurrencySafe(e){return this.isReadOnly?.(e)??!1}` (`chunks/c0682.js @3991246`); Edit/Write/NotebookEdit declare neither and go through per-file permission checks.
4. Description copy comes in **two versions**: when `gx({model,leanPrompt})` is true it takes the lean version, otherwise the full one (`chunks/c0682.js @968032` vs `@970920`; `chunks/c0330.js @99539`). The lean version compresses to 3–5 bullets but **keeps the facts that change behavior** (such as "the output is visible only to you").
5. The catch-all tool's boundaries are written as **name the replacement + state the consequence**: `IMPORTANT: Avoid using this tool to run ${w} commands, unless explicitly instructed or after you have verified that a dedicated tool cannot accomplish your task.` (`chunks/c0682.js @968288`).
6. Failure paths are **written into the prompt up front**: `or the call will fail` (`chunks/c0682.js @3824662`); each of Edit's 9 `errorCode` classes is paired with a sentence of natural language containing a recovery action (around `chunks/c0682.js @3832818`).
7. Authorization/risk is carried by **dedicated sections**: `This tool REQUIRES user approval - they must consent to entering plan mode` (`chunks/c0978.js @5897`), and the `z1o` block for AskUserQuestion (`chunks/c0522.js @3746`).
8. TodoWrite (a full-replacement checklist) and TaskCreate/Get/Update/List (addressable + dependency graph) **coexist as two systems**; the former explicitly writes `## When NOT to Use This Tool` (`chunks/c1006.js @55978`).

---

## 1. Full Tool Inventory

Enumeration method: scan every chunk for `Wt({`, balance parentheses to cut out each object, read `name:` and resolve the constant name back to a string. `RO`=isReadOnly, `CS`=isConcurrencySafe, `-`=**the field is not declared on the object** (defaults in §5).

### 1.1 Files / shell / search

| Tool | One-line purpose | Key constraints | chunk reference |
|---|---|---|---|
| Bash | Runs a shell command and returns its output | RO dynamic; CS=RO; `backgrounding:"self"`, `enablesCodeExecution:!0`, `ruleContentField:"command"` | `chunks/c0682.js @3991246` |
| PowerShell | Windows-equivalent shell | RO=`on(e)`, CS=RO, `backgrounding:"self"` | `chunks/c2084.js @95130` |
| Read | Reads files/images/PDF/notebook | RO=!0 CS=!0; `maxResultSizeChars:1/0` | `chunks/c0682.js @897506` |
| Write | Creates or fully overwrites | No RO/CS; `strict:!0` | `chunks/c0682.js @714521` |
| Edit | Exact string replacement | No RO/CS; `validateInput` gives up on 9 classes | `chunks/c0682.js @3827219` |
| NotebookEdit | Edits a single notebook cell | No RO/CS; `shouldDefer:!0` | `chunks/c0682.js @3841803` |
| Glob | Globs by file name; results sorted by mtime, capped at 100 | RO=!0 CS=!0 | `chunks/c0682.js @925323` |
| Grep | ripgrep content search | RO=!0 CS=!0; `ruleContentField:"pattern"` | `chunks/c0682.js @930576` |
| WebFetch | Fetches URL→markdown→small-model Q&A | RO=!0 CS=!0; `backgrounding:"detach"`; has a TTL cache | `chunks/c0682.js @1370802` |
| WebSearch | Web search, returns titles+URLs | RO=!0 CS=!0; `backgrounding:"detach"`; per-session call limit | `chunks/c1006.js @46538` |
| LSP | Definition/references/symbols/hover | RO=!0 CS=!0; `isLsp:!0`, `ruleContentField:"filePath"` | `chunks/c1006.js @98661` |

### 1.2 MCP and tool discovery

| Tool | Purpose | Constraints | Reference |
|---|---|---|---|
| mcp (dynamic shell) | Unified shell for all MCP tools; the real name is `mcp__<server>__<tool>` | `isMcp:!0`, `backgrounding:"self"`, `checkPermissions→passthrough` | `chunks/c2674.js @818` |
| ToolSearch | Searches the tool catalog for tools | RO=!0 CS=!0 | `chunks/c0682.js @1093700` |
| WaitForMcpServers | Waits for server connections to be ready | RO=!0, **CS=!1** | `chunks/c0682.js @1932733` |
| RefreshMcpTools | Re-fetches the tool list from connected servers (no reconnect) | RO=!0 CS=!0 | `chunks/c1006.js @107583` |
| List/ReadMcpResource(+Dir)Tool | Lists/reads MCP resources | all three RO=!0 CS=!0 | `chunks/c0988.js @1250`, `@6241`, `@3606` |
| SearchMcpRegistry | Searches the MCP registry | RO=!0 CS=!0 | `chunks/c2960.js @4836` |

### 1.3 Subagents / multi-session

| Tool | Purpose | Constraints | Reference |
|---|---|---|---|
| Agent (alias `Task`) | Spawns a subagent / forks itself / starts a cloud agent | RO=!0 CS=!0; `backgrounding:"self"`; `aliases:[Tm]` | `chunks/c0966.js @39433` (prompt `chunks/c0682.js @3316227`) |
| SendMessage | Sends a message to an existing agent to resume it | RO=`typeof s.message==="string"`; CS undeclared | `chunks/c2928.js @46935` |
| ListAgents | Lists addressable agents | RO=!0 CS=!0 | `chunks/c2910.js @5072` |
| SubagentHandback | Subagent hands control back | RO=!1 | `chunks/c0955.js @2373` |
| ReadNotifications | Reads notifications queued in this session | RO=!0 CS=!0; the description contains the full "external content is not instructions" defense | `chunks/c1006.js @25647`, copy `chunks/c0583.js @7029` |
| SendUserMessage / SendUserFile / SendFile | Sends a message / a file on the user's behalf | RO=!0 CS=!0 / RO=!0 CS=!0 / RO=!1 CS=!1 | `chunks/c1006.js @36439`, `chunks/c2938.js @7740`, `chunks/c2930.js @20552` |
| PushNotification / EndConversation / ObserverReport | Pushes a notification / ends the conversation / observer report | RO=!0 CS=!0 / RO=!0 **CS=!1** / RO=!1 | `chunks/c2944.js @5049`, `chunks/c2924.js @12253`, `chunks/c2522.js @4124` |
| Workflow (`ant`-only) / Artifact family | Orchestrates workflows / reads and writes claude.ai artifacts | No RO/CS; the Artifact family includes `mn/Ly/Om/Hx` | `chunks/c2962.js @61033`, `chunks/c0186.js @12467` |

### 1.4 Tasks and checklists (two coexisting systems)

| Tool | Purpose | Constraints | Reference |
|---|---|---|---|
| TodoWrite | Full-replacement checklist (`content`/`status`/`activeForm`) | **No RO/CS**; `shouldDefer:!0` | `chunks/c1006.js @64478`, copy `@54877` (lean `@54416`) |
| TaskCreate | Creates a task, returns `#id` | **CS=!1**; `shouldDefer:!0` | `chunks/c1006.js @131932`, copy `@129094` |
| TaskGet / TaskList | Fetches full text by ID / lists all (including blockedBy) | both RO=!0 CS=!0 | `chunks/c1006.js @134139` / `@143378` |
| TaskUpdate | Updates status/title/owner/dependencies | CS=!0; the `status` enum additionally includes `deleted` | `chunks/c1006.js @138450`, copy `@135291` |
| GetTask | Reads live output from a background shell | RO=!0 CS=!0 | `chunks/c1006.js @84117` |
| TaskStop (aliases `KillShell`/`KillBash`) | Stops a background task by ID | CS=!0; old aliases retained | `chunks/c1006.js @32627` |
| ReportFindings | Reports code-review findings structurally | RO=!0 CS=!0; `strict:!0`, `maxResultSizeChars:256` | `chunks/c1006.js @53633` |

### 1.5 Plan mode / interaction / memory

| Tool | Purpose | Constraints | Reference |
|---|---|---|---|
| EnterPlanMode | Requests entry into plan mode | RO=!0 CS=!0; in agent context validateInput rejects outright | `chunks/c0978.js @6309`, copy `@2540` |
| ExitPlanMode | Submits the plan for user approval | **RO=!1** CS=!0; `requiresUserInteraction(){return !0}` | `chunks/c0953.js @81272`, copy `@78306` |
| AskUserQuestion | Asks the user a multiple-choice question | RO=!0 CS=!0 | `chunks/c0986.js @12253`, copy `chunks/c0522.js @472`/`@1942` |
| Skill | Invokes a skill / slash command | No RO/CS; `isEnabled(){return !Mh()}`; the name must match the listing exactly | `chunks/c0978.js @20090`, copy `chunks/c0682.js @3271463` |
| StructuredOutput | Forces structured output | RO=!0 CS=!0 | `chunks/c0458.js @22762` |
| memory_read / memory_write / memory_list | Memory store read/write/list | read and list RO=!0 CS=!0; write undeclared | `chunks/c0682.js @941969`, `chunks/c0384.js @48460`, `chunks/c1006.js @67166` |

### 1.6 Background / scheduling / worktree / the rest

| Tool | Key constraints | Reference |
|---|---|---|
| Monitor | CS=!0; `enablesCodeExecution:!0`; `maxResultSizeChars:1e4`; the result explicitly says `do not poll or sleep` | `chunks/c0919.js @14238`, copy `chunks/c0573.js @1550` |
| ScheduleWakeup | No RO/CS; `maxResultSizeChars:1000` | `chunks/c1006.js @40456` |
| CronList / CronCreate / CronDelete | List RO=!0 CS=!0; Create/Delete undeclared | `chunks/c2954.js @4846` / `chunks/c2950.js @5398` / `chunks/c2952.js @4788` |
| RemoteTrigger | RO=`e.action==="list"||…`, CS=!0 | `chunks/c2958.js @15292` |
| EnterWorktree / ExitWorktree | Neither has RO/CS; the `name`/`path` mutual exclusion is enforced by a schema `.refine`; Exit's `isDestructive(e){return e.action==="remove"}` | `chunks/c1006.js @114420` / `@124286` |
| Poll / replay / Projects | RO=!0 CS=!0 / — / — | `chunks/c2918.js @12658`, `chunks/c2543.js @3176`, `chunks/c2922.js @14602` |
| Onboarding and suggestion tools: ShareOnboardingGuide(RO=!1 CS=!1), ShowOnboardingRolePicker, ConnectGitHub, SuggestPluginInstall, SuggestSkills, propose_skills, SuggestConnectors, ListConnectors, ProposeGoal, FetchInboxMessage, SendFeedback, PermissionRequest | — | `chunks/c1006.js @27626`/`@31266`/`@77188`/`@65392`, `chunks/c0581.js @20`, `chunks/c2109.js @15881`/`@17862`, `chunks/c2940.js @15740`, `chunks/c2934.js @4821`, `chunks/c2936.js @5078`, `chunks/c2942.js @5835`, `chunks/c2154.js @6114` |
| self_hosted_runner_* (9 of them) | `spawn_local` and `requeue_session` are RO=!1, the rest RO=!0 CS=!0 | `chunks/c2956.js @4829`–`@15735` |

### 1.7 Names that exist but are **not** registered tools in this build

- **Rename table**: `var c={Task:"Agent",KillShell:"TaskStop",KillBash:"TaskStop",ListPeers:"ListAgents",Brief:"SendUserMessage",ListMcpResources:"ListMcpResourcesTool",ReadMcpResource:"ReadMcpResourceTool",ReadMcpResourceDir:"ReadMcpResourceDirTool"}` (`chunks/c0073.js @2436`).
- **Present only in permission-rule groups**: `MultiEdit`, `NotebookRead`, `LS` (`chunks/c3520.js @17273`: `[…,Jr,"MultiEdit","LS"]`, `[…,"NotebookRead","LS",…]`) — their tool-definition objects were **not found**.
- **Deprecated list**: `var Jhe=new Set(["Frame","FrameRead","TeamCreate","TeamDelete","SuggestBackgroundPR","AutofixPr","TaskOutput","AgentOutputTool","BashOutputTool","AgentOutput","BashOutput"])` (`chunks/c0682.js @1001038`).
- `Schedule`, `Worktree`, `SlashCommand`, `MCP` (as tool names): their tool-definition objects were **not found**; the capability is split into ScheduleWakeup/Cron*, EnterWorktree/ExitWorktree, with Skill taking over slash-command invocation (inferred).

---

## 2. Verbatim quotes (the 8 most instructive descriptions)

### 2.1 Bash — using "prefer the dedicated tool" to hold down abuse of the catch-all tool

The full version is assembled by `Yht()` (`chunks/c0682.js @970920`):

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

(`${co}`=Glob, `${Jr}`=Grep, `${dt}`=Read, `${Ot}`=Edit, `${Sn}`=Write, `${Ue}`=Bash; `${w}` expands on macOS/Linux to `` `find`, `grep`, `cat`, `head`, `tail`, `sed`, `awk`, or `echo` ``. Offsets: `@968288`, `@974420`, `@974994`.)

**What it is doing**: it first acknowledges the capability overlap ("While the Bash tool can do similar things"), then grounds the reason in **user experience and permission review** ("easier to review tool calls and give permission"), rather than "you are not allowed to use it". Every `# Instructions` line is a pit someone actually stepped in. Counter-examples negate in place with parentheses, `(NOT find or ls)`, which saves tokens compared with a separate sentence and is harder to skip.

The lean version (`YYn()`, `chunks/c0682.js @968032`) keeps only 4 bullets and **trades off differently** — it drops the tool navigation and keeps two facts that change behavior:

```text
Executes a bash command and returns its output.
- Working directory persists between calls, but prefer absolute paths — `cd` in a compound command can trigger a permission prompt. Shell state (env vars, functions) does not persist; the shell is initialized from the user's profile.
- Command output is displayed to you, not reliably to the user.
- `timeout` is in milliseconds: default ${qz()}, max ${iO()} for a foreground command.
```

The same tool is de-privileged in the coordinator role, **writing the reason and the exit together** (`chunks/c0583.js`, template string begins with `${Ue} in the coordinator`):

```text
${Ue} in the coordinator runs only a command it can verify as read-only and that stays in the working directory (no cd, pushd or popd), with no input besides command, description and timeout (no run_in_background, no sandbox bypass, no other machine) — run anything else from a worker via the ${yt} tool.
```

### 2.2 Edit — failure up front + errors as teaching

`Nfr()` (`chunks/c0682.js @3824547`, body `@3825704`):

```text
Performs exact string replacements in files.

Usage:
- You must use your `${dt}` tool at least once in the conversation before editing. This tool will error if you attempt an edit without reading the file.
- When editing text from Read tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: ${s}. Everything after that is the actual file content to match. Never include any part of the line number prefix in the old_string or new_string.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.${g}
- Use `replace_all` for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance.
```

Lean version (`@3824662`):

```text
Performs exact string replacement in a file.

- You must ${dt} the file in this conversation before editing, or the call will fail.
- `old_string` must match the file exactly, including indentation, and be unique — the edit fails otherwise. Strip the Read line prefix (${r?"line number + a single tab or `:`":"line number + tab"}) before matching.
- `replace_all: true` replaces every occurrence instead.
```

Runtime error text (around `chunks/c0682.js @3832818`) — **each one is a next action for the model**:

```text
Found ${Ne} matches of the string to replace, but replace_all is false. To replace all occurrences, set replace_all to true. To replace only one occurrence, please provide more context to uniquely identify the instance.
String: ${b}
```

```text
String to replace not found in file.
String: ${b}
(note: Edit also tried swapping \uXXXX escapes and their characters; neither form matched, so the mismatch is likely elsewhere in old_string. Re-read the file and copy the exact surrounding text.)
```

Others: `File does not exist. … Did you mean ${Qe}?` / `Cannot create new file - file already exists.` / `File is a Jupyter Notebook. Use the ${jl} to edit this file.` / `No changes to make: old_string and new_string are exactly the same.` / `File is too large to edit (${pn(qe)}). Maximum editable file size is ${pn(Atn)}.`

**Takeaways**: ① failure up front (`or the call will fail`) moves the cost of an error ahead of the decision point; ② counter-examples always carry the fix ("add minimal context or use `replace_all`"); ③ the `\uXXXX` note hands over the **debugging reasoning**, instead of just reporting a mismatch.

### 2.3 Read — optimistic assumptions to reduce model hesitation

`iWo()` (`chunks/c0330.js @99539`):

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

The lean version (same function from `@99539`) compresses to 5 bullets, and the last one merges the two "what happens when it can't read" paragraphs above into a statement of fact:

```text
Reads a file from the local filesystem.

- `file_path` must be an absolute path.
- Reads up to ${d2t} lines by default.
- When you already know which part of the file you need, only read that part. This can be important for larger files.
- Reads images (PNG, JPG, …) and presents them visually. Reads PDFs via the `pages` parameter (e.g. "1-5", max 20 pages/request; required for PDFs over 10 pages). Reads Jupyter notebooks (.ipynb) as cells with outputs.
- Reading a directory, a missing file, or an empty file returns an error or system reminder rather than content.
```

### 2.4 Grep / Glob — turning "which tool to use" into hard rules

Grep full version (`E6r()`, `chunks/c0330.js @103165`):

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

Grep lean version (same function, `@103165`):

```text
Content search built on ripgrep. Prefer this over `grep`/`rg` via ${Ue} — results integrate with the permission UI and file links.

- Full regex syntax (e.g. "log.*Error", "function\s+\w+"). Ripgrep, not grep — escape literal braces (`interface\{\}`).
- Filter with `glob` (e.g. "**/*.tsx") or `type` (e.g. "js", "py", "rust").
- `output_mode`: "content" (matching lines), "files_with_matches" (paths only, default), or "count".
- `multiline: true` for patterns that span lines.
```

Glob (`w6r()`, `chunks/c0330.js @102758`):

```text
- Fast file pattern matching tool that works with any codebase size
- Supports glob patterns like "**/*.js" or "src/**/*.ts"
- Returns matching file paths sorted by modification time
- Use this tool when you need to find files by name patterns
- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the ${yt} tool instead (if available)
```

**Takeaways**: hard constraints (`ALWAYS`/`NEVER`) are **immediately followed by the reason**; real bug-level details (Go's `interface{}` needing escapes, a multi-round Glob search escalating to Agent) are written in too, saving a whole round of trial and error.

### 2.5 Agent — writing "don't fool yourself" as a sectioned spec

`s0o()` (`chunks/c0682.js @3316227`):

```text
## When to fork

Fork yourself (pass `subagent_type: "fork"`) when the intermediate tool output isn't worth keeping in your context. The criterion is qualitative — "will I need this output again" — not task size. Fork open-ended questions. If research can be broken into independent questions, launch parallel forks in one message. A fork beats a fresh subagent for this — it inherits context and shares your cache.

Forks are cheap because they share your prompt cache.

**Don't peek.** The tool result includes an `output_file` path — do not Read or tail it. You get a completion notification; trust it. Reading the transcript mid-flight pulls the fork's tool noise into your context, which defeats the point of forking.

**Don't race.** After launching, you know nothing about what the fork found. Never fabricate or predict fork results in any format — not as prose, summary, or structured output. The notification arrives as a user-role message in a later turn; it is never something you write yourself. If the user asks a follow-up before the notification lands, tell them the fork is still running — give status, not a guess.

**Writing a fork prompt.** Since the fork inherits your context, the prompt is a *directive* — what to do, not what the situation is. Be specific about scope: what's in, what's out, what another agent is handling. Don't re-explain background.
```

(`**Don't peek.**` `@3317187`, `**Don't race.**` `@3317446`; "Never delegate understanding" `@3318956`; cost-sensitive copy `@3325107`; "Trust but verify" `@3329732`.)

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

**Takeaways**: the criterion is pinned down hard yet still allows autonomy ("qualitative … not task size"); anti-hallucination is written as a **format-level prohibition** ("not as prose, summary, or structured output") and paired with the correct action; the subheading itself is the prohibition, so it is extremely cheap to scan; `<example>` carries `<commentary>` explaining "what should not happen after this step".

### 2.6 TodoWrite — the positive example / counter-example / reasoning three-part form

Lean version `Bn` (`chunks/c1006.js @54416`):

```text
Create and update a task list for the current session. The list is rendered to the user as your working plan.

- Each todo has `content`, `status` ("pending" | "in_progress" | "completed"), and `activeForm` (present-tense label shown while in progress).
- Send the full list each call; it replaces the previous one.
- Keep one item `in_progress` at a time and mark it `completed` when done.
```

Full version `jn` (`@54877`, excerpt):

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

In the counter-example section (from `@55978`), each `<example>` is followed by `<reasoning>`:

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

Hard state constraints (`@62913`, `@63148`, `@63380`):

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

**Takeaways**: both the positive and negative sides are laid out symmetrically, each with its own reasoning; the state machine is hard-coded and parentheses close off any room for interpretation; "completed" is defined as 4 executable veto conditions.

### 2.7 TaskCreate / TaskUpdate — duplicating copy is fine, but spell out the differences

TaskCreate (`dr()`, `chunks/c1006.js @129094`):

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

TaskUpdate (`kr`, `@135291`, excerpt):

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

**Takeaways**: the `## Staleness` section exists specifically for multi-agent concurrency — read with `TaskGet` before changing anything; examples use **minimal executable JSON**, with no explanation.

### 2.8 EnterPlanMode / ExitPlanMode / WebFetch / AskUserQuestion

EnterPlanMode (`_e()`, `chunks/c0978.js @2540`):

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

(Start of the quoted section `@2925` / `### BAD` `@5602` / `REQUIRES user approval` `@5897`.)

ExitPlanMode (`Ks`, `chunks/c0953.js @78306`, excerpt) — the point is disambiguation:

```text
## When to Use This Tool
IMPORTANT: Only use this tool when the task requires planning the implementation steps of a task that requires writing code. For research tasks where you're gathering information, searching files, reading files or in general trying to understand the codebase - do NOT use this tool.
…
**Important:** Do NOT use ${Gs} to ask "Is this plan okay?" or "Should I proceed?" - that's exactly what THIS tool does. ExitPlanMode inherently requests user approval of your plan.
```

(Within the `@78306` block: `IMPORTANT: Only use…` `@78868`, `ExitPlanMode inherently…` `@79514`.)

WebFetch (`lWo()`/`El()`, `chunks/c0330.js @106037`/`@106873`):

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

AskUserQuestion (`BUr`, `chunks/c0522.js @1942`):

```text
Use this tool only when you are blocked on a decision that is genuinely the user's to make: one you cannot resolve from the request, the code, or sensible defaults.

Usage notes:
- Users will always be able to select "Other" to provide custom text input
- Use multiSelect: true to allow multiple answers to be selected for a question
- If you recommend a specific option, make that the first option in the list and add "(Recommended)" at the end of the label

Plan mode note: To switch into plan mode, use ${lx} (not this tool). Once in plan mode, use this tool to clarify requirements or choose between approaches BEFORE finalizing your plan. Do NOT use this tool to ask "Is my plan ready?", "Should I proceed?", or otherwise reference "the plan" in questions — the user cannot see the plan until you call ${lb} for approval.
```

`z1o` in the same file (`chunks/c0522.js @3746`):

```text
Reserve this for decisions where the user's answer changes what you do next — not for choices with a conventional default or facts you can verify in the codebase yourself. In those cases pick the obvious option, mention it in your response, and proceed.
```

Skill (`fXt`, `chunks/c0682.js @3271463`, final paragraph):

```text
Only names from the listing (or that the user typed explicitly) are valid. Built-in CLI commands (`/help`, `/clear`, …) aren't skills. If a `<${dp}>` block is already present this turn, the skill is loaded — follow it directly rather than calling again.
```

**Takeaways**: ① `## BAD` uses the **user's own words** as entries, which are easier to match than abstract descriptions; ② a single default direction, `If unsure… err on the side of planning`, replaces an exhaustive enumeration of conditions; ③ the division of labor between two easily confused tools (ExitPlanMode vs AskUserQuestion) is stated outright; ④ the definite wording of `WILL FAIL` (rather than "may fail") reduces probing; ⑤ every restriction comes with an exit (authenticated sites→MCP, localhost→Bash curl, GitHub→`gh`); ⑥ **state preconditions** prevent duplicate calls (if the skill is already loaded, don't call again).

---

## 3. Checklist of writing techniques in tool descriptions

**Measurement basis**: Corpus A = all strings and template literals (≥12 characters) concatenated from the bodies of 24 description functions/literals, **52,451 characters** in total; Corpus B = `grep -roF <pattern> raw/chunks/ | wc -l` (all 4060 chunks).

| Pattern | Corpus A | Corpus B | | Pattern | Corpus A |
|---|---|---|---|---|---|
| `IMPORTANT:` | 8 | 51 | | `"- "` line-leading bullet | 198 |
| `\bIMPORTANT\b` | 10 | — | | `"## "` heading | 13 |
| `NEVER` | 3 | 48 | | `When to/NOT to Use` | 8 |
| `ALWAYS` | 3 | 31 | | `e.g.` | 20 |
| `Do NOT` | 2 | 73 | | `Default` (any form) | 17 |
| `do not`/`Do not` | 11 | — | | `Only use` | 5 |
| `must` (case-insensitive) | 19 | — | | `Prefer` | 5 |
| `MUST` | 4 | — | | `permission` | 11 |
| `instead of` | 3 | 387 | | `read-only`/`read only` | 3 |
| `FAIL`/`will fail`/`fails`/`will error` | 11 | — | | `absolute path` | 6 |
| `NOTE` | 2 | — | | `Use this tool` | 9 (B:23) |

> `instead of` in Corpus B includes a great deal of non-tool copy (UI/error messages) and serves only as an order-of-magnitude reference.

**8 representative original sentences**

1. Hard prohibition + immediate reason: `ALWAYS use ${Jr} for search tasks. NEVER invoke `grep` or `rg` as a ${Ue} command. The ${Jr} tool has been optimized for correct permissions and access.` (`chunks/c0330.js @103789`)
2. Definite failure warning: `IMPORTANT: WebFetch WILL FAIL for authenticated or private URLs.` (`chunks/c0330.js @106594`)
3. Precondition preventing duplicate calls: `If a <${dp}> block is already present this turn, the skill is loaded — follow it directly rather than calling again.` (end of the `chunks/c0682.js @3271463` block)
4. Anti-hallucination + correct action: `Never fabricate or predict fork results in any format — not as prose, summary, or structured output. … give status, not a guess.` (`chunks/c0682.js @3317446`)
5. Subheadings as prohibitions: `**Don't peek.**` / `**Don't race.**` / `**Never delegate understanding.**` (`@3317187`, `@3317446`, `@3318956`)
6. Making the definition of done executable: `Never mark a task as completed if: - Tests are failing - Implementation is partial - You encountered unresolved errors - You couldn't find necessary files or dependencies` (`chunks/c1006.js @63380`)
7. Authorization written into the description: `This tool REQUIRES user approval - they must consent to entering plan mode` (`chunks/c0978.js @5897`)
8. Anchoring the criterion: `The criterion is qualitative — "will I need this output again" — not task size.` (within the `chunks/c0682.js @3316227` block)

**Technique table (directly copyable)**

| Technique | Form | Why it works |
|---|---|---|
| Hard-constraint trio | `ALWAYS` / `NEVER` / `IMPORTANT:` | All-caps still acts as a visual anchor in dense text; once paired with a reason it is hard to discard as noise |
| Veto-style subheadings | `## When NOT to Use This Tool`, `**Don't peek.**` | You see the forbidden zone first; a higher hit rate than burying it in a subordinate clause of a positive rule |
| Three-part example | `<example>` → dialogue → `<reasoning>` | The reasoning makes "why not this time" explicit and yields a transferable criterion |
| Failure up front | `or the call will fail` / `WILL FAIL` | Moves the cost of an error ahead of the decision point, saving one wasted call |
| Errors as instructions | `Found N matches … set replace_all to true …` | The tool result is the input to the next step, so it is written as a "next action" rather than an error code |
| Restriction paired with an exit | `not supported; for a local server, use curl via Bash` | Every prohibition comes with a viable substitute, avoiding dead ends or detours |
| State machine + parenthetical disambiguation | `Exactly ONE … (not less, not more)` | Closes off the interpretive space of "is more than one acceptable" |

---

## 4. How the input schemas are written

Uniformly `o()`=string, `C()`=number, `H()`=boolean, `B([...])`=enum, `T()`=array, `Ve({...})`=object, each paired with `.describe()`. **Almost every field has a describe**, and each one writes semantics + default value + cross-field dependency + example at the same time.

**Bash** (`Whr`, `chunks/c0682.js @3982194`, `grn` at `@3983788`):

```text
command: o().refine(eO, jhr).describe("The command to execute")
timeout: CH(C().optional()).describe(`Optional timeout in milliseconds (max ${iO()} for a foreground command)`)
run_in_background: fT(H().optional()).describe(qdn())
dangerouslyDisableSandbox: fT(H().optional()).describe("Set this to true to dangerously override sandbox mode and run commands without sandboxing.")
_simulatedSedEdit: u({filePath:o(),newContent:o(),baseHash:o().optional()}).optional().describe("Internal: pre-computed sed edit result from preview")
```

- The validation failure message states the security reason outright: `jhr` = `"command contains control characters that would be hidden in the approval dialog"` (`chunks/c0682.js @3982108`).
- The describe on the `description` field is itself a tutorial: `Clear, concise description of what this command does in active voice. Never use words like "complex" or "risk" in the description - just describe what it does.` + the positive example `ls → "List files in current directory"` and a positive example for a hard-to-parse command, `git reset --hard origin/main → "Discard all local changes and match remote main"`.
- **The schema morphs with the environment**: `grn=f(()=>(Za()? mrn().omit({run_in_background:!0,_simulatedSedEdit:!0}) : mrn().omit({_simulatedSedEdit:!0})).superRefine(…)` — in remote-execution scenarios it simply `.omit()`s the fields that aren't allowed.

**Edit** (`QJ`, `chunks/c0682.js @710496`):

```text
Ve({
  file_path: o().describe("The absolute path to the file to modify"),
  old_string: o().describe("The text to replace"),
  new_string: o().describe("The text to replace it with (must be different from old_string)"),
  replace_all: fT(H()).default(!1).optional().describe("Replace all occurrences of old_string (default false)"),
  ...sj()
})
```

The constraint is consistent in three places: `.default(!1)` + `.optional()` + the `(default false)` in describe; `(must be different from old_string)` also has a matching rejection message at runtime.

**Read** (`EKn`, `chunks/c0682.js @892123`):

```text
Ve({
  file_path: o().describe("The absolute path to the file to read"),
  offset: CH(C().int().nonnegative().optional()).describe("The line number to start reading from. Only provide if the file is too large to read at once"),
  limit: CH(C().int().positive().optional()).describe("The number of lines to read. Only provide if the file is too large to read at once."),
  pages: o().optional().describe(`Page range for PDF files (e.g., "1-5", "3", "10-20"). Only applicable to PDF files. Maximum ${Y0e} pages per request.`),
  ...sj()
})
```

Type constraints go into the schema (`.int().nonnegative()`), while **"when should I fill this in" goes into describe** (`Only provide if the file is too large to read at once`) — this suppresses thoughtless argument passing. The same pattern appears in Glob: `path: o().optional().describe('… IMPORTANT: Omit this field to use the default directory. DO NOT enter "undefined" or "null" - simply omit it for the default behavior. …')` (`chunks/c0682.js @923329`).

**Grep** (`CVn`, `chunks/c0682.js @927515`, excerpt):

```text
  pattern: o().describe("The regular expression pattern to search for in file contents"),
  glob: o().optional().describe('Glob pattern to filter files (e.g. "*.js", "*.{ts,tsx}") - maps to rg --glob'),
  output_mode: B(["content","files_with_matches","count"]).optional().describe('Output mode: … Defaults to "files_with_matches".'),
  "-B": CH(C().optional()).describe('Number of lines to show before each match (rg -B). Requires output_mode: "content", ignored otherwise.'),
  head_limit: CH(C().optional()).describe('Limit output to first N lines/entries, equivalent to "| head -N". … Defaults to 250 when unspecified. Pass 0 for unlimited (use sparingly — large result sets waste context).'),
  offset: CH(C().optional()).describe('Skip first N entries before applying head_limit, equivalent to "| tail -n +N | head -N". … Defaults to 0.'),
  multiline: fT(H().optional()).describe("Enable multiline mode where . matches newlines and patterns can span lines (rg -U --multiline-dotall). Default: false."),
```

Every field notes its rg counterpart (`(rg -B)`); `Requires output_mode: "content", ignored otherwise.` is **deliberately repeated** across 5 fields to prevent invalid combinations; `Pass 0 for unlimited (use sparingly — …)` uses the reason in parentheses to suppress "passing 0 is safer".

**Agent** (`Io`/`amr`, `chunks/c0966.js @10295`, `@11663`):

```text
name: o().regex(L4o,{message:"name must start with a letter or digit and contain only letters, digits, underscores, or hyphens (max 64 chars)"})
     .refine((e)=>e!==eg,{message:`"${eg}" is reserved — SendMessage routes it to the main conversation`})
     .refine((e)=>!nO(e),{message:'name must not be a reserved name ("main", "team-lead", "user" or "system", in any spelling) or have the shape of an agent id — those already address an agent directly'})
     .optional().describe("Name for the spawned agent. Makes it addressable via SendMessage({to: name}) while running.")
isolation: B(["worktree","remote"]).optional().describe('Isolation mode. "worktree" creates a temporary git worktree so the agent works on an isolated copy of the repo. "remote" launches the agent in a remote cloud environment (always runs in background; availability is gated).')
cwd: o().optional().describe('Absolute path to run the agent in. … Mutually exclusive with isolation: "worktree".')
run_in_background: H().optional().describe("Agents run in the background by default; you will be notified when one completes. Set to false only when your very next action depends on this agent's result and nothing else could usefully happen while it runs — otherwise leave it in the background so the user can hand you other work.")
```

Validation messages are written for the model rather than the developer (the alternate path is stated outright: `SendMessage routes it to the main conversation`); mutual exclusions are written into describe; in `amr` the schema is **trimmed by feature flag**: `CLAUDE_CODE_SUBAGENT_MODEL_FORCE? h.omit({model:!0}) : h`, `h=e? n.omit({run_in_background:!0}) : …`.

**TaskCreate / TaskUpdate** (`Ns` `@131558`, `js` `@137593`):

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

One example, `(e.g., "Running tests")`, pins down "present continuous"; deletion semantics live in the field description (`Set a key to null to delete it.`); `status` is assembled with `vRe().or(x("deleted"))`, matching the line `Use deleted to permanently remove a task.` in the description.

**Common patterns**: ① every field has a describe; ② required simply means not adding `.optional()`; ③ enums are always `.optional()` with the default branch named in describe; ④ mutual exclusions/dependencies are stated outright, never left to inference; ⑤ the schema is alive (`.omit/.extend/.refine/superRefine` trimmed by flag, platform, remote capability); ⑥ validation failure messages are written for the model to read.

---

## 5. Unverified / unreadable parts

1. **The `Wt` wrapper itself was not located**: `Wt` is imported from `/$bunfs/root/chunk-1b21she7.js` (see the head of `chunks/c2674.js`), and the carved-out chunks cannot be mapped directly to bun's internal chunk names, so the **default value when `isReadOnly`/`isConcurrencySafe` are not declared cannot be confirmed**; every such case in the table is marked `-`.
2. **`Schedule`/`Worktree`/`SlashCommand`/`MCP` as tool names**: no corresponding tool-definition object was found anywhere in the corpus, so they are not listed in the table.
3. **`MultiEdit`/`NotebookRead`**: they appear only in permission-rule groups and compatibility lists (`chunks/c3520.js @17273`), and **cannot be confirmed** as tools registered in this build (leaning toward retained historical names; this is inferred).
4. **The Artifact family**: the names `mn="Artifact"`, `Ly="ArtifactComments"`, `Om="ArtifactData"`, `Hx="ArtifactCheck"` are pinned down in `chunks/c0186.js @12467`, but only Artifact's tool object has a fairly clear location; the other three objects were not located one by one (they appear in the telemetry mapping at `chunks/c0682.js @996223`).
5. **Tool-count basis**: `Wt({` occurs 93 times, 82 of which balance out into objects, and about 70 of those yield a tool name. The "actual registered count" is also affected by `isEnabled()`, `shouldDefer`, enterprise/`ant` branches, and platform (`O()==="windows"`); **this table is not the final tool list handed down to the model at runtime**.
6. The 9 `self_hosted_runner_*` in `chunks/c2956.js` appear only in that chunk; their UI/permission wiring is **not verified**.
7. Corpus A's statistics depend on manually locating the "description body"; where a tool description is assembled from several places (e.g. Bash's `Yht` built via `Sm()`), the count covers only the template/string literals themselves and **excludes runtime-inserted content**.

---

## 6. What this suggests for us

1. **Copy the "tool object + two description versions" structure**: fix `name / searchHint / description / prompt / inputSchema / isReadOnly / isConcurrencySafe / backgrounding`, and split descriptions into lean and full (`chunks/c0682.js @968032` vs `@970920`). One source of truth sliced at two granularities, rather than two sets of copy to maintain.
2. **Copy `IMPORTANT: Avoid using this tool to run X … Instead, use the appropriate dedicated tool`**: the catch-all tool is the biggest consumer of dedicated-tool usage; listing the replacement relationships **one by one** (`Read files: Use Read (NOT cat/head/tail)`) is far more effective than a vague sentence in the system prompt (`chunks/c0682.js @968288`).
3. **Copy "failure up front" + "errors as the next step"**: Edit writes its 9 failure classes as natural language containing a recovery action (around `chunks/c0682.js @3832818`). When writing tools, write error messages as prompts.
4. **Copy the symmetric `When NOT to Use This Tool` structure + `<example>/<reasoning>`**: reasoning is the key to making the criterion explicit, at almost no cost (from `chunks/c1006.js @55978`).
5. **Copy "the subheading is the prohibition"**: `**Don't peek.**`, `**Don't race.**`, `**Never delegate understanding.**` (`chunks/c0682.js @3317187`, `@3317446`, `@3318956`), for anti-hallucination clauses in every async/concurrent scenario.
6. **Copy "every restriction must have an exit"**: each WebFetch restriction is followed by a substitute (authenticated sites→MCP, localhost→Bash curl, GitHub→`gh`) (`chunks/c0330.js @106594`, `@106873`). Prohibiting without providing an exit leaves the agent spinning.
7. **Copy "a default direction instead of an exhaustive condition list"**: `If unsure whether to use it, err on the side of planning` (around `chunks/c0978.js @5897`); `If you recommend a specific option, make that the first option in the list and add "(Recommended)"` (`chunks/c0522.js @1942`).
8. **Copy "the schema is alive"**: the same tool's schema is morphed by platform/remote/flag with `.omit()/.extend()/.refine()` (`chunks/c0682.js @3983788`, `chunks/c0966.js @11663`), instead of writing "this field is invalid in some cases" in the description.
