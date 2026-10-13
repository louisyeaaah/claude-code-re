> English version. 中文原版：[07-prompt-writing-patterns.md](07-prompt-writing-patterns.md)

# How Claude Code v2.1.287 Writes Prompts: Quantifiable First-Hand Observations


> Method: `raw/census.py` extracts every string/template literal from 4060 embedded JS chunks (476,109 of them),
> then filters for "prompt-like" literals (≥80 characters, containing spaces and newlines, containing referential
> words such as you/your/user/tool/the, deduplicated, license headers stripped) — 772 of them (2.67 MB) — and tabulates them.
> Reproduce: `cd raw && python3 census.py` (the deduplicated version of the script is in the appendix at the end of this file).

## 1. Size distribution

| Metric | Value |
|---|---|
| Prompt-like literals (after dedup) | **772**, totalling 2.67 MB |
| Median length | **552 characters** |
| p75 / p90 / p99 | 1,722 / 6,401 / 48,681 characters |
| All string literals | 476,109 (including short strings in code) |

Conclusion: this is not "one big prompt" but **several hundred few-hundred-character blocks**. A median of 552 characters means a large share of prompts are shorter than a single screen — they work through **assembly**, not through length.

## 2. Distribution of instruction markers (count = occurrences / literals containing the word)

| Marker | Occurrences | Documents | Reading |
|---|---|---|---|
| `e.g.` | 164 | 82 | Most frequent — **almost every rule comes with an example** |
| `instead of` | 111 | 37 | Corrects behaviour with an "alternative" rather than a "prohibition" |
| `Do not` | 94 | 65 | The main negative form |
| `unless` | 92 | 68 | Nearly every prohibition carries an **exception condition** |
| `required` | 89 | 44 | Parameter/condition constraints |
| `If you` | 85 | 62 | Condition—action phrasing |
| `Never` / `NEVER` | 63 / 35 | 44 / 18 | Uppercase NEVER is reserved for a very few red lines |
| `only when` | 56 | 40 | Tightens the scope of applicability |
| `Don't` | 49 | 30 | Colloquial negation |
| `do NOT` | 35 | 25 | Local emphasis (mixed case) |
| `MUST` | 34 | 29 | Obligation type, less common than the negative type |
| `Always` / `ALWAYS` | 24 / 12 | 18 / 12 | Less common than the negative type |
| `for example` | 32 | 18 | Another way to write an example |
| `IMPORTANT:` | 21 | 17 | Paragraph-level emphasis |
| `Prefer` | 19 | 18 | Expresses a preference rather than a prohibition |
| `Avoid` | 15 | 15 | Same as above |
| `CRITICAL` | 14 | 13 | Rare in system prompts, more common in skills/commands |

**How to read this**: `e.g.` (164) + `instead of` (111) + `unless` (92) are all more frequent than `NEVER` (35). The style of these prompts leans toward **"give the condition, give the alternative, give the example"** rather than suppressing behaviour with uppercase prohibitions. Uppercase `NEVER` is reserved for the genuine red lines (the "hand the whole advice document to you" level).

## 3. Seven rule sentence patterns (with verbatim samples)

### ① Prohibition + exception (unless)
```
Do not proceed unless you expected them.
No model turn unless the plugin asks for one.
```
> Writing only "don't do X" leaves the model stuck in edge cases; adding a single `unless ...` clause spells out when it may proceed.

### ② Prohibition + replacement (instead of / rather than)
```
When true, the sandbox runtime deterministically denies hosts not in allowedDomains instead of prompting.
Prefer the Edit tool for modifying existing files — it only sends the diff.
Prefer to create a new commit rather than amending an existing commit.
```
> Compared with "don't do X", `instead of / rather than` names the model's next action directly, **leaving no room for it to improvise**.

### ③ Condition—action (If you …)
```
If you did not check, say you did not check.
If you find yourself repeating what a subagent is doing, you should not have spawned it.
If you told the user this was saved or remembered, tell them plainly that it was not.
```
> The pattern is highly consistent: an observable trigger condition (what you did, what you found) + an immediately executable action. Sentences like these can go into a test set one by one.

### ④ Don't write documentation red lines (NEVER, uppercase)
```
- NEVER create documentation files (*.md) ...
- NEVER invoke `grep` or `rg` as a Bash command.
- NEVER run destructive git commands (push --force, reset --hard, checkout .)
- NEVER create files unless they're absolutely necessary for achieving your goal.
- The assistant NEVER uses the <shutdown> tool or even mentions the possibility of ending the conversation.
```
> Only ~18 literals in the whole corpus use uppercase NEVER, and each maps to a real, high-frequency incident (creating stray md files, bypassing dedicated tools, destructive git, unilaterally ending the conversation).

### ⑤ Preference ordering (Prefer / Avoid)
```
Prefer choices whenever the likely answers can be listed.
Prefer modelUsage for token/cost accounting.
Prefer denying the enclosing directories.
- Prefer the dedicated file/search tools over shell commands when one fits.
```
> "Prefer A over B" instead of "prohibit B" preserves sensible exceptions, and is also easier to keep consistent with the implementation.

### ⑥ Conflict adjudication (X wins)
```
Managed, --settings and user settings choose the level (the most restrictive wins); project and local settings can only lower it, never raise it.
An explicit value always wins.
Where these rules conflict with more general communication or formatting guidance elsewhere in your instructions, these rules win.
```
> Once multiple rules coexist, conflicts are inevitable; **writing the precedence down explicitly** is far cheaper than making the model guess. This pattern has already been engineered in the permission system (`first-wins` / `merge` and the like) — prompts should follow suit.

### ⑦ Lead with the conclusion, then the method (Lead with …)
```
Report what actually happened, not what you intended.
Lead with the outcome. Your first sentence after finishing should answer "what happened" ...
Report outcomes faithfully: if tests fail, say so with the output; if a step was skipped, say that ...
```
> Output-facing rules invariably define **what the first sentence of the finished product looks like** before discussing process discipline.

## 4. Structural conventions (not sentence patterns, but equally reusable)

1. **Section titles are themselves instructions**: `# Executing actions with care`, `# Reporting outcomes`, `# Delivering work` — the title states the criterion for that section.
2. **List item length is controlled**: most items run 1–3 sentences; only when a long explanation is needed does a section run to a full 3.6 KB (`# Executing actions with care`), and even then it stays a checklist internally.
3. **Examples before adjectives**: risk is not described as "dangerous" but as `force-push / git reset --hard / changing CI`; reporting standards are not described as "be accurate" but as `if tests fail, say so with the output`.
4. **Counter-examples appear in pairs**: `text like "Let me read the file:" ... should just be "Let me read the file." with a period.` — the good and bad examples are written side by side.
5. **Multiple phrasings for the same mechanism**: the system-reminder explanation has 3 variants, the communication rules have 3 (terminal / focus / specific client), switched by carrier instead of writing one universal long text (see [`01-system-prompt.en.md`](01-system-prompt.en.md)).
6. **Dynamic content speaks only of "this turn"**: static blocks use `NEVER / always`, dynamic blocks use `this session / right now / the user has ... enabled`, making the period of validity explicit in the wording.
7. **Placeholder-isation**: many of the originals are `${toolName}` / `${language}` / `${n}` templates, so one piece of text is reused across different tools/forms (e.g. TodoWrite and TaskCreate share one sentence), reducing wording drift.

## 5. Unverified / framing notes

- The statistical object is **embedded string literals**, which include tool parameter descriptions, configuration documentation, error messages and other non-"prompt" text; the 772 are an approximate filtered set, not an exact list of "prompts sent to the model".
- Counts depend on the deduplication convention (the same text appearing in multiple chunks is deduplicated), so absolute numbers are only useful for comparing relative frequencies — they should not be read as "there are 94 Do nots in the system prompt".
- No cross-version comparison was done (five other version files, 2.1.272–2.1.286, are available on this machine), so whether the style evolved between versions is unverified.

## Appendix: the essentials of the reproduction script

`raw/census.py`: state-machine scan (handling `'`/`"`/backtick template literals with nested `${}`, and comments) → collect literals → filter (≥80 characters, contains spaces and newlines, contains referential words, license headers stripped, deduplicated by the first 120 characters) → count markers and length quantiles.
