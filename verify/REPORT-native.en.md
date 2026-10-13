> English version. 中文原版：[REPORT-native.md](REPORT-native.md)

# Step 4 · Hard-core layer: bytecode-region completeness and the native layer

> Object: `~/.local/share/claude/versions/2.1.287` (Mach-O arm64, 227,827,120 bytes)
> Tooling: `otool`, `file` (system-provided), `zstd` (/opt/homebrew/bin/zstd), `raw/carve_modules.py`

## 1. Conclusions at a glance

1. The structure of the whole file is now pinned down: **`__TEXT`(0–66.6 MB) + `__DATA_CONST` + `__DATA` + `__BUN`(68.2–227.2 MB, 159 MB) + `__LINKEDIT`**. All JS/bytecode/embedded native libraries live in the single section **`__BUN,__bun`**.
2. Inside `__BUN` there are three regions: **bytecode/string-table region (68.2–177.8 MB) → JS module source region (177.8–219.0 MB, 41.6 MB) → embedded native library region (219.0–227.2 MB, 8.4 MB)**.
3. **The prompts have no copy that "exists only in bytecode"**: the string table in the bytecode region and the prompts in the source region are the same batch of text, and every prompt string sampled can be found in the source corpus. The earlier "43,607 entries not found in the source" was a false gap caused by runtime strings (Bun/Rust/JSC internals) plus escaping differences.
4. The trailing 8.4 MB is **not JS bytecode but native dynamic libraries embedded in the file**, among them:
   - `@rpath/libComputerUseSwift.dylib` (**two copies, x86_64 + ARM64, Swift**)
   - `libcomputer_use_input.dylib` (**Rust**, leaking a build path `/Users/runner/work/apps/apps/packages/desktop/computer-use-input/target/{x86_64,aarch64}-apple-darwin/release/deps/`)
   - `@rpath/audio-capture.node` (Node native addon)
5. Besides the JS modules there are also **231 non-chunk bunfs resources** (`SKILL-*.md[.zst]`, `README-*`, `SCHEMA-*`, `NOTICE-*`, of which 132 are `.zst`). This part was **not extracted one by one** (see the not-yet-done items in §5).

## 2. Mach-O segments

```
__PAGEZERO    vmaddr 0x0            filesize 0
__TEXT        vmaddr 0x100000000    fileoff        0  filesize  66,633,728
__DATA_CONST  vmaddr 0x103f8c000    fileoff 66,633,728  filesize   1,425,408
__DATA        vmaddr 0x1040e8000    fileoff 68,059,136  filesize     147,456
__BUN         vmaddr 0x1042dc000    fileoff 68,206,592  filesize 158,957,568   ← all embedded content
__LINKEDIT    vmaddr 0x10da74000    fileoff 227,164,160 filesize     662,960
```

`__BUN` holds exactly one section, `__bun` (size 158,949,736) — Bun's `--compile` stuffs the module graph, sources, resources and embedded libraries into this single section.

## 3. Bytecode-region completeness check (step 4a)

Method: extract every printable string of ≥24 characters from the non-source regions (68.2–177.8 MB and 219.0–227.2 MB of `__BUN`), filter them down to "sentence-like" candidates, and look each one up across the 2,174 module sources.

| Measure | Count |
|---|---|
| Printable strings (≥24) in the non-source region | 163,486 |
| Of which "sentence-like" candidates | 77,098 |
| Not found in the source corpus | 43,607 (56.6%) |
| Still not found after the "prompt-smelling" filter | 2,737 |
| Confirmed by manual sampling to be a Claude Code prompt yet genuinely absent from the source | **0** |

The sampling process (`verify/bytecode-gap-check` plus two rounds of manual review):

- The overwhelming majority of the 43,607 are strings from the **Bun / Rust / JavaScriptCore runtimes** (`wtf8`, `RobinHoodHashTable`, `assertion failed`, bash completions, error-page CSS, word-list data, ...), which were never Claude Code's to begin with.
- The few entries that looked like "Claude Code prompts" (such as `When a finished piece of work is meant for other people or agents…`, `Why Claude Code refused to start…`, `Those prefixes match byte for byte…`) **can all be found in the source corpus** (`raw/chunks2/`) — the first round judged them as gaps because the bytecode string table stores the **decoded whole string**, whereas the source holds an escaped/concatenated form, so the comparison criteria differed.
- Conclusion: **the source region is the complete source of prompts**; the bytecode region contains no prompts of its own. This also explains why the UTF-16 copies caught by `strings` (73–80 MB) correspond one-to-one with the source.

## 4. The embedded native libraries (step 4b)

Scanning the trailing 8,374,397 bytes of `__BUN` (starting at file offset **219,452,723**) for Mach-O magic numbers turned up 7 Mach-O headers (2 of them spurious hits):

| Offset within blob | Arch | Type | Install name / origin |
|---|---|---|---|
| `0x000fd4` | x86_64 | DYLIB | `@rpath/libComputerUseSwift.dylib` (contains Swift sections such as `__swift5_typeref`, `__constg_swiftt`) |
| `0x137fd4` | ARM64 | DYLIB | `@rpath/libComputerUseSwift.dylib` (the arm64 build of the same library) |
| `0x26532d` | x86_64 | DYLIB | `/Users/runner/work/apps/apps/packages/desktop/computer-use-input/target/x86_64-apple-darwin/release/deps/libcomputer_use_input.dylib` |
| `0x33032d` | ARM64 | DYLIB | As above, the `aarch64-apple-darwin` build |
| `0x429630` | ARM64 | DYLIB | Depends on `@rpath/audio-capture.node`, `/usr/lib/libobjc.A.dylib` |

Implication (inferred, from the first-hand paths and section names above): **"computer use" is not a pure-JS implementation**; the JS side (`mcp__cua__*` / the screen-control tools) calls into a set of native libraries: an input-injection library written in Rust plus a Swift wrapper, and separately an N-API addon for audio capture. The build paths show they come from Anthropic's monorepo (`apps/packages/desktop/computer-use-input`) and were packed into the single-file artifact.

> This also explains why the `ComputerUse`-related capabilities in the tool lists of documents 03/06 do not show up among the JS modules: **the implementation is not on the JS side**.

## 5. Not yet done / not verified

1. **The 231 non-chunk resources were not extracted one by one**. Their path table is confirmed to exist (`/$bunfs/root/SKILL-*.md[.zst]`, `README-*`, `SCHEMA-*`, `NOTICE-*`, 132 `.zst`), and `zstd -d` was tried against all 169 zstd frames in the file: 25 frames decompressed successfully, but their contents are all **things belonging to the Bun runtime itself** (error-page CSS, bash completions, Bun's JS shim), and no Claude Code SKILL resource came out — which means these resources are framed in a way that does not match my "magic number to next magic number" slicing assumption, and they need to be located one by one via the bunfs file table.
   - Limited impact: the several known skill/prompt bodies (`# Skillify`, `# Claude Code Doctor`, `# Workflow authoring reference`, `# Dream`) **all have verbatim copies among the JS modules** (see 08), so prompt coverage is unaffected.
2. `HOOKS_WORKER_URL` points at `/$bunfs/root/src/plugins/functionHooks/hooks-worker/hooks-worker.js`, but that file is neither among the 2,174 modules nor recovered from the resource region — **its implementation has still not been read** (consistent with the conclusion in 06).
3. The bytecode itself was **not decompiled**. There is no public decompiler for JSC bytecode; this step only performed the "completeness check" (proving the source region is complete) and did not turn the bytecode back into readable IR. If that were genuinely needed, only instruction-level statistics would be possible (for example a per-frame opcode histogram), which offers no incremental value on prompts / multi-agent topics.
4. 2 of the 7 Mach-O headers are magic numbers that merely happen to occur in the data (they parse to an absurd `ncmds=1036213520`) and have been discarded; whether the embedded libraries still contain unidentified smaller components (such as the body of `audio-capture.node`) was **not broken down further**.

## 6. Reproducing

```bash
# Segments and sections
otool -l ~/.local/share/claude/versions/2.1.287

# Carve out the trailing blob (after the last module body)
python3 raw/carve_modules.py          # generates modules.json (with end / binary_tail metadata for 2173)
python3 - <<'PY'
import json
m=[x for x in json.load(open("raw/modules.json")) if x["idx"]==2173][0]
d=open("~/.local/share/claude/versions/2.1.287","rb").read()
open("work/tail-blob.bin","wb").write(d[m["binary_tail"]["abs_start"]:])
PY

# Completeness check
python3 verify/bytecode_gap_check.py

# Embedded native libraries
python3 - <<'PY'
import re, struct
blob=open("work/tail-blob.bin","rb").read()
for i,o in enumerate([m.start() for m in re.finditer(rb"\xcf\xfa\xed\xfe", blob)]):
    cpu,sub,ft,ncmds,sz = struct.unpack_from("<iiIII", blob, o+4)
    open(f"work/embedded/macho{i}.bin","wb").write(blob[o:o+3_000_000])
PY
file work/embedded/*.bin && otool -D work/embedded/macho0.bin
```

## 7. Permission gate and sandbox: how the native side actually looks (addendum)

What `codesign` and string scanning give us:

```
Identifier=com.anthropic.claude-code     TeamIdentifier=Q6L2SF6YDW     Format=Mach-O thin (arm64)
flags=0x10000(runtime)                    Timestamp=2 Oct 2026 at 2:11:41 am
entitlements: com.apple.security.automation.apple-events,
              com.apple.security.cs.allow-jit,
              com.apple.security.cs.allow-unsigned-executable-memory,
              com.apple.security.cs.disable-library-validation,
              com.apple.security.device.audio-input
```

Key points:

- **The CLI itself has no macOS App Sandbox entitlement** (no `com.apple.security.app-sandbox`); instead it carries the hardened runtime + JIT allowance + Apple Events automation allowance + microphone allowance. That is, the "permission gate" is **implemented by the application layer itself**, not enforced by the operating system.
- Operating-system-level isolation is **invoked by the CLI on its own initiative**: the binary contains `sandbox-exec`(3), `sandbox_init`(15), `seatbelt`(2), `(version 1)`(4), `allow file-read`(9), `deny network`(2) — i.e. on macOS it launches child processes with a seatbelt profile; on the Linux side the counterparts are `bwrap`(64) and `seccomp`(96).
- Only together with the conclusion in document 06 does this become complete: **the JS side decides "whether to ask the user", the native/system side decides "what can be touched once it is running"** — the two layers are independent implementations; the former can be rewritten by flags/settings, the latter is a process boundary.

> Addendum (already done within this step): **the sandbox profile is not assembled by native code but on the JS side** — `PV()` in `raw/chunks2/0205__chunk-5vadtxaa.js` directly constructs the seatbelt profile string array (`(version 1)` + `(deny default (with message …))` + the Mach IPC allowlist + the optional trustd/apple-events + the file-read/file-write rules generated by `_a()`/`RV()`/`kV()`), which `sandbox-exec` then uses to launch the child process. The verbatim fragments are in [`seatbelt-profile.en.md`](seatbelt-profile.en.md) (37 entries). Still not done: fully reconstructing the **default allow set** of the file-read/file-write rules (which requires understanding the three assembly functions `_a`/`RV`/`kV`), and the corresponding `bwrap`/`seccomp` code on the Linux side.
