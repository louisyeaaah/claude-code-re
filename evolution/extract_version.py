#!/usr/bin/env python3
"""对任意 Claude Code 单文件产物做同一套提取（v2：按模块逐个抽字面量 + 长度上限，避免解析器被反引号带跑）。

用法：python3 extract_version.py <binary> <outdir>
产物：<outdir>/meta.json、prompts.jsonl、sections.txt、probes.json
"""
import os, re, sys, json, hashlib

BIN = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
CAP = 400_000          # 单条字面量长度上限，超过即视为解析失败

data = open(BIN, "rb").read()
sha = hashlib.sha256(data).hexdigest()
bounds = [m.start() + 1 for m in re.finditer(rb"\x00// @bun @bytecode", data)]
mods, bad = [], 0
for i, b in enumerate(bounds):
    e = bounds[i + 1] - 1 if i + 1 < len(bounds) else len(data)
    text = data[b:e].decode("latin-1")
    pr = sum(1 for c in text if c == "\n" or 32 <= ord(c) < 127) / max(1, len(text))
    if pr > 0.9:
        mods.append(text)
    else:
        bad += 1
bundle = "\n".join(mods)


def literals(text, minlen=120):
    n = len(text); i = 0; out = []
    def skip(s, i, q):
        i += 1
        while i < len(s):
            if s[i] == "\\": i += 2; continue
            if s[i] == q: return i + 1
            i += 1
        return i
    def tpl(s, i):
        i += 1; d = 0; b = []; over = False
        while i < len(s):
            c = s[i]
            if c == "\\": b.append(s[i:i+2]); i += 2; continue
            if d == 0 and c == "`": return i + 1, (None if over else "".join(b))
            if d == 0 and c == "$" and i + 1 < len(s) and s[i+1] == "{":
                d = 1; b.append("${"); i += 2; continue
            if d > 0:
                if c in "\"'":
                    j = skip(s, i, c); b.append(s[i:j]); i = j; continue
                if c == "`":
                    j, sub = tpl(s, i)
                    b.append("" if sub is None else "`" + sub + "`"); i = j; continue
                if c == "{": d += 1
                elif c == "}": d -= 1
                b.append(c); i += 1; continue
            b.append(c); i += 1
            if len(b) > CAP: over = True; b = []
        return i, None
    while i < n:
        c = text[i]
        if c in "\"'":
            q = c; j = i + 1; b = []
            while j < n:
                if text[j] == "\\": b.append(text[j:j+2]); j += 2; continue
                if text[j] == q: break
                b.append(text[j]); j += 1
            s = "".join(b)
            if len(s) >= minlen and " " in s: out.append(("str", s))
            i = j + 1; continue
        if c == "`":
            j, s = tpl(text, i)
            if s and len(s) >= minlen and " " in s: out.append(("tpl", s))
            i = j; continue
        i += 1
    return out


lits = []
for m in mods:
    lits.extend(literals(m))
with open(os.path.join(OUT, "prompts.jsonl"), "w") as f:
    for kind, s in lits:
        f.write(json.dumps({"k": kind, "n": len(s), "h": hashlib.md5(s.encode()).hexdigest()[:12], "t": s[:800]},
                           ensure_ascii=False) + "\n")

sections = sorted(set(re.findall(r"^#{1,3} [A-Z][^\n`$]{2,60}$", bundle, re.M)))
open(os.path.join(OUT, "sections.txt"), "w").write("\n".join(sections))


def count(pat):
    return len(re.findall(pat, bundle))


SECTION_TITLES = ["# System", "# Doing tasks", "# Executing actions with care", "# Using your tools",
                  "# Tone and style", "# Harness", "# Text output (does not apply to tool calls)",
                  "# Writing for the user", "# Delivering work", "# Corrections", "# Reporting outcomes",
                  "# Context management", "# Focus mode", "# Background Session", "# Language", "# Machines",
                  "# Environment", "# Communicating with the user"]
HOOKS = ["PreToolUse", "PostToolUse", "PostToolUseFailure", "PostToolBatch", "Notification", "UserPromptSubmit",
         "UserPromptExpansion", "SessionStart", "SessionEnd", "Stop", "StopFailure", "SubagentStart", "SubagentStop",
         "PreCompact", "PostCompact", "PreModelSwitch", "PostModelSwitch", "PermissionRequest", "PermissionDenied",
         "Setup", "TeammateIdle", "TaskCreated", "TaskCompleted", "Elicitation", "ElicitationResult", "ConfigChange",
         "WorktreeCreate", "WorktreeRemove", "InstructionsLoaded", "CwdChanged", "FileChanged", "DirectoryAdded",
         "MessageDisplay"]
TOOLS = ["Bash", "Read", "Edit", "Write", "Glob", "Grep", "WebFetch", "WebSearch", "TodoWrite", "TaskCreate",
         "TaskGet", "TaskUpdate", "TaskList", "Agent", "Task", "SendMessage", "ListAgents", "TaskStop", "Skill",
         "EnterPlanMode", "ExitPlanMode", "AskUserQuestion", "NotebookEdit", "LSP", "Workflow", "CronCreate",
         "ScheduleWakeup", "EnterWorktree", "RemoteTrigger", "ReportFindings", "StructuredOutput"]
FLAGS = ["tengu_velvet_tide", "tengu_velvety_sprout", "tengu_verified_vs_assumed", "tengu_cedar_lantern",
         "tengu_silent_harbor", "tengu_ochre_wren", "tengu_onyx_plover", "tengu_amber_sextant", "tengu_slate_bittern"]
probes = {
    "modules_text": len(mods),
    "modules_binary": bad,
    "bundle_chars": len(bundle),
    "literals_ge120": len(lits),
    "literal_max_len": max((len(s) for _, s in lits), default=0),
    "hook_events_present": [h for h in HOOKS if h in bundle],
    "hook_event_count": sum(1 for h in HOOKS if h in bundle),
    "sections_present": [s for s in SECTION_TITLES if s in bundle],
    "section_count": sum(1 for s in SECTION_TITLES if s in bundle),
    "tools_present": [t for t in TOOLS if f'"{t}"' in bundle],
    "tool_count": sum(1 for t in TOOLS if f'"{t}"' in bundle),
    "todo_thresholds": re.findall(r"TURNS_SINCE_WRITE:\d+,TURNS_BETWEEN_REMINDERS:\d+", bundle)[:1],
    "autocompact_delta": sorted(set(re.findall(r"var \w+=(13000|15000|20000);", bundle))),
    "memory_index_constants": re.findall(r'Wd="MEMORY\.md",NH=(\d+),UQ=(\d+)', bundle)[:1],
    "microcompact": re.findall(r"minIdleSeconds:\d+,keepToolUses:\d+,clearAtLeastTokens:\d+,triggerToolUsesBelowCount:\d+,minTriggerToolUses:\d+", bundle)[:1],
    "output_styles": sorted(set(re.findall(r'name:"(Proactive|Concise|Explanatory|Learning)",source:"built-in"', bundle))),
    "identity_strings": sorted(set(re.findall(r'"(You are Claude Code[^"]{0,70}|You are a Claude agent[^"]{0,70})"', bundle))),
    "dynamic_boundary_sentinel": "yes" if "__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__" in bundle else "no",
    "billing_header": "yes" if "x-anthropic-billing-header:" in bundle else "no",
    "tengu_flag_calls_total": len(set(re.findall(r'tengu_[a-z_]{3,40}', bundle))),
    "named_flags_hit": [f for f in FLAGS if f in bundle],
    "skillify": "# Skillify" in bundle,
    "doctor": "# Claude Code Doctor" in bundle,
    "workflow_authoring": "# Workflow authoring reference" in bundle,
    "dream_memory": "# Dream: Memory Consolidation" in bundle,
    "task_notification_xml": "<task-notification>" in bundle,
    "coordinator_prompt": "orchestrates software engineering tasks across multiple workers" in bundle,
    "readonly_mode_banner": "=== CRITICAL: READ-ONLY MODE" in bundle or "CRITICAL: READ-ONLY MODE" in bundle,
}
json.dump(probes, open(os.path.join(OUT, "probes.json"), "w"), indent=2, ensure_ascii=False)
json.dump({"binary": BIN, "sha256": sha, "bytes": len(data), "modules_text": len(mods),
           "bundle_chars": len(bundle), "literals_ge120": len(lits)},
          open(os.path.join(OUT, "meta.json"), "w"), indent=2)
print(f"{OUT}: modules={len(mods)} chars={len(bundle):,} literals={len(lits)} maxlit={probes['literal_max_len']:,} "
      f"sections={probes['section_count']} hooks={probes['hook_event_count']} tools={probes['tool_count']}")
