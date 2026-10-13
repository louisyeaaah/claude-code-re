#!/usr/bin/env python3
"""跨版本对比「提示词正文」：按模板字面量抽小节正文 + 归一化散文行，避免 minifier 噪声。

用法：cd evolution && python3 diff_evo.py    # 生成 REPORT-evolution.md
"""
import re, os, json, difflib

V = os.path.expanduser("~/.local/share/claude/versions")
ORDER = ["2.1.272", "2.1.282", "2.1.283", "2.1.284", "2.1.286", "2.1.287"]
SECTIONS = ["# System", "# Doing tasks", "# Executing actions with care", "# Using your tools",
            "# Tone and style", "# Harness", "# Text output (does not apply to tool calls)",
            "# Writing for the user", "# Delivering work", "# Corrections", "# Context management",
            "# Communicating with the user", "# Environment"]
MTIME = {"2.1.272": "09-15", "2.1.282": "09-25", "2.1.283": "09-27", "2.1.284": "09-29",
         "2.1.286": "10-02", "2.1.287": "10-02"}
BT = chr(96)
BS = chr(92)
cache = {}


def bundle_of(ver):
    if ver in cache:
        return cache[ver]
    p = f"bundle-{ver}.txt"
    if os.path.exists(p):
        t = open(p, encoding="latin-1").read()
        cache[ver] = t
        return t
    d = open(os.path.join(V, ver), "rb").read()
    bounds = [m.start() + 1 for m in re.finditer(rb"\x00// @bun @bytecode", d)]
    parts = []
    for i, b in enumerate(bounds):
        e = bounds[i + 1] - 1 if i + 1 < len(bounds) else len(d)
        t = d[b:e].decode("latin-1")
        if sum(1 for c in t if c == "\n" or 32 <= ord(c) < 127) / max(1, len(t)) > 0.9:
            parts.append(t)
    txt = "\n".join(parts)
    open(p, "w").write(txt)
    cache[ver] = txt
    return txt


def norm(s):
    s = re.sub(r"\$\{[^{}]*\}", "«»", s)
    s = s.replace(BT, "")
    return re.sub(r"\s+", " ", s).strip()


def enclosing_literal(bundle, idx):
    start = bundle.rfind(BT, 0, idx)
    if start < 0:
        return None
    i = start + 1
    depth = 0
    while i < len(bundle):
        c = bundle[i]
        if c == BS:
            i += 2
            continue
        if depth == 0 and c == BT:
            return bundle[start + 1:i]
        if depth == 0 and c == "$" and i + 1 < len(bundle) and bundle[i + 1] == "{":
            depth = 1
            i += 2
            continue
        if depth > 0:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
        i += 1
    return None


def section_text(bundle, title):
    for m in re.finditer(re.escape(title), bundle):
        t = enclosing_literal(bundle, m.start())
        if t and len(t) < 30000 and title in t:
            return t
    i = bundle.find(title)
    if i < 0:
        return None
    m = re.search(r"\n#[a-zA-Z ]", bundle[i + len(title):])
    j = i + len(title) + m.start() if m else len(bundle)
    return bundle[i:i + min(j - i, 20000)]


IDENT = re.compile(r"^[A-Za-z_$][\w$]{0,7}$")


def substantive(ops, old, new):
    """剔除纯 minifier 标识符改名，只留真正的文字改动。"""
    out = []
    for tag, i1, i2, j1, j2 in ops:
        a, b = old[i1:i2].strip(), new[j1:j2].strip()
        if tag == "replace" and IDENT.match(a) and IDENT.match(b):
            continue
        if tag == "replace" and not a and not b:
            continue
        out.append((tag, i1, i2, j1, j2))
    return out


def prose_lines(bundle):
    out = set()
    for m in re.finditer(r"[A-Z][^\n\"`]{59,400}", bundle):
        t = m.group(0)
        if re.search(r"(function|=>|\(\)|;\s*let |\bvar \b|\breturn\b|\w+\(\w)", t):
            continue
        if sum(c.isalpha() or c in " ,.:;'" for c in t) / len(t) < 0.92:
            continue
        if " " not in t:
            continue
        out.add(norm(t))
    return out


bundles = {v: bundle_of(v) for v in ORDER}
sections = {v: {s: section_text(bundles[v], s) for s in SECTIONS} for v in ORDER}
prose = {v: prose_lines(bundles[v]) for v in ORDER}
probes = {v: json.load(open(f"v{v}/probes.json")) for v in ORDER}

L = []
A = L.append
A("# Claude Code 提示词跨版本演化（2.1.272 → 2.1.287）\n")
A("> 方法：对六个本机安装版本的产物跑同一套切块，抽**小节正文**（取包含标题的那个模板字面量）与**归一化散文行**后对比。")
A("> 归一化 = 去 `${}` 插值、去反引号、压缩空白；只保留英文长句（≥60 字符、无代码符号），以剔除 minifier 改名噪声。\n")

A("## 1. 规模与节奏\n")
A("| 版本 | 构建日期 | 模块数 | 源码字符 | 提示词型字面量(≥120) |")
A("|---|---|---|---|---|")
for v in ORDER:
    m = json.load(open(f"v{v}/meta.json"))
    A(f"| {v} | {MTIME[v]} | {m['modules_text']} | {m['bundle_chars']:,} | {m['literals_ge120']:,} |")

A("\n## 2. 小节正文的逐版本状态\n")
A("（✓=与 2.1.272 完全一致；△N处=有 N 处改动；相似度为归一化后的序列相似度）\n")
A("| 小节 | " + " | ".join(ORDER) + " |")
A("|---" * (len(ORDER) + 1) + "|")
base = {s: norm(sections[ORDER[0]][s] or "") for s in SECTIONS}
for s in SECTIONS:
    row = []
    for v in ORDER:
        t = norm(sections[v][s] or "")
        if not t:
            row.append("✗")
        elif t == base[s]:
            row.append("✓")
        else:
            sm = difflib.SequenceMatcher(None, base[s], t)
            sub = substantive(sm.get_opcodes(), base[s], t)
            row.append("✓" if not sub else f"△{len(sub)}处/{sm.ratio():.2f}")
    A(f"| `{s}` | " + " | ".join(row) + " |")

A("\n## 3. 小节内容相对最早版本的真实改动\n")
for s in SECTIONS:
    rows = []
    for v in ORDER:
        t = norm(sections[v][s] or "")
        if t and t != base[s]:
            sm = difflib.SequenceMatcher(None, base[s], t)
            ops = substantive([op for op in sm.get_opcodes() if op[0] != "equal"], base[s], t)
            if ops:
                rows.append((v, len(base[s]), len(t), sm.ratio(), ops, base[s], t))
    if not rows:
        continue
    A(f"### `{s}`")
    for v, a_len, b_len, ratio, ops, old, new in rows:
        A(f"- **{v}**：{a_len} → {b_len} 字符，相似度 {ratio:.3f}，{len(ops)} 处改动")
        for tag, i1, i2, j1, j2 in ops[:3]:
            if tag in ("replace", "delete"):
                A(f"    - 旧：`{old[i1:i2][:130]}`")
            if tag in ("replace", "insert"):
                A(f"    - 新：`{new[j1:j2][:130]}`")
    A("")

A("\n## 4. 整句级增删（相邻版本，按长度取前 6）\n")
prev = None
for v in ORDER:
    if prev:
        a, b = prose[prev], prose[v]
        A(f"### {prev} → {v}")
        A(f"- 共有 {len(a & b):,} / 新增 {len(b - a):,} / 消失 {len(a - b):,}")
        for t in sorted(b - a, key=len, reverse=True)[:6]:
            A(f"    - 新增：{t[:150]}")
        for t in sorted(a - b, key=len, reverse=True)[:4]:
            A(f"    - 消失：{t[:150]}")
        A("")
    prev = v

A("\n## 5. 结构性探针（常量/清单是否随版本变化）\n")
A("| 探针 | " + " | ".join(ORDER) + " |")
A("|---" * (len(ORDER) + 1) + "|")
keys = ["hook_event_count", "todo_thresholds", "memory_index_constants", "output_styles",
        "dynamic_boundary_sentinel", "billing_header", "skillify", "doctor", "dream_memory",
        "workflow_authoring", "coordinator_prompt", "task_notification_xml", "tengu_flag_calls_total",
        "section_count", "tool_count"]
for k in keys:
    vals = [json.dumps(probes[v][k], ensure_ascii=False)[:36] for v in ORDER]
    A(f"| {k} | " + " | ".join(vals) + " |")

open("REPORT-evolution.md", "w").write("\n".join(L) + "\n")
print("wrote REPORT-evolution.md")
