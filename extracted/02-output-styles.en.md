> English version. 中文原版：[02-output-styles.md](02-output-styles.md)

# Reverse Engineering the Output Style Mechanism in Claude Code v2.1.287

> Sources: `chunks/c0682.js` @1,126,000~1,134,000 (built-in style table and loader), @112,8940 (the `bbt` insight template), @132,387 (the `# Output Style` / `# Language` templates)
> Companion: for system-prompt assembly see [`01-system-prompt.en.md`](01-system-prompt.en.md)

## Why this gets a document of its own

Output Style is **the structural design most worth copying** in this prompt-engineering setup: it lifts "who I am and how I speak" out of the behavioral rules wholesale and turns it into a first-class, pluggable, persistable object that plugins can distribute. The behavioral rules (# Doing tasks / # Executing actions with care) stay put; the expression layer switches with the style.

## 1. Data structure

The built-in table is an object keyed by name, with `default` mapped to `null` (= nothing appended):

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

A style = 5~7 fields, each layer solving a different problem:

| Field | Purpose | Injection timing |
|---|---|---|
| `name` / `description` | The basis for choosing, shown to the user and the model | `/output-style` UI |
| `source` | `built-in` / user directory / plugin; determines priority and whether it can be overridden | Load time |
| `prompt` | **Identity-level** (long): can replace the first identity sentence wholesale | Into the system prompt every turn |
| `turnReminder` | **Once per turn** (one sentence): compresses the style's core into a one-line reminder | Every turn |
| `waitingTurnReminder` | Specific to the waiting state (e.g. don't poll while waiting on a background task) | Particular states |
| `keepCodingInstructions` | Whether to keep the `# Doing tasks` coding discipline | Assembly time |

> Worth learning: **one intent written at three granularities** — identity (a few hundred words), a per-turn reminder (one sentence), a state special case (one sentence). The long text shapes, the short sentences sustain, the special cases correct course.

## 2. How the five built-in styles differ in behavior

### Proactive

Prompt header: `You should work proactively and autonomously, executing immediately and minimizing interruptions.` The body is the six items of `F7n`:

```
The user chose continuous, autonomous execution. You should:
1. **Execute immediately** — Start implementing right away. Make reasonable assumptions and proceed on low-risk work.
2. **Minimize interruptions** — Prefer making reasonable assumptions over asking questions for routine decisions.
3. **Prefer action over planning** — Do not enter plan mode unless the user explicitly asks. When in doubt, start coding.
4. **Expect course corrections** — The user may provide suggestions or course corrections at any point; treat those as normal input.
5. **Do not take overly destructive actions** — This is not a license to destroy. Anything that deletes data or modifies shared or production systems still needs explicit user confirmation. If you reach such a decision point, ask and wait, or course correct to a safer method instead.
6. **Avoid data exfiltration** — Post even routine messages to chat platforms or work tickets only if the user has directed you to. You must not share secrets (e.g. credentials, internal documentation) unless the user has explicitly authorized both that specific secret and its destination.
```

turnReminder: `Execute autonomously, minimize interruptions, prefer action over planning.`

waitingTurnReminder (while waiting on a background task): `Execute autonomously and minimize interruptions. If the only work left is waiting for a background task or monitor you started, end your turn now: you will be notified when it finishes or fires. Do not poll, sleep, or re-read its output while you wait.`

> Worth learning: items 5 and 6 are the standard way to **fence in freedom** — first grant autonomy explicitly, then point out **which actions fall outside the grant** (destructive actions, data exfiltration). Otherwise "more autonomous" is easily read as "can do anything".

### Concise

Six rules + one **conflict-resolution clause**:

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

> Worth learning: items 5 and 6 close off the two typical misuses of "concise" up front (failing to say what should be said, dropping error information); the last line is an **explicit precedence declaration** — style rules beat general communication rules, so the model doesn't oscillate between two instructions.

### Explanatory

Appends `## Insights` and specifies the output shape (even the separator lines are given):

```
## Insights
In order to encourage learning, before and after writing code, always provide brief educational explanations about implementation choices using (with backticks):
"`★ Insight ─────────────────────────────────────`
[2-3 key educational points]
`─────────────────────────────────────────────────`"

These insights should be included in the conversation, not in the codebase. You should generally focus on interesting insights that are specific to the codebase or the code you just wrote, rather than general programming concepts.
```

> Worth learning: **specify the medium** (written in the conversation, not in the codebase) + **specify the shape** (a fixed frame, 2~3 items) + **specify the bias** (this repository's concrete issues take priority over general concepts). This is far more effective than "explain a bit more".

### Learning

The most complex of the five: it turns "teaching" into an executable interaction protocol:

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

> Worth learning: it turns "get the user involved" into a **verifiable state machine**: first write `TODO(human)` (exactly one), then issue the request, then **stop and wait**. It also gives two complete examples (a whole function / a fragment inside a function) to anchor the granularity.

### default

`null` — nothing appended; the base identity and the general communication discipline are used.

## 3. Injection path

Style content is not stuffed into messages; it is **appended to the system prompt**:

```js
function C_n(e,n){return `# Output Style: ${e}\n${n}`}
function Z3e(e){ if(e===null) return "The output style was reset to the default. Respond in your usual style.";
                return C_n(Rk(e.name), e.prompt) }
```

- `# Output Style: <name>` is the header line, with the style prompt body below it (`Rk()` does the escaping).
- Switching to the default style is not "saying nothing" but an explicit notification: `The output style was reset to the default. Respond in your usual style.` — **clearing state also has to be announced**.
- Language preference goes through the same mechanism: `# Language` + `Always respond in ${e}. ... Never substitute accented characters with their ASCII equivalents` (clearing it likewise has its own sentence). Style and language are **two orthogonal dimensions**, set and cleared independently of each other.

## 4. Custom styles and source priority

- Styles can come from the user directory (`.claude/output-styles/*.md`) and from plugins; the file format is frontmatter + body, with frontmatter fields named the same as the built-in ones: `name` / `description` / `keep-coding-instructions` (= whether to keep `# Doing tasks`) / `force-for-plugin` (force-enabled by a plugin).
- Symbols such as `outputStyles` / `plugin_load_output_styles` appear in the loader and the plugin-loading paths (`chunks/c0682.js` @401390, @1124961, @1127037), which shows that styles are **assets a plugin can distribute**, on the same level as commands, agents, and skills.
- The point of `keepCodingInstructions`: a style only changes "persona and expression", while **engineering discipline is kept by default** — only an explicit declaration overrides it. Safe by default.

## 5. What this teaches us

1. **Split the "expression layer" out of the "principles layer"**: principles (how to work, when to ask) and expression (tone, length, format) have different lifecycles — the former iterates by version, the latter switches by user preference.
2. **Three granularities**: a long identity text + a one-sentence per-turn reminder + a one-sentence waiting/special case. The long text shapes once, the short sentences keep it alive every turn, the special cases correct course precisely.
3. **Every style needs "anti-misuse" items** (items 5 and 6 of Concise; items 5 and 6 of Proactive).
4. **Write the conflict ruling explicitly**: `Where these rules conflict with more general communication or formatting guidance elsewhere in your instructions, these rules win.` — without this sentence, the style prompt ends up in a tie with the system prompt inside the model.
5. **State transitions must leave a trace**: setting the default and clearing the language preference each get an explicit sentence, so the model doesn't carry over the previous turn's stylistic inertia.
6. **Styles must be distributable**: go through the plugin system (frontmatter + directory convention) rather than a built-in enum — the ecosystem can contribute styles.

## 6. Unverified / not readable

- Whether more styles exist beyond the five built-ins (rolled out gradually by flag) was not exhaustively checked; the keys actually present in the table are `default / Proactive / Concise / Explanatory / Learning`.
- The exact injection site of `turnReminder` (a system-prompt block or a per-turn message prefix) was not traced line by line in the assembly function — it is **inferred** to be a short per-turn reminder, with no runtime verification.
- The full frontmatter validation rules for custom styles were not extracted item by item (only the appearance of the four field names `name/description/keep-coding-instructions/force-for-plugin` was confirmed).
