#!/usr/bin/env python3
"""对比"默认预算"与"榨干预算"两轮 Ghidra 反编译结果。

用法：python3 tools/compare_ghidra_runs.py
输入：out/{cua,input,audio}-all.txt（第一轮：90s/1024）
      out/max-{cua,input,audio}.txt（第二轮：1200s/16384）
输出：控制台表格 + out/max-comparison.json
"""
import re, os, json

PAIRS = [("cua", "out/cua-all.txt", "out/max-cua.txt"),
         ("input", "out/input-all.txt", "out/max-input.txt"),
         ("audio", "out/audio-all.txt", "out/max-audio.txt")]

rows = []
for name, old, new in PAIRS:
    if not os.path.exists(new):
        print(f"!! 缺少 {new}（第二轮还没跑完）")
        continue
    o = open(old, encoding="utf-8", errors="replace").read()
    n = open(new, encoding="utf-8", errors="replace").read()
    ob = re.split(r"^// ==== ", o, flags=re.M)[1:]
    nb = re.split(r"^// ==== ", n, flags=re.M)[1:]
    r = {
        "lib": name,
        "functions_old": len(ob), "functions_new": len(nb),
        "incomplete_old": sum(1 for b in ob if "decompile incomplete" in b or "decompile error" in b),
        "incomplete_new": sum(1 for b in nb if "decompile incomplete" in b or "decompile error" in b),
        "jumptable_old": o.count("Could not recover jumptable"),
        "jumptable_new": n.count("Could not recover jumptable"),
        "typeprop_old": sum(1 for b in ob if "Type propagation" in b),
        "typeprop_new": sum(1 for b in nb if "Type propagation" in b),
        "unreachable_old": o.count("Removing unreachable block"),
        "unreachable_new": n.count("Removing unreachable block"),
        "chars_old": len(o), "chars_new": len(n),
    }
    slow = new + ".slow.txt"
    if os.path.exists(slow):
        times = [int(l.split("\t")[0]) for l in open(slow) if l.strip() and not l.startswith("#")]
        r["slow_count"] = len(times)
        r["slow_max"] = max(times) if times else 0
        r["slow_total"] = sum(times)
    rows.append(r)

print(f"{'库':6s} {'函数':>12s} {'未完成':>10s} {'跳转表告警':>16s} {'类型传播':>12s} {'反编译文本':>18s} {'慢函数(≥20s)':>14s}")
for r in rows:
    print(f"{r['lib']:6s} {r['functions_old']:>5d}→{r['functions_new']:<5d} "
          f"{r['incomplete_old']:>4d}→{r['incomplete_new']:<4d} "
          f"{r['jumptable_old']:>7d}→{r['jumptable_new']:<7d} "
          f"{r['typeprop_old']:>5d}→{r['typeprop_new']:<5d} "
          f"{r['chars_old']/1e6:>7.2f}→{r['chars_new']/1e6:<7.2f}MB "
          f"{r.get('slow_count','-'):>6} 个 (最慢 {r.get('slow_max','-')}s)")

json.dump(rows, open("out/max-comparison.json", "w"), indent=2, ensure_ascii=False)
print("\nwrote out/max-comparison.json")
