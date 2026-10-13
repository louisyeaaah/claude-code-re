#!/usr/bin/env python3
"""把抓到的真实请求与静态还原结果做逐条对照。

输入：captured/lean/*.body.json、captured/full/*.body.json
输出：verify/REPORT-dynamic.md 的控制台摘要（正文人工撰写，本脚本只给判据）
"""
import json, glob, re, os, sys

PROBES = [
    ("身份句（SDK 变体）", "You are a Claude agent, built on Anthropic's Claude Agent SDK.", "static: X0"),
    ("身份句（CLI 变体）", "You are Claude Code, Anthropic's official CLI for Claude.", "static: Qw"),
    ("安全基线 vMe", "IMPORTANT: Assist with authorized security testing, defensive security, CTF challenges", "01 §3"),
    ("# System 五条", "Tools are executed in a user-selected permission mode.", "01 §3.1"),
    ("system-reminder 归属", "bear no direct relation to the specific tool results or user messages in which they appear",
     "01 §3.1"),
    ("自动压缩说明", "The system will automatically compress prior messages in your conversation as it approaches context limits.",
     "01 §3.1"),
    ("# Doing tasks：不要多余抽象", "Don't add features, refactor, or introduce abstractions beyond what the task requires.", "01 §3.2"),
    ("# Doing tasks：默认不写注释", "Default to writing no comments. Only add one when the WHY is non-obvious", "01 §3.2"),
    ("# Doing tasks：优先改现有文件", "Prefer editing existing files to creating new ones.", "01 §3.2"),
    ("# Executing actions with care", "Carefully consider the reversibility and blast radius of actions.", "01 §3.3"),
    ("授权语义 once≠always", "does NOT mean that they approve it in all contexts", "01 §3.3"),
    ("# Using your tools 并行规则", "make all independent tool calls in parallel", "01 §3.4"),
    ("# Tone and style：emoji", "Only use emojis if the user explicitly requests it.", "01 §3.5"),
    ("# Tone and style：不要冒号", "Do not use a colon before tool calls.", "01 §3.5"),
    ("# Harness 段落", "# Harness", "01 §3.6"),
    ("# Text output", "# Text output (does not apply to tool calls)", "01 §4"),
    ("# Context management", "# Context management", "01 §4"),
    ("# Environment", "# Environment", "01 §4"),
    ("billing header 首块", "x-anthropic-billing-header: cc_version=", "05 §2 / 06"),
]


def norm(s):
    return re.sub(r"\s+", " ", s)


def analyze(tag, path):
    b = json.load(open(path))
    sysb = b.get("system") or []
    full = norm("\n\n".join(s.get("text", "") for s in sysb))
    out = {"tag": tag, "file": path, "model": b.get("model"), "blocks": len(sysb),
           "chars": len(full), "tools": len(b.get("tools") or []),
           "tool_names": [t.get("name") for t in (b.get("tools") or [])],
           "block_meta": [{"chars": len(s.get("text", "")), "cache_control": s.get("cache_control"),
                           "head": s.get("text", "")[:60]} for s in sysb]}
    hits = []
    for label, probe, ref in PROBES:
        hits.append((label, probe in full, ref))
    out["probes"] = hits
    out["sections"] = re.findall(r"^#{1,2} .*$", full, re.M)
    return out


rows = []
for tag, pat in (("lean", "captured/lean/*.body.json"), ("full", "captured/full/*.body.json")):
    fs = sorted(glob.glob(pat))
    if not fs:
        print(f"!! no capture for {tag}")
        continue
    # 取最大的一次（主请求）
    best = max(fs, key=lambda f: os.path.getsize(f))
    rows.append(analyze(tag, best))

for r in rows:
    print("=" * 78)
    print(f"{r['tag']}: {r['file']}")
    print(f"  model={r['model']} blocks={r['blocks']} chars={r['chars']} tools={r['tools']}")
    for i, m in enumerate(r["block_meta"]):
        print(f"   block{i}: {m['chars']:>7,}B cache_control={m['cache_control']} head={m['head']!r}")
    print("  sections:", r["sections"])
    print("  探针命中：")
    miss = 0
    for label, ok, ref in r["probes"]:
        if not ok:
            miss += 1
        print(f"    [{'✓' if ok else '✗'}] {label:32s} ({ref})")
    print(f"  命中 {len(r['probes'])-miss}/{len(r['probes'])}")

json.dump(rows, open("comparison.json", "w"), indent=2, ensure_ascii=False)
print("\nwrote verify/comparison.json")
