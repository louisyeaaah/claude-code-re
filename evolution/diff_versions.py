#!/usr/bin/env python3
"""按顺序对比六个版本的提取结果，生成 evolution/REPORT-evolution.md 的素材 + 表格。"""
import json, os, hashlib, collections, sys

ORDER = ["v2.1.272", "v2.1.282", "v2.1.283", "v2.1.284", "v2.1.286", "v2.1.287"]
MTIME = {"v2.1.272": "09-15", "v2.1.282": "09-25", "v2.1.283": "09-27", "v2.1.284": "09-29",
         "v2.1.286": "10-02", "v2.1.287": "10-02"}

meta = {v: json.load(open(f"{v}/meta.json")) for v in ORDER}
probes = {v: json.load(open(f"{v}/probes.json")) for v in ORDER}
secs = {v: [l for l in open(f"{v}/sections.txt").read().split("\n") if l] for v in ORDER}
lits = {}
for v in ORDER:
    s = {}
    for line in open(f"{v}/prompts.jsonl"):
        o = json.loads(line)
        s[o["h"]] = o
    lits[v] = s

print("## 规模与节奏\n")
print("| 版本 | 构建日期 | 模块数 | 源码字符 | 字面量(≥120) | 小节标题数 |")
print("|---|---|---|---|---|---|")
for v in ORDER:
    m = meta[v]
    print(f"| {v[1:]} | {MTIME[v]} | {m['modules_text']} | {m['bundle_chars']:,} | {m['literals_ge120']:,} | {len(secs[v])} |")

print("\n## 探针逐版本对照\n")
keys = ["hook_event_count", "todo_thresholds", "autocompact_delta", "memory_index_constants", "microcompact",
        "output_styles", "identity_strings", "dynamic_boundary_sentinel", "billing_header", "skillify", "doctor",
        "dream_memory", "workflow_authoring", "coordinator_prompt", "task_notification_xml", "tengu_flag_calls_total"]
for k in keys:
    row = [json.dumps(probes[v][k], ensure_ascii=False) for v in ORDER]
    if len(set(row)) == 1:
        print(f"- **{k}**：6 个版本完全相同 → `{row[0][:120]}`")
    else:
        print(f"- **{k}**：")
        for v, r in zip(ORDER, row):
            print(f"    - {v[1:]}: {r[:200]}")

print("\n## 小节标题的增删\n")
base = set(secs[ORDER[0]])
for v in ORDER[1:]:
    cur = set(secs[v])
    add = sorted(cur - base)
    rem = sorted(base - cur)
    if add or rem:
        print(f"- {v[1:]}: +{len(add)} / -{len(rem)}")
        for a in add[:12]:
            print(f"    + {a}")
        for r in rem[:8]:
            print(f"    - {r}")
    base = cur

print("\n## 相邻版本的提示词集合差异（按字面量内容 md5）\n")
print("| 对比 | 新增 | 删除 | 两版共有 |")
print("|---|---|---|---|")
prev = None
for v in ORDER:
    if prev:
        a, b = lits[prev], lits[v]
        add = set(b) - set(a)
        rem = set(a) - set(b)
        print(f"| {prev[1:]} → {v[1:]} | {len(add):,} | {len(rem):,} | {len(set(a)&set(b)):,} |")
    prev = v

print("\n## 每个区间的「新增提示词」示例（≥300 字符，按长度降序取 6 条）\n")
prev = None
for v in ORDER:
    if prev:
        a, b = lits[prev], lits[v]
        add = [b[h] for h in set(b) - set(a) if b[h]["n"] >= 300]
        add.sort(key=lambda x: -x["n"])
        print(f"### {prev[1:]} → {v[1:]}（新增 {len(add)} 条 ≥300 字符，示例）")
        for o in add[:6]:
            t = " ".join(o["t"].split())[:180]
            print(f"- [{o['n']}] {t}")
        print()
    prev = v
