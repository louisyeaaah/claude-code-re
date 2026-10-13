#!/usr/bin/env python3
"""步骤 4a：源码语料完整性核对。

思路：二进制里除 177.8–219.0 MB 的 ASCII 模块源码区外，还有 ~150 MB 的二进制/字节码区。
若某个提示词只存在于字节码区、不在源码区，我们的语料就有缺口。
做法：从非源码区抽出所有「句子型」ASCII 串，逐个在源码语料里找；把找不到的按长度排序输出。
"""
import re, os, sys, json, collections

BIN = "~/.local/share/claude/versions/2.1.287"
SRC_LO, SRC_HI = 177_838_376, 219_016_033     # ASCII 模块源码区
d = open(BIN, "rb").read()

# 源码语料（已切好的模块）
corpus = []
for f in os.listdir("raw/chunks2"):
    corpus.append(open(os.path.join("raw/chunks2", f), encoding="latin-1").read())
corpus = "\n".join(corpus)

# 非源码区
outside = d[:SRC_LO] + d[SRC_HI:]
runs = re.findall(rb"[\x20-\x7e]{24,}", outside)
print(f"非源码区 ASCII 串(>=24): {len(runs):,}")

def sentenceish(s):
    t = s.decode("latin-1")
    if " " not in t:
        return False
    letters = sum(c.isalpha() for c in t)
    if letters / len(t) < 0.55:
        return False
    words = t.split()
    if len(words) < 4:
        return False
    if t.count("/") > len(t) / 12:          # 路径
        return False
    if re.fullmatch(r"[A-Za-z0-9_.\-/=+ ]+", t) and len(words) < 6:
        return False
    return True

cands = []
seen = set()
for s in runs:
    if not sentenceish(s):
        continue
    t = s.decode("latin-1")
    key = re.sub(r"\s+", " ", t).strip()
    if key in seen:
        continue
    seen.add(key)
    cands.append(key)
print(f"句子型候选: {len(cands):,}")

missing = [c for c in cands if c not in corpus]
print(f"源码语料中找不到的: {len(missing):,}  ({len(missing)/max(1,len(cands)):.1%})")

by_first = sorted(missing, key=lambda x: -len(x))
json.dump({"candidates": len(cands), "missing": len(missing),
           "missing_top": by_first[:400]}, open("verify/bytecode-gap.json", "w"),
          indent=2, ensure_ascii=False)

print("\n=== 最长的 25 条「只存在于非源码区」的句子 ===")
for m in by_first[:25]:
    print(f"  [{len(m):>4}] {m[:160]}")
print("\n=== 其中含提示词味道关键词的 ===")
KEY = ("You are", "you must", "IMPORTANT", "Do not", "should", "the user", "This tool", "NEVER", "When ")
hits = [m for m in missing if any(k in m for k in KEY)]
print(f"命中 {len(hits)} 条，示例：")
for m in hits[:20]:
    print("  •", m[:150])
json.dump(hits[:300], open("verify/bytecode-gap-promptish.json", "w"), indent=2, ensure_ascii=False)
