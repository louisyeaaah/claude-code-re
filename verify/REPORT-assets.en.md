> English version. 中文原版：[REPORT-assets.md](REPORT-assets.md)

# Embedded assets of Claude Code v2.1.287 (168 of 169 zstd frames)

> Target: `~/.local/share/claude/versions/2.1.287` (227,827,120 bytes, sha256 prefix `6eab8333fe212155`)
> Material: 168 decompressed files under [work/assets/](work/assets/) plus [index.json](work/assets/index.json); extractor [tools/extract_assets.py](tools/extract_assets.py)
> Method: zstd magic scan + the `zstandard` module; **not** an exact filename-table mapping (see §5)

## 0. Headline findings

- The binary contains **169** zstd frames; **168** decompress, totalling **11,283,111 bytes (11.28 MB)**: 135 on the Claude side (9,908,273 B / 9.91 MB) and 33 in the Bun runtime region (1,374,838 B / 1.37 MB).
- The single failure (index 33, offset `0x3b7a43c`) is in the **Bun region**: its frame header asks for an external zstd dictionary (`Dictionary mismatch`) and the surrounding bytes are Bun string tables, so a magic-byte false positive is the likelier reading. **All 135 Claude-side frames decompressed.**
- The two regions are measured, not guessed: Bun frames cluster at `0x388cbb3`-`0x3a02f95` (59.3-60.8 MB) and Claude frames at `0xd0dfe8e`-`0xd858d9d` (219.0-226.9 MB); the 151 MB between them is JSC bytecode and modules.
- The name table (`/$bunfs/root/<name>-<hash>.<ext>[.zst]`) spans `0xd85b83d`-`0xd87eac9`: about **230** non-chunk entries and ~2169 chunk entries, which is where the earlier report's "231 non-chunk resources" came from.
- Names and contents **cannot** be derived one from the other: in-binary loader references plus content fingerprints pin down exactly **11** pairs (6 whiteboard files and mermaid/hljs/Chart.js/PSL/function-hooks .d.ts); the rest only support a monotone "frame order = name order" statement.
- The `.zst` suffix in the name table is **not** a compression indicator: `mermaid.min.js`, `chart.umd.min.js` and `hljsBundle.generated.min.js` carry no `.zst` yet are zstd frames (3.5 MB / 208 KB / 593 KB of decompressed output in the table below).
- Between frames there are also **uncompressed** sibling resources (that is where the no-`.zst` names live): three non-1-byte gaps in the Claude region total 4,721,613 bytes - two WOFF2 fonts, at least four design/slides prompt docs, at least six Mach-O slices, `audio-capture.node`, and a 10 KB autonomous-loop prompt.

## 1. Method and reproducibility

### 1.1 Extraction pipeline

1. Read the whole binary and scan for `\x28\xb5\x2f\xfd` (the zstd magic) -> 169 candidate offsets;
2. For each offset take `d[o:o+3_000_000]` and hand it to `zstandard.ZstdDecompressor().decompress(..., max_output_size=16_000_000)`;
3. Decode as UTF-8 (`errors=replace`), slug the filename from the frontmatter `name:` or the first heading, and record offset, decompressed size, sha256 prefix and region.

Key lines: [extract_assets.py:15-16](tools/extract_assets.py#L15-L16) (magic scan and decompressor) and [extract_assets.py:42](tools/extract_assets.py#L42) (region test `o < 0x4000000`). The region test only affects labelling, never the decompressed bytes.

### 1.2 Why slicing and feeding `zstd -d` fails

Consecutive frames are separated by **exactly one `0x00` pad byte** (measured gap = 1) and frame length has no prefix: only decoding reveals the end, while a magic scan only gives the next start. First-hand comparison with `/opt/homebrew/bin/zstd`:

| Slice | Command | Result |
|---|---|---|
| frame start -> next magic (pad byte included) | `zstd -d -c slice_exact.zst` | exit 0, but stderr says `unknown header` (one extra trailing byte) |
| start -> start + 3 MB fixed window | `zstd -d -c slice_over.zst` | `unsupported format`, fails |
| truncated to the first 1000 bytes | `zstd -d -c slice_short.zst` | `Read error (39) : premature end`, fails |
| shifted 500 bytes earlier | `zstd -d -c slice_prev.zst` | `unsupported format`, fails |

In short: find the start by magic scan, find the end by decoding (or tolerate the 1-byte pad); a raw byte range is not a usable stream.

### 1.3 Success rate and the failed frame

- 169 frames / 168 successes (99.4%); Claude side 135/135, Bun side 33/34.
- Failed frame index 33 at `off=0x3b7a43c`, error `Dictionary mismatch`. The frame header descriptor `0x62` declares a 1-byte dictionary ID, so a dictionary is required; but the bytes around it are Bun string tables (`elselinklogsglob`, `pretestNODE />`) and it sits ~1.5 MB away from the Bun frame cluster. **Both readings stay open**: a real frame needing a dictionary, or a magic-byte false positive.

### 1.4 Why the split is bun 33 vs claude 135

The artifact is a `bun build --compile` executable: Bun's own runtime assets come first, Claude Code's own `$bunfs/root/` payload comes later.

| Region | Frames | Offset range | Decompressed | Content signature |
| `bun` | 33 | `0x388cbb3`-`0x3a02f95` (59.3-60.8 MB) | 1,374,838 | Bun error-page CSS (asset-000), RSC client logic (003), bun completions (005/007), npm package-name table (008, 162 KB), `node:` polyfills (010/013/016/024/032), util/path/net/tls/buffer shims |
| `claude` | 135 | `0xd0dfe8e`-`0xd858d9d` (219.0-226.9 MB) | 9,908,273 | the 135 resources of §2; the name table `0xd85b83d`-`0xd87eac9` follows immediately |

The `0x4000000` (64 MB) threshold is only an empirical separator; it falls inside the 151 MB hole between 60.8 MB and 219.0 MB and changes no assignment.

## 2. All 135 Claude-side resources, largest first

The Type column is this report's own grouping (3rd-party = vendored, skill = SKILL/command doc with `---` frontmatter, skill support = that skill's own templates and scripts, reference = documentation, html, script = JS/Python, types = `.d.ts`, data = JSON). Every summary was written after reading the first lines of that file; entries not read beyond the head say so.

| Bytes | Lines | Extracted file | Type | One-line summary |
|---|---|---|---|---|
| 3,566,058 | 3587 | `asset-048-asset.txt` | 3rd-party | Full mermaid 11.16.1 bundle (3.5 MB); also carries the license notices of DOMPurify 3.4.0 and lodash inside (see 3.4) |
| 593,163 | 47 | `asset-035-asset.txt` | 3rd-party | highlight.js 11.11.1 browser IIFE, 186 grammars; header says it is generated by scripts/generate-hljs-browser-bundle.ts (BSD-3-Clause) |
| 573,702 | 14914 | `asset-044-asset.txt` | types | TypeScript declarations for the function-hooks plugin API; the header says EARLY ACCESS and that the engine writes it beside each mod as .claude-plugin/types/claude-code/index.d.ts |
| 329,237 | 4554 | `asset-162-asset.txt` | html | whiteboard template (329 KB, <title>Whiteboard</title>, inlined @ant/cds token sheet) |
| 317,800 | 2253 | `asset-143-Model-Migration-Guide.md` | reference | Model Migration Guide: migration steps, per-SDK syntax differences, breaking changes and deprecated parameters; routed from /claude-api migrate |
| 208,522 | 14 | `asset-034-asset.txt` | 3rd-party | Chart.js v4.5.1 UMD bundle (MIT banner on line 1); ships Colors/Decimation/Filler/Legend plugins inline |
| 167,048 | 1 | `asset-063-asset.txt` | 3rd-party | Public suffix list JSON: source publicsuffix.org, license MPL-2.0, version 2026-09-08_12-18-37_UTC (ICANN + PRIVATE) |
| 154,540 | 2710 | `asset-159-asset.txt` | html | whiteboard template (154 KB, <title>Whiteboard</title>, external Google Fonts) |
| 127,802 | 3094 | `asset-041-asset.md` | skill support | workshop-page direct-HTML template (the blessed *.workshop.html shape) with the publish-time structural verification rules |
| 117,526 | 2962 | `asset-040-asset.md` | skill support | workshop artifact HTML template (frontmatter in an HTML comment: name: workshop); documents four mechanical fill slots {{TITLE}}/{{TAB_TITLE}}/{{EYEBROW}}/{{SUMMARY}} |
| 105,678 | 1142 | `asset-163-asset.txt` | script | whiteboard helper = **merge-state.mjs** (live variant; its usage comment runs `node merge-state.mjs`): reads board state, appends elements clear of what is already there |
| 101,940 | 936 | `asset-054-asset.md` | script | Claude Test main CLI: spec writing, git commit state, runs directory and logs (inferred ct.mjs) |
| 100,774 | 595 | `asset-118-Building-LLM-Powered-Applications-with-Claude.md` | reference | Building LLM-Powered Applications with Claude: choose the surface first; the body carries {{FABLE_NAME}}/{{OPUS_NAME}} placeholders and a "your training prior may be stale" warning |
| 96,305 | 1769 | `asset-157-asset.txt` | html | 96 KB self-contained HTML template whose <title> holds '<!-- SLOT: TITLE ...'; inferred to be one of the artifact/plan templates (body not read in full) |
| 95,251 | 158 | `asset-043-Environment.md` | reference | The "# Environment" context-slot doc: three kinds of slot plus the <user_environment_to_replace> block |
| 94,008 | 1532 | `asset-148-With-stdout-stderr-redirected-to-a-pipe-as-under.md` | script | prefix_diff.py: diff two consecutive Messages requests in the parts a thinking block is bound to |
| 88,532 | 1748 | `asset-038-asset.md` | skill support | HTML body fragment for artifact-pr-review (no doctype/html/head wrapper); the comment requires escaping every PR-derived string |
| 88,266 | 1482 | `asset-160-asset.txt` | script | whiteboard helper = **board.mjs** (solo variant; its usage comment runs `node board.mjs`): reads the board and PNG-snapshot islands the page embeds and writes the republishable page |
| 80,310 | 513 | `asset-166-Plugin-eval-claude-plugin-eval-and-skill-doctor.md` | reference | Plugin eval reference: case.yaml fields, graders, MCP mocks, run options, exit codes, HTML report |
| 77,274 | 2232 | `asset-045-asset.txt` | script | Multi-module JS concatenated with '//// <path>' banners (collector/*: create-collector, hold-of, mock-clock...); [REPORT-plugin-api.md](verify/REPORT-plugin-api.md) identifies it as the source of the function-hooks `claude plugin test` suite - quoted from that report, not read closely here |
| 70,477 | 857 | `asset-067-asset.md` | script | Claude Test run-log reader: line-by-line JSON error-answer detection |
| 69,242 | 340 | `asset-084-Storybook-source-shape.md` | reference | Storybook source shape: Storybook is the fidelity oracle, not the runtime; Playwright+chromium are required |
| 69,156 | 338 | `asset-127-Hill-Climbing-on-an-Eval.md` | reference | Hill-Climbing on an Eval |
| 66,582 | 1066 | `asset-149-With-stdout-stderr-redirected-to-a-pipe-as-under.md` | script | drop_block_probe.py: replay a captured conversation and report what the API drops and why |
| 65,592 | 1547 | `asset-072-asset.txt` | skill support | The workshop decisions script: decision-block interaction on the page |
| 64,004 | 249 | `asset-146-Preserved-Thinking---Keeping-Earlier-Reasoning-V.md` | reference | Preserved Thinking - keeping earlier reasoning valid across a conversation |
| 59,209 | 289 | `asset-082-Package-source-shape.md` | reference | Package source shape: components come from dist + .d.ts when there is no Storybook |
| 59,098 | 501 | `asset-071-Claude-Test-the-conversation-side.md` | skill | Claude Test main skill: runs plain-language specs against the local app and returns PASS/FAIL plus screenshots |
| 58,092 | 244 | `asset-122-Cost-Optimization---Cutting-Spend-per-Completed.md` | reference | Cost Optimization: optimize cost per completed task, not cost per token |
| 56,307 | 919 | `asset-057-asset.txt` | script | Claude Test config layer: RC file, private dir, key validation and warnings (inferred config.mjs) |
| 55,699 | 1005 | `asset-085-asset.md` | script | design-sync converter main script (package-build.mjs): bundles a design system into the DS-project layout |
| 55,191 | 235 | `asset-124-Building-an-Eval-for-a-Claude-Powered-Applicatio.md` | reference | Building an Eval |
| 51,938 | 805 | `asset-086-asset.md` | script | package-validate.mjs: shape checks plus a sampled render check of the output dir |
| 48,945 | 237 | `asset-150-Prompt-Audit---Finding-and-Removing-Dated-Prompt.md` | reference | Prompt Audit: find and remove dated prompting patterns |
| 46,110 | 753 | `asset-097-asset.md` | script | compare.mjs: capture self-contained previews against the repo's own storybook renders |
| 44,225 | 577 | `asset-152-Tool-Use-Concepts.md` | reference | Tool Use Concepts |
| 42,953 | 498 | `asset-070-Claude-Test-runner-drive-the-app-in-a-browser-ju.md` | skill | Claude Test internal skill: drives the app in a background browser (browser_* MCP allowlist) |
| 42,525 | 688 | `asset-036-artifact-pr-review.md` | skill | artifact-pr-review: turns a GitHub PR into a structured review briefing (bottom line, recommendation, visual explainer, decision blocks); the body embeds an HTML template |
| 40,528 | 725 | `asset-039-workshop.md` | skill | workshop: build a design with the user one decision at a time and publish it as an evolving document |
| 39,653 | 98 | `asset-147-Preserved-Thinking---Causes-Fixes-and-the-Keep-L.md` | reference | Preserved Thinking - causes, fixes and the keep list |
| 38,063 | 1087 | `asset-046-asset.md` | skill support | plan artifact HTML template (name: plan) with the {{TITLE}} fill contract and the @ant/cds vanilla token note |
| 37,817 | 682 | `asset-093-Where-things-are.txt` | reference | Where things are: the design-sync artifact and file map |
| 35,661 | 504 | `asset-141-Managed-Agents---Tools-Skills.md` | reference | Managed Agents - Tools & Skills |
| 34,396 | 455 | `asset-130-Managed-Agents---Endpoint-Reference.md` | reference | Managed Agents - Endpoint Reference |
| 33,603 | 500 | `asset-064-asset.txt` | script | Claude Test skill parsing: parseSkillMd and friends |
| 33,036 | 297 | `asset-151-Prompt-Caching---Design-Optimization.md` | reference | Prompt Caching - design and optimization: the prefix-match invariant |
| 32,832 | 359 | `asset-132-Managed-Agents---Core-Concepts.md` | reference | Managed Agents - Core Concepts |
| 32,005 | 144 | `asset-050-Function-hooks-the-long-form.md` | reference | Function hooks, the long form: what a plugin is, how the engine loads it, what it can hook |
| 31,711 | 442 | `asset-126-Cost-reduction-search-how-to-structure-it.md` | reference | How to structure a cost-reduction search |
| 31,080 | 500 | `asset-037-artifact-pr-review.md` | skill | A second version of the same skill: same PR briefing, stressing that PR text is untrusted input and must be escaped |
| 30,120 | 542 | `asset-089-asset.txt` | script | lib/dts.mjs: ts-morph extraction of <Name>Props structural types |
| 29,118 | 287 | `asset-113-Upgrading-the-anthropic-Python-SDK-0.x---1.x.md` | reference | Upgrading the anthropic Python SDK 0.x -> 1.x |
| 28,619 | 292 | `asset-059-asset.txt` | script | Claude Test environment report: per-file scan including symlinks and non-regular files |
| 28,236 | 847 | `asset-074-asset.txt` | skill support | CDS token block, carved byte-exact from the workshop-page template |
| 28,225 | 126 | `asset-083-design-sync.md` | skill | design-sync: convert and push a React design system to claude.ai/design |
| 27,892 | 204 | `asset-125-Eval-health-checklist.md` | reference | Eval health checklist |
| 27,847 | 282 | `asset-140-Managed-Agents---Self-Hosted-Sandboxes.md` | reference | Managed Agents - Self-Hosted Sandboxes |
| 27,340 | 271 | `asset-052-Onboarding-the-machine-first-then-the-starter-su.md` | reference | Claude Test onboarding: the machine first, then the starter suite, then the person |
| 26,203 | 260 | `asset-136-Managed-Agents---Multiagent-Sessions.md` | reference | Managed Agents - Multiagent Sessions |
| 25,497 | 328 | `asset-062-asset.txt` | script | Claude Test tool loading: read file, hash, dynamic import via pathToFileURL |
| 25,248 | 263 | `asset-056-asset.txt` | script | Claude Test run/port probe: ownPorts, answer JSON back to the page |
| 25,159 | 576 | `asset-049-asset.txt` | script | Built-in SDK of the AppifactRepl tool: runs stdin code once as a single async function, with claude.use(db/files/assets) |
| 25,041 | 290 | `asset-134-Managed-Agents---Events-Steering.md` | reference | Managed Agents - Events & Steering |
| 24,065 | 366 | `asset-161-whiteboard.md` | skill | whiteboard (live variant): everyone sees each other's strokes and cursors; this session stands on the board as a small figure |
| 23,240 | 417 | `asset-101-asset.md` | script | resync.mjs: the re-sync driver that emits one machine-readable verdict |
| 22,987 | 167 | `asset-129-Live-Documentation-Sources.md` | reference | Live Documentation Sources: live URLs for WebFetch |
| 22,604 | 651 | `asset-155-Tool-Use---TypeScript.md` | reference | Tool Use - TypeScript |
| 22,529 | 289 | `asset-065-asset.txt` | script | Claude Test tool install: installTools, toolsDir, lock file (inferred tools.mjs) |
| 22,228 | 296 | `asset-121-Anthropic-CLI-ant.md` | reference | Anthropic CLI (`ant`): every API resource as a shell subcommand |
| 20,946 | 88 | `asset-047-artifact-design.md` | skill | artifact-design: the design pass to load before writing any artifact |
| 20,442 | 566 | `asset-112-Claude-API---Python.md` | reference | Claude API - Python |
| 19,799 | 275 | `asset-123-HTTP-Error-Codes-Reference.md` | reference | HTTP error codes reference |
| 19,708 | 629 | `asset-115-Tool-Use---Python.md` | reference | Tool Use - Python |
| 19,332 | 365 | `asset-078-Cowork-Plugin-Authoring.md` | reference | Cowork plugin authoring: create a plugin from scratch or customize one per organization |
| 19,067 | 567 | `asset-107-Managed-Agents---Go.md` | reference | Managed Agents - Go |
| 19,002 | 210 | `asset-053-asset.md` | script | Claude Test script for sign-in/sign-out and credentials (logoutCmd/loadConfig; inferred ct-auth.mjs) |
| 18,900 | 363 | `asset-102-Claude-API---C.md` | reference | Claude API - C#: namespace reference and examples |
| 18,429 | 343 | `asset-091-asset.txt` | script | lib/source-storybook.mjs: parse storybook-static/index.json and pair story names to exports |
| 18,007 | 316 | `asset-080-asset.txt` | script | Categorical palette validator (JS twin of asset-081) |
| 17,026 | 446 | `asset-110-Managed-Agents---Java.md` | reference | Managed Agents - Java |
| 16,553 | 343 | `asset-168-run-skill-generator.md` | skill | run-skill-generator: author or improve the run-<unit> skill that tells agents how to build, launch and drive a project |
| 16,387 | 1 | `asset-068-asset.txt` | data | Frozen snapshot of the pinned @playwright/mcp client-visible tool list (single-line JSON) |
| 16,294 | 296 | `asset-096-asset.md` | script | preview-rebuild.mjs: fast single-component preview recompile (the inner loop) |
| 16,121 | 339 | `asset-128-Hillclimb-state-schema-v2.md` | reference | Hillclimb state schema v2: state.json field definitions |
| 15,993 | 149 | `asset-144-Claude-Model-Catalog.md` | reference | Claude Model Catalog: exact model IDs (incl. claude-opus-4-5/4-6/4-7, claude-haiku-4-5, claude-mythos-preview) |
| 15,869 | 247 | `asset-158-whiteboard.md` | skill | whiteboard (solo variant): a shared sketch canvas; the user draws and hits Publish, this session wakes, reads the board and draws back |
| 15,829 | 259 | `asset-092-asset.txt` | script | lib/story-imports.mjs: how story modules resolve at preview-compile time (designed to be forked) |
| 15,785 | 306 | `asset-081-thresholds.md` | reference | thresholds.md: thresholds and usage for palette validation (Python twin: validate_palette.py) |
| 15,723 | 257 | `asset-098-asset.md` | script | package-capture.mjs: the package shape has no reference render, so each preview is photographed alone |
| 15,710 | 406 | `asset-153-Claude-API---TypeScript.md` | reference | Claude API - TypeScript |
| 15,686 | 326 | `asset-088-asset.txt` | script | lib/bundle.mjs: esbuild to a window.<GLOBAL> IIFE plus the @ds-bundle header |
| 14,601 | 224 | `asset-055-asset.md` | script | Claude Test browser driver: wait-text / wait-gone and friends (inferred ctbrowser.mjs) |
| 14,341 | 357 | `asset-167-Example-Electron-desktop-GUI-app.md` | reference | Example: Electron / desktop GUI app: ship a driver script, not a note saying 'npm start opens a window' |
| 14,277 | 162 | `asset-066-asset.txt` | script | Claude Test guard: validates tool calls that would type a secret (namesSecret; inferred guard.mjs) |
| 14,065 | 164 | `asset-061-asset.txt` | script | Claude Test hosts handling: yamlScalar, resolver pin rules (inferred hosts.mjs) |
| 13,764 | 237 | `asset-100-asset.md` | script | lib/remote-diff.mjs: two-partition diff of a fresh local build vs the uploaded _ds_sync.json |
| 13,563 | 443 | `asset-111-Managed-Agents---PHP.md` | reference | Managed Agents - PHP |
| 13,548 | 85 | `asset-137-Managed-Agents---Onboarding-Flow.md` | reference | Managed Agents - Onboarding Flow |
| 13,432 | 284 | `asset-095-asset.txt` | script | lib/docs.mjs: component doc discovery and guidelines copy |
| 13,375 | 231 | `asset-069-Claude-Test-the-spec-author-background-nobody-is.md` | skill | Claude Test internal skill: drafts spec files in the background (user-invocable: false, context: fork; very long allowed/disallowed tool lists) |
| 13,341 | 76 | `asset-138-Managed-Agents---Overview.md` | reference | Managed Agents - Overview |
| 12,912 | 226 | `asset-133-Managed-Agents---Environments-Resources.md` | reference | Managed Agents - Environments & Resources |
| 12,688 | 166 | `asset-058-asset.txt` | script | Claude Test project discovery: infers the dev-server port (vite/next/astro) (inferred discover.mjs) |
| 12,308 | 267 | `asset-165-verify.md` | skill | verify: exercise the affected flow end-to-end before committing, asserting behaviour rather than tests/types |
| 12,123 | 180 | `asset-060-asset.txt` | script | Claude Test fence proxy: 16 KB header cap, net/tls forwarding (inferred fence-proxy.mjs) |
| 12,043 | 220 | `asset-131-Managed-Agents---Common-Client-Patterns.md` | reference | Managed Agents - Common Client Patterns |
| 12,029 | 218 | `asset-087-asset.txt` | script | lib/common.mjs: pure filesystem/string helpers |
| 11,950 | 239 | `asset-108-Claude-API---Java.md` | reference | Claude API - Java |
| 11,922 | 255 | `asset-114-Streaming---Python.md` | reference | Streaming - Python |
| 11,779 | 312 | `asset-073-asset.txt` | skill support | Decision-component styles, carved byte-exact from the workshop-page template |
| 11,626 | 203 | `asset-164-prototype.md` | skill | prototype: turn an idea into a clickable single-page artifact |
| 11,602 | 396 | `asset-077-Component-Schemas.md` | reference | Plugin component schema reference: where skills/agents/commands/hooks live and what fields they take |
| 11,602 | 179 | `asset-119-Admin-API-Organization-Management.md` | reference | Admin API (organization management) |
| 11,560 | 363 | `asset-116-Managed-Agents---Python.md` | reference | Managed Agents - Python |
| 11,362 | 201 | `asset-135-Managed-Agents---Memory-Stores.md` | reference | Managed Agents - Memory Stores (beta agent-memory-2026-07-22) |
| 11,321 | 143 | `asset-142-Managed-Agents---Webhooks.md` | reference | Managed Agents - Webhooks |
| 11,131 | 123 | `asset-145-Platform-Availability.md` | reference | Platform Availability: 1P / P-AWS / Bedrock / Vertex / Foundry feature matrix |
| 11,027 | 389 | `asset-156-Managed-Agents---TypeScript.md` | reference | Managed Agents - TypeScript |
| 10,892 | 247 | `asset-075-asset.md` | skill support | artifact-tool body fragment: data-table template (includes SLOT: TITLE) |
| 10,800 | 223 | `asset-099-asset.txt` | script | lib/sync-hashes.mjs: single source of truth for the hash recipes (_ds_sync.json / sourceKeys) |
| 10,559 | 211 | `asset-076-asset.md` | skill support | artifact-tool body fragment: report template |
| 10,494 | 394 | `asset-117-Managed-Agents---Ruby.md` | reference | Managed Agents - Ruby |
| 10,109 | 23 | `asset-042-Plugin-eval-and-skill-doctor---quick-reference.md` | reference | Quick reference for claude plugin eval and /skill-doctor (24 lines): availability, what it does, entry points |
| 9,696 | 257 | `asset-103-Claude-API---cURL-Raw-HTTP.md` | reference | Claude API - cURL / raw HTTP |
| 9,596 | 182 | `asset-094-asset.txt` | script | lib/previews.mjs: one preview .tsx per component |
| 9,508 | 221 | `asset-154-Streaming---TypeScript.md` | reference | Streaming - TypeScript |
| 9,489 | 228 | `asset-109-Tool-Use---Java.md` | reference | Tool Use - Java (annotated tools) |
| 9,068 | 156 | `asset-139-Managed-Agents---Scheduled-Deployments.md` | reference | Managed Agents - Scheduled Deployments |
| 9,024 | 193 | `asset-079-Reference-palette.md` | reference | Reference palette: the filled-in reference instance of the data-viz method (swap in your brand's values) |
| 8,814 | 48 | `asset-051-plugin-authoring.md` | skill | plugin-authoring: make a mod (pane/band/status line/toast/hook) that hot-reloads in this session |
| 8,736 | 101 | `asset-120-Agent-Design-Patterns.md` | reference | Agent Design Patterns |
| 8,653 | 369 | `asset-104-Managed-Agents---cURL-Raw-HTTP.md` | reference | Managed Agents - cURL / raw HTTP |
| 8,462 | 190 | `asset-105-Claude-API---Go.md` | reference | Claude API - Go |
| 8,432 | 162 | `asset-090-asset.txt` | script | lib/css.mjs: token-file copy, @font-face extraction, styles.css writer |
| 8,377 | 220 | `asset-106-Tool-Use---Go.md` | reference | Tool Use - Go |

## 3. Categories

### 3.1 Skills (the 14 files with `---` frontmatter)

| i | name | Lines | Bytes | description (first ~50 chars) | Found in the JS corpus? |
|---|---|---|---|---|---|
| 36 | `artifact-pr-review` | 689 | 42,525 | Create a PR review artifact - a structured review br... | yes (1 chunk) |
| 37 | `artifact-pr-review` | 501 | 31,080 | Create a PR review artifact - a structured review br... | yes (1 chunk) |
| 39 | `workshop` | 726 | 40,528 | Build a design together with the user, one decision ... | yes (1 chunk) |
| 47 | `artifact-design` | 89 | 20,946 | Design guidance and fundamentals for Artifacts.... | yes (1 chunk) |
| 51 | `plugin-authoring` | 49 | 8,814 | Make a mod: a live pane, band, status line, toast or... | yes (1 chunk) |
| 69 | `(no name:)` | 232 | 13,375 | Internal to Claude Test — drafts spec files in the b... | not found |
| 70 | `(no name:)` | 499 | 42,953 | Internal to Claude Test — runs the specs in a backgr... | not found |
| 71 | `(no name:)` | 502 | 59,098 | Check that the web app in this repo still works, wit... | not found |
| 83 | `design-sync` | 127 | 28,225 | Push a React design system to claude.ai/design. This... | yes (1 chunk) |
| 158 | `whiteboard` | 248 | 15,869 | Create a whiteboard artifact - a shared sketch canva... | yes (1 chunk) |
| 161 | `whiteboard` | 367 | 24,065 | Create a whiteboard artifact - a live sketch canvas ... | yes (1 chunk) |
| 164 | `prototype` | 204 | 11,626 | Turn an idea into a working proof of concept and pub... | yes (1 chunk) |
| 165 | `verify` | 268 | 12,308 | Verify that a code change actually does what it's su... | yes (1 chunk) |
| 168 | `run-skill-generator` | 344 | 16,553 | Author or improve the run-<unit> skill - a per-proje... | yes (1 chunk) |

**Relationship to the skill prompts already known from the JS corpus: the descriptions are duplicated, the bodies are unique.** First-hand evidence ([raw/chunks/c1171.js](raw/chunks/c1171.js)):

- Corpus skill registration carries metadata plus a loader that fetches the body at runtime, e.g. inside `getPromptForCommand`: `let{SKILL_MD:h}=await On(), g=Hs(h[e]).content.trimStart()` - the body is decompressed from `/$bunfs/root/SKILL-*.md.zst`;
- Four probes of 60-180 characters taken from the middle of each skill body return **0 hits in the corpus** (32 probes over asset-158/161/164/165/39/83/36/168), while the first 70 characters of each frontmatter `description` return **11 of 14 hits** (the three misses are the Claude Test internal skills 69/70/71, which are not in the c1171.js skill table);
- In other words, the skill text visible to the earlier corpus pass was only **registration metadata** (name/menuDescription/description/whenToUse/argumentHint/allowed-tools). The actual bodies (tens to hundreds of KB of SKILL.md) exist only in these compressed resources - the single biggest thing this extraction adds.
- Two skill-shaped documents have no frontmatter: asset-166 (Plugin eval, 514 lines) and asset-118 (Building LLM-Powered Applications, 596 lines) start with `#` and are likewise unique to the asset blob.

### 3.2 Reference documentation

- **66** reference files, the bulk of the Claude-side bytes. Only two exceed 100 KB: Model Migration Guide (317,800 B / 2254 lines; migration steps, per-SDK syntax, breaking changes, routed from `/claude-api migrate`) and Building LLM-Powered Applications with Claude (100,774 B / 596 lines; choose the surface first, and the body still carries `{{FABLE_NAME}}`/`{{OPUS_NAME}}` placeholders). Right behind them: the Plugin eval reference (80,310 B), Hill-Climbing on an Eval (69,156 B), Storybook source shape (69,242 B), Cost Optimization (58,092 B) and Building an Eval (55,191 B).
- Managed Agents family (**20** files = 13 same-titled docs + 7 language/binding docs): Overview / Core Concepts / Endpoint Reference / Environments & Resources / Tools & Skills / Events & Steering / Multiagent Sessions / Memory Stores (`agent-memory-2026-07-22` beta) / Scheduled Deployments / Self-Hosted Sandboxes / Webhooks / Common Client Patterns / Onboarding Flow, plus the cURL, Go, Java, PHP, Python, Ruby and TypeScript binding READMEs (see §5 on name mapping).
- Other title-level threads: `Claude API - *` 6 files (C#/Go/Java/Python/TypeScript/cURL), `Tool Use *` 5 files (concepts + 4 languages), `Streaming *` 2 files (Python/TypeScript), `Example: *` 1 file (Electron).
- Eval and cost cluster (8 files): Building an Eval (55 KB), Eval health checklist (27.9 KB), Hill-Climbing on an Eval (69.2 KB), Hillclimb state schema v2 (16.1 KB), Cost Optimization (58.1 KB), Cost-reduction search (31.7 KB), Prompt Audit (48.9 KB), Prompt Caching (33.0 KB).
- Migration and compatibility: Model Migration Guide (317.8 KB), the two Preserved Thinking docs (64.0 KB + 39.7 KB) plus two runnable probes (`prefix_diff.py`, 94 KB; `drop_block_probe.py`, 66.6 KB), and Upgrading the anthropic Python SDK 0.x -> 1.x (29.1 KB).
- Metadata files: Claude Model Catalog (16.0 KB, 150 lines; exact model IDs such as `claude-opus-4-5`/`4-6`/`4-7`, `claude-haiku-4-5`, `claude-mythos-preview`), Platform Availability (11.1 KB; the 1P/P-AWS/Bedrock/Vertex/Foundry matrix), Live Documentation Sources (23.0 KB), HTTP Error Codes (19.8 KB), Admin API (11.6 KB), Anthropic CLI `ant` (22.2 KB), Agent Design Patterns (8.7 KB), Tool Use Concepts (44.2 KB).

### 3.3 Front-end / HTML resources

| i | Bytes | Lines | Feature string | What it is |
|---|---|---|---|---|
| 157 | 96,305 | 1770 | `<title><!-- SLOT: TITLE -` | self-contained HTML template with slots (inferred artifact/plan template; body not read in full) |
| 159 | 154,540 | 2711 | `<title>Whiteboard</title>` + Google Fonts links | page template of the whiteboard variant that ships `board.mjs` |
| 162 | 329,237 | 4555 | `<title>Whiteboard</title>` + `@ant/cds` token sheet | page template of the whiteboard variant that ships `merge-state.mjs` |
| 40 | 117,526 | 2963 | `name: workshop` (frontmatter in an HTML comment) | workshop artifact template with the four fill slots |
| 41 | 127,802 | 3095 | `name: workshop-page` | direct-HTML workshop template plus publish-time structural rules |
| 46 | 38,063 | 1088 | `name: plan` | plan artifact template (PLAN_TEMPLATE) |
| 38 | 88,532 | 1749 | `Artifact-tool body fragment` | PR-review body fragment (no doctype wrapper) |
| 75 | 10,892 | 248 | `<!-- SLOT: TITLE -->Data table` | artifact body fragment: data table |
| 76 | 10,559 | 212 | `<!-- SLOT: TITLE -->Report` | artifact body fragment: report |

Matching scripts and styles (also unique to the blob): asset-072 (workshop decisions script, 65.6 KB / 1548 lines), asset-073 (decision-component styles, 11.8 KB), asset-074 (CDS token block, 28.2 KB).

### 3.4 Vendored third-party libraries

| i | Bytes | Library | Version | Source / license evidence (first lines) | Name inside the binary |
|---|---|---|---|---|---|
| 48 | 3,566,058 | mermaid | 11.16.1 | banner prepended by the loader: `/*! mermaid v11.16.1 · MIT · Copyright (c) 2014 - 2022 Knut Sveidqvist */`; the bundle also carries DOMPurify 3.4.0 (Apache-2.0 + MPL-2.0) and lodash (MIT) notices | `/$bunfs/root/mermaid.min.js` |
| 35 | 593,163 | highlight.js | 11.11.1 | first line says it is generated by `scripts/generate-hljs-browser-bundle.ts`; `BSD 3-Clause License, Copyright (c) 2006, Ivan Sagalaev`; 186 grammars | `/$bunfs/root/hljsBundle.generated.min.js` |
| 63 | 167,048 | public suffix list | 2026-09-08 | single-line JSON: `{"source":"https://publicsuffix.org/list/public_suffix_list.dat","license":"MPL-2.0","version":"2026-09-08_12-18-37_UTC"...}` | `/$bunfs/root/psl-data.json-ffeefa5c.txt.zst` |
| 34 | 208,522 | Chart.js | 4.5.1 | banner: `Chart.js v4.5.1 ... (c) 2025 Chart.js Contributors ... Released under the MIT License` | `/$bunfs/root/chart.umd.min.js` |

All four are **unmodified upstream bundles** (banners and license notices kept). Their purpose is visible from the loaders: `loadMermaidBundleJs` / `loadHljsBundleJs` / `loadChartBundleJs` pull them in on demand for artifact rendering, and the PSL feeds the Claude Test fence proxy's host classification. This build vendors no ESLint or other linter on the Claude side (grepping `eslint` across the assets only hits the Bun-side package-name table and polyfills, asset-008/013).

### 3.5 Type declarations and test infrastructure

- **asset-044 (573,702 B / 14,915 lines) = `claude-code.d.ts`**, the full TypeScript declarations of the function-hooks plugin API (its own header says EARLY ACCESS and that the engine writes it as `<mod>/.claude-plugin/types/claude-code/index.d.ts`). That topic is **already analysed by [REPORT-plugin-api.md](verify/REPORT-plugin-api.md) (450 lines)** (worker sandbox, 136 hook points, 10 built-in plugins), so this report only cross-references it; the sibling assets are asset-045 (the `plugin test` suite), asset-050 (long form, 145 lines) and asset-051 (plugin-authoring skill, 49 lines).
- Test infrastructure: the whole Claude Test plugin (**16** extracted files match by content: 52,53,54,55,56,57,59,62,64,65,66,67,69,70,71,91 - 3 skills plus CLI/browser/config/discover/guard/hosts/proxy scripts and `spec-format`), and the whole design-sync converter (**17**: 82-88,90,92,93,94,96,97,98,99,100,101; the loader declares 24 `SKILL_FILES` entries, the rest did not land on disk).

### 3.6 Plugin runtime families (quick map)

Membership rule: keyword hit inside the file's text, so one file can belong to two families (040/041 are workshop templates that also mention whiteboards).
- whiteboard (9: 40,41,72,158,159,160,161,162,163): two variants of three files each - SKILL.md + template.html + helper (`board.mjs` / `merge-state.mjs`);
- workshop / plan (8: 39,40,41,46,72,73,74,162): templates + decisions script + styles/tokens;
- design-sync (17: 82-88,90,92,93,94,96,97,98,99,100,101): skill + converter scripts + two source-shape docs + the `Where things are` map;
- Claude Test (16: see §3.5);
- plugin eval / skill-doctor (2: 42,166): quick reference + the 514-line reference;
- function hooks (3: 44,50,51): the .d.ts + the long form + the skill.

These families are packed together as plugins inside the binary (the frame order lines up with each loader's `SKILL_FILES` object), which is what lets you tell which resources ship with the same plugin.

## 4. Corrections to earlier conclusions

- [README.md:312](README.md#L312) said "**231 non-chunk resources (`SKILL-*.md[.zst]` and the like) were not extracted one by one**". Today: **all 169 zstd frames were attempted and all 135 Claude-side frames decompressed and landed on disk** (9.91 MB).
- The "231" order of magnitude reproduces but does not align exactly: rescanning the name table with `/$bunfs/root/[A-Za-z0-9._@+-]+` yields **229-230** non-chunk entries (the count depends on where the final byte is cut; the strings are not NUL-terminated in the table but run into the next entry) and ~2169 chunk entries. Which one or two entries differ from 231 is **not determined**.
- Coverage should therefore be stated as: **of roughly 230 non-chunk names in the Claude-side table, 135 (about 59%) are now on disk as zstd frames**. The remainder is not "missing" but falls into three buckets: (a) siblings stored uncompressed - measured in the inter-frame gaps: two WOFF2 fonts, `audio-capture.node` (444 KB Mach-O), at least six further Mach-O slices, at least four design/slides prompt docs and a 10 KB autonomous-loop prompt, 4,721,613 bytes in total, **none of which were written to disk this round**; (b) install-layout names (hashes-free names such as `/$bunfs/root/template.html` or `board.mjs` are the same content as a hashed `.zst` blob, written twice); (c) resources that are not text at all (`.node`, `.woff2`, `.ts`, `.tsx`).
- Another intuition to correct: **the `.zst` suffix is not a compression test**. Only 80 non-chunk names end in `.zst`, yet there are 135 Claude-side frames; `mermaid.min.js`, `chart.umd.min.js` and `hljsBundle.generated.min.js` have no `.zst` and are still zstd frames.
- Earlier notes placed the name table "around 0xd87e9b0"; measurement shows that offset is only the **tail** of the table (from `/$bunfs/root/drop_block_probe-...` to `template-eg8004mh.md`). The table starts at `0xd85b83d`, ends at `0xd87eac9`, and its first half is entirely chunk names.

## 5. Unverified / could not be read

- **One frame fails to decompress** (index 33, Bun region); see §1.3. Whether it is a real resource or a magic-byte false positive is **unverified** in this round; a zstd decode with the right dictionary or Bun's asset-manifest format would settle it.
- **Name-to-content mapping is not exact.** We clustered by offset rather than mapping through the name table. Only 11 pairs are confirmed:
  - six whiteboard files (first-hand evidence: the in-binary loader sources of `chunk-zqxb1n4f.js` / `chunk-4atxqh9y.js` and `Et()==="live"?Dn():Mn()` in [raw/chunks/c1171.js](raw/chunks/c1171.js)) - `SKILL-7f2555bf.md.zst` + `template.html-af756034.txt.zst` + `board.mjs-0bf8864f.txt.zst` are asset-158/159/160 (solo; the helper calls itself `board.mjs`), and `SKILL-8e6c8b5d.md.zst` + `template.html-94ff54c0.txt.zst` + `merge-state.mjs-49ddf23e.txt.zst` are asset-161/162/163 (live; the helper is referenced as `merge-state.mjs`);
  - five library/typings files (mermaid, highlight.js, Chart.js, PSL, `claude-code.d.ts`) matched by in-file banners or by the loader's own variable names, see §3.4 and §3.5.
- **The other ~124 frames only get an interval, not a name.** The verifiable regularity is a monotone "name order = frame order" relation: with 16 anchors identifiable by content (chart/hljs/plugin-eval-quickref/claude-code.d.ts/mermaid/PSL/cost-optimization/build-eval/eval-hillclimb/model-migration/preserved-thinking/the four whiteboard files/plugin-eval), the difference between name-table index and frame index drifts monotonically from -33 to +52 - the two sequences are in the same order but hold different numbers of entries (more names than frames). A strict 1:1 alignment therefore passes only 80/135 (59%) of type spot-checks and must not be used as a mapping.
- **Not read closely**: asset-045 (the concatenated plugin-test suite source; only head and tail read), asset-157 (96 KB template; only the header slots read), asset-072 (1548-line decisions script), asset-093 (683-line design-sync map) and others. Table summaries cover the opening lines only, not full-text semantics.
- **The Claude Test script-to-filename assignment is inference** (the 7 rows in §2 marked "inferred X.mjs"): it rests on content features (`logoutCmd`, `ownPorts`, `installTools`, `parseSkillMd`, `namesSecret`, `RC_FILE`, the `vite|next|astro` port heuristic) plus the 27 filenames the loader lists; hashes were not matched one by one.
- **The 33 Bun-region resources were only identified at first-line level** (error-page CSS, polyfills, completions, package-name table); upstream provenance and versions were not confirmed individually.
- Table entries such as `sourcemap.json` produced by my regex (`sourcemap.js` followed by adjacent bytes) are artifacts of the scan, not separate resources, and are not used in the body.

## Appendix A: checkable commands and feature strings

- Frame count: `python3 -c "import re;d=open('/Users/yezhipeng/.local/share/claude/versions/2.1.287','rb').read();print(len(re.findall(rb'\x28\xb5\x2f\xfd',d)))"` -> `169`
- Name table: `0xd85b83d`-`0xd87eac9`; the non-chunk section starts after the last `chunk-` name (on this machine that boundary sits just before `0xd87e5b0`)
- Feature strings: `claude-opus-4-7` (asset-144), `{{FABLE_NAME}}` (asset-118), `name: workshop-page` (asset-041), `EARLY ACCESS` (asset-044), `agent-memory-2026-07-22` (asset-135), `wOF2` (the font gap after frame k=7), `@rpath/audio-capture.node` (the 444 KB gap after frame k=10)
- Whiteboard mapping: `grep -ao 'var [A-Za-z]*="/\$bunfs/root/SKILL-[0-9a-z]*\.md\.zst"' binary` reproduces it; `chunk-zqxb1n4f.js` = solo, `chunk-4atxqh9y.js` = live

## Appendix B: how claims are labelled

- First-hand: file contents, binary offsets and bytes, loader source, the `zstd` CLI experiment;
- Inferred: the region threshold, family membership, Claude Test script roles, the purpose of asset-157/045;
- Not found: any vendored ESLint copy on the Claude side; `verify/REPORT-plugin-api.md` (does not exist, hence §3.5 is a first-hand summary); the true identity of the failed frame.

