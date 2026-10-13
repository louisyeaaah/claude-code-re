> English version. 中文原版：[REPORT-dynamic.md](REPORT-dynamic.md)

# Step 2 · Dynamic verification: capture one real request and compare it against the static reconstruction

> Purpose: static analysis yields "assembly code + the original text of each block"; this step verifies it against the **request body that was actually sent**, and surfaces where the static inference was wrong.
> Artifacts: `verify/captured/` (raw request bodies), `verify/comparison.json`, and this report.

## 1. Method (no real credentials touched, no external request produced)

```bash
# 1) Local interception server: writes only the request body to disk, then returns 400 without forwarding
python3 verify/capture_server.py 18787 captured

# 2) Run the CLI once with a separate config directory + dummy key + a base URL pointing at localhost
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
  CLAUDE_CONFIG_DIR=.../verify/cfg \
  ANTHROPIC_BASE_URL=http://127.0.0.1:18787 \
  ANTHROPIC_API_KEY=sk-ant-dummy-key ANTHROPIC_AUTH_TOKEN=dummy-token \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_TELEMETRY=1 DISABLE_ERROR_REPORTING=1 \
  ~/.local/share/claude/versions/2.1.287 -p "reply ok"
```

Safety boundary: `CLAUDE_CONFIG_DIR` points at an empty directory inside the workspace (so the credentials and config under `~/.claude` are unreachable); the key is a dummy string; `ANTHROPIC_BASE_URL` points at 127.0.0.1, so **the request never left this machine** (the server returns 400 as soon as it receives it). The error the CLI reports is exactly `API Error: 400 captured locally; not forwarded`.

## 2. What was captured

| Variant | Trigger | system blocks | system characters | Tools |
|---|---|---|---|---|
| **lean** (default) | plain `-p` | 3 | 5,789 | 20 |
| **full** | plus `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT=0` | 3 | 26,950 | 20 |

Both carry the model field `claude-opus-5-5` (the local CLI's default model), with request bodies of roughly 66–76 KB containing fields such as `context_management`, `thinking`, `safeguards`, and `output_config`.

**The three system blocks of both requests** (order and cache_control exactly identical):

```
block0        74 B  cache_control=None          'x-anthropic-billing-header: cc_version=2.1.287.1f9; cc_entrypoint=sdk-cli;'
block1        62 B  cache_control={ephemeral}   "You are a Claude agent, built on Anthropic's Claude Agent SDK."
block2  5,681/27,078 B  cache_control={ephemeral}  '\nYou are an interactive agent that helps users ...'
```

That is: **the most volatile piece, the billing header, is its own first block and is not cached**; the identity has a block of its own; everything else is merged into the third block — consistent with the static analysis (05 §2).

## 3. The lean / full switch sits right there in the code, and was verified on the real CLI

Assembly site (`raw/chunks2/0374__chunk-mphp7acd.js` @1447722):

```js
be = g ? [["lean_body", Wao(j,n)]]
       : [["intro",Iao(j)],["system",Lao(n)],["doing_tasks",…Nao()],["actions",Fao()],["tools",Bao(z)],["tone",jao()]];
```

`g = AG(model)`, and the check in `Ao()` involves `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT`: a truthy value → lean, `"0"/"false"/"no"/"off"` → forces **full**. The live result matches what the code predicts (5,789 → 26,950 characters).

## 4. Item-by-item comparison

### 4.1 Hits (the live run confirmed the static conclusions)

| Static conclusion | Dynamic evidence |
|---|---|
| Existence and headings of the 6 static blocks | The full run shows `# System`, `# Doing tasks`, `# Executing actions with care`, `# Using your tools`, `# Tone and style`; headings and order match the assembly code |
| Three identity variants | block1 is in fact the SDK variant `You are a Claude agent, built on Anthropic's Claude Agent SDK.` (the non-interactive `-p` path); the CLI variant `Qw` does not appear — consistent with the code branch |
| Safety baseline (vMe) present verbatim | ✓ verbatim hit |
| Billing header is its own first, uncached block | ✓ block0 has no `cache_control` |
| Tool descriptions come in **two copies** (lean/full) | ✓ the same set of 20 tools, with description length varying by mode: Bash 1,097 → 9,438, Agent 1,668 → 6,926, Read 790 → 1,782, WebFetch 469 → 1,608, WebSearch 334 → 1,344 (the rest unchanged) |
| `# Harness` belongs to the lean body | ✓ appears only in the lean version; the full version has no `# Harness`, and the corresponding content is folded into `# System` |
| `# Context management` / `# Environment` / `# auto memory` are dynamic blocks | ✓ present in both versions (`# auto memory` with its 6 subsections) |
| `# Text output` is a conditional block | ✓ appears in the full version only |
| The tool list is trimmed by switches | ✓ only 20 tools; entries that exist in the static corpus — `TodoWrite/TaskCreate/TaskUpdate/TaskList` (`CLAUDE_CODE_ENABLE_TODO_TOOLS` off), `Glob/Grep`, `EnterPlanMode/ExitPlanMode`, `AskUserQuestion`, etc. — were not sent |

### 4.2 Corrections (where the static inference was wrong)

**The third variant of the system-reminder wording is not triggered by "coordinator/background mode".**

In the real request, the corresponding sentence under `# System` reads:

```
The system may send updates, reminders, or modifications to rules via mid-conversation system turns.
These are system-controlled, unlike function results.
```

The static code is `function Dao(e){return p8(e)&&!xQn(e)&&!ujo(Be(e))}`, where `p8(e)` reads the model's `midConversationSystem` capability bit and `ujo(e)` excludes `claude-opus-4-8`. In other words, this tier is decided by **whether the model supports mid-conversation system messages**, and has nothing to do with coordinator/background. The attribution in §3.1 of `01-system-prompt.en.md` has been corrected accordingly.

### 4.3 Absent but explained

- `# Writing for the user` (the "No em-dashes, no parentheticals, no arrows" set) appears in neither mode — it is injected conditionally on the client/carrier, and the `-p` scenario does not satisfy that condition.
- `# Focus mode`, `# Background Session`, `# Machines`, `# Language`, and the autonomous-run addendum blocks do not appear, matching the "injected according to run shape" design.
- The personalized `# Session-specific guidance` and `# Memory` content varies with the config directory (an empty config here).

## 5. Quantifying coverage

Every English source line inside fenced quote blocks in `extracted/01-system-prompt.en.md` (129 lines) was compared verbatim against this full request: **70 lines matched verbatim (54%)**. The 59 misses fall into three groups: ① the whole `# Writing for the user` block (not injected in this scenario); ② the `# Harness` items that appear only in the lean body; ③ lines elided with `...` or containing `${}` interpolations. The hit rate depends on the scenario, so it cannot be used to measure reconstruction correctness; **the right criterion is "everything that should appear did appear, and everything absent has a reason to be absent"**.

## 6. What could not be verified

- **Interactive TUI mode**: the sandbox forbids `openpty` (`script: openpty: Operation not permitted`), so a genuinely interactive session cannot be run; the CLI identity variant (`Qw`) and the full block combination on the interactive path were therefore **not exercised live**.
- **The `scope:"global"` cache tier**: the local base URL points at localhost, which is not first-party (`gr` is false), so only `{type:"ephemeral"}` showed up in the live run — consistent with the code's prediction — but the global tier itself was never triggered.
- Model/account-dependent branches (such as the `claude-opus-4-8` exclusion) cannot be exercised on this machine.

## 7. Reproducing

```bash
cd verify
python3 capture_server.py 18787 captured &          # local interception
# In another terminal, run the command from §1 twice: once with the defaults (lean), once with CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT=0 (full)
ls captured/full/86400                                # raw request body
python3 compare_prompt.py                             # generates comparison.json
```

The raw request bodies (`captured/*.body.json`) are sanitized: they contain only the dummy key and a local address, and no real credentials.
