#!/usr/bin/env python3
"""逐函数对比两轮反编译输出：默认预算 vs 榨干预算。

不是只比告警计数——而是把每个函数的伪代码正文规范化后哈希对比，
找出真正有差异的函数（新增内容 / 改善 / 退化）。

用法：python3 tools/diff_decomp_runs.py
"""
import re, os, hashlib, json

PAIRS = [("cua", "out/cua-all.txt", "out/max-cua.txt"),
         ("input", "out/input-all.txt", "out/max-input.txt"),
         ("audio", "out/audio-all.txt", "out/max-audio.txt")]


def parse(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    out = {}
    for chunk in re.split(r"^// ==== ", t, flags=re.M)[1:]:
        head, _, body = chunk.partition("\n")
        name = head.split(" @ ")[0].strip()
        norm = re.sub(r"\s+", " ", re.sub(r"/\*.*?\*/", "", body, flags=re.S)).strip()
        out[name] = {"h": hashlib.md5(norm.encode()).hexdigest()[:12],
                     "len": len(norm), "raw_len": len(body),
                     "bad": ("decompile incomplete" in body or "decompile error" in body),
                     "jt": body.count("Could not recover jumptable")}
    return out


summary = []
for lib, old, new in PAIRS:
    if not os.path.exists(new):
        print(f"!! 缺 {new}")
        continue
    a, b = parse(old), parse(new)
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    diffs = []
    for k in set(a) & set(b):
        if a[k]["h"] != b[k]["h"]:
            diffs.append((k, a[k]["len"], b[k]["len"], a[k]["jt"], b[k]["jt"]))
    improved = [d for d in diffs if d[2] > d[1]]
    worsened = [d for d in diffs if d[2] < d[1]]
    fixed = [k for k in set(a) & set(b) if a[k]["bad"] and not b[k]["bad"]]
    broke = [k for k in set(a) & set(b) if not a[k]["bad"] and b[k]["bad"]]
    summary.append({"lib": lib, "functions": len(b), "same_hash": len(set(a) & set(b)) - len(diffs),
                    "changed": len(diffs), "bigger": len(improved), "smaller": len(worsened),
                    "fixed_incomplete": sorted(fixed), "newly_incomplete": sorted(broke),
                    "missing_in_new": only_a, "new_in_new": only_b})
    print(f"=== {lib}: {len(b)} 个函数")
    print(f"    逐字节相同(规范化后): {len(set(a) & set(b)) - len(diffs)}   有差异: {len(diffs)}（变大 {len(improved)} / 变小 {len(worsened)}）")
    print(f"    从 incomplete 变正常: {len(fixed)} {fixed[:5]}")
    print(f"    反而变坏的: {len(broke)} {broke[:5]}")
    if improved[:5]:
        print("    变化最大的几个（规范化长度 旧→新）:")
        for k, l1, l2, j1, j2 in sorted(improved, key=lambda x: -(x[2] - x[1]))[:5]:
            print(f"      {k[:60]:60s} {l1:>6}→{l2:<6}  跳转表 {j1}→{j2}")

json.dump(summary, open("out/max-diff.json", "w"), indent=2, ensure_ascii=False)
print("\nwrote out/max-diff.json")
