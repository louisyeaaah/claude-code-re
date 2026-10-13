#!/usr/bin/env python3
"""抽取 Claude Code 单文件产物里内嵌的 zstd 压缩资源（插件技能、模板、参考文档）。

用法：python3 tools/extract_assets.py [binary] [outdir]
产出：<outdir>/asset-NNN-<slug>.md / .txt、<outdir>/index.json
"""
import os, re, sys, json, hashlib
import zstandard as zstd

BIN = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.local/share/claude/versions/2.1.287")
OUT = sys.argv[2] if len(sys.argv) > 2 else "work/assets"
os.makedirs(OUT, exist_ok=True)

d = open(BIN, "rb").read()
offs = [m.start() for m in re.finditer(rb"\x28\xb5\x2f\xfd", d)]
dctx = zstd.ZstdDecompressor()
print(f"binary {len(d):,} bytes, zstd frames: {len(offs)}")

records = []
for i, o in enumerate(offs):
    try:
        raw = dctx.decompress(d[o:o + 3_000_000], max_output_size=16_000_000)
    except Exception as e:
        records.append({"i": i, "off": o, "error": str(e)[:80]})
        continue
    text = raw.decode("utf-8", "replace")
    head = text.lstrip()
    fm = re.match(r"---\n(.*?)\n---\n", text, re.S)
    fname = re.search(r"^name:\s*(.+)$", fm.group(1), re.M) if fm else None
    title = None
    m = re.search(r"^#{1,2}\s+(.+)$", text, re.M)
    if m:
        title = m.group(1).strip()[:80]
    fm_name = fname.group(1).strip().strip('"') if fname else None
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", (fm_name or title or "asset"))[:48].strip("-") or "asset"
    ext = ".md" if head.startswith(("---", "#", "<!--")) else ".txt"
    fn = f"asset-{i:03d}-{slug}{ext}"
    open(os.path.join(OUT, fn), "w", encoding="utf-8").write(text)
    records.append({
        "i": i, "off": o, "file": fn, "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest()[:16],
        "region": "bun" if o < 0x4000000 else "claude",
        "frontmatter_name": fm_name, "title": title,
        "first_line": text.split("\n", 1)[0][:100],
    })

json.dump(records, open(os.path.join(OUT, "index.json"), "w"), indent=1, ensure_ascii=False)
claude = [r for r in records if r.get("region") == "claude"]
bun = [r for r in records if r.get("region") == "bun"]
print(f"extracted: {len([r for r in records if 'file' in r])}  (claude-region {len(claude)}, bun-region {len(bun)}, failed {len([r for r in records if 'error' in r])})")
print(f"total decompressed: {sum(r.get('bytes',0) for r in records):,} bytes")
print("\nClaude Code 侧资源（按大小，前 25）：")
for r in sorted(claude, key=lambda x: -x.get("bytes", 0))[:25]:
    print(f"  {r['bytes']:>9,}B  {r['frontmatter_name'] or (r['title'] or '')[:40]:<40} {r['file']}")
