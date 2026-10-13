> English version. 中文原版：[REPORT-ghidra.md](REPORT-ghidra.md)

# Appendix: decompiling Claude Code's native layer with Ghidra (2026-10-14)

> The short version first: **Ghidra works, and this time it genuinely dug something up — but what it decompiles is the "embedded native libraries", not the JS and not the JSC bytecode.**
> Object: the three native libraries embedded in the tail of the `__BUN` segment of Claude Code v2.1.287.

## 1. Installation and configuration (the actual steps on this machine)

```bash
brew install ghidra          # 12.1.4 (formula), pulls in the openjdk@21 21.0.12.1 dependency automatically
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
GH=/opt/homebrew/Cellar/ghidra/12.1.4/libexec/support/analyzeHeadless
```

Two pitfalls:

1. `brew install ghidra` writes to `/opt/homebrew` and `~/Library/Caches/Homebrew`, both outside this session's workspace — the file permissions had to be relaxed the first time in order to install it.
2. Every time Ghidra starts it wants to write `~/Library/ghidra/ghidra_<ver>_PUBLIC` (the JAVA_HOME cache), which is also blocked. The fix is to redirect the user settings directory into the workspace: in `libexec/support/launch.properties`, change
   `#VMARGS=-Dapplication.settingsdir=` to
   `VMARGS=-Dapplication.settingsdir=<repo>/ghidra-cfg`
   (**Note**: this is a file inside the keg; `brew upgrade ghidra` will overwrite it, so it must be redone after an upgrade.)

The decompilation script: [`ghidra-scripts/DumpDecomp.java`](../ghidra-scripts/DumpDecomp.java) — walks the functions, calls `DecompInterface` to emit C, and supports name filtering (`-` means all).

```bash
"$GH" ghidra-proj cua -import work/embedded/macho1.bin \
      -postScript DumpDecomp.java "-" out/cua-all.txt -scriptPath ghidra-scripts
```

## 2. Scale of the decompilation results

| Library | Corresponding file | Functions | Decompiled successfully | Output |
|---|---|---|---|---|
| `libComputerUseSwift.dylib` (arm64) | `work/embedded/macho1.bin` | 2,817 | 2,817 | 4.3 MB C |
| `libcomputer_use_input.dylib` (arm64) | `work/embedded/macho5.bin` | 1,821 | 1,819 | 4.0 MB C |
| `audio-capture.node` (arm64) | `work/embedded/macho6.bin` | 579 | **579** | 2.1 MB C |

> Addendum (2026-10-14): the 3 functions that previously failed (2 in input, 1 in audio) were reporting a **decompile timeout**; after relaxing the per-function budget from 90 s to 400 s they **all succeeded** — that is, 5,217/5,217 decompiled in full. All 3 are unnamed runtime functions (`FUN_*`, with type-propagation warnings) and add nothing to the product conclusions.

Ghidra 12 has built-in **Swift name recovery** (the analysis log even shows `Swift Type Metadata Analyzer`), so those 2,817 Swift function names are readable (things like `ComputerUseSwift.AXDispatch.typeText(in:)`) — its single biggest advantage over `nm`/r2.

## 3. Finding A: `libComputerUseSwift` = the **accessibility (AX) layer**

The entire capability surface can be read straight off the recovered symbols:

```
ComputerUseSwift.AXDispatch.{keyCombo, typeText, deleteAtCaret}(in:)
ComputerUseSwift.AXDispatch.{Intent, Button, TypeMode, Outcome, ReasonCode, Result(Codable)}
ComputerUseSwift.AXElementAtPoint.Hit         ascendToTextual / ascendToPressable / ascendToSelectable
ComputerUseSwift.AXMenu.{Outcome, ReasonCode, Result}
ComputerUseSwift.AXWindow.{list, Info, OverlappingPanel}
ComputerUseSwift.AXSummary.Node
ComputerUseSwift.ScreenshotForComputerUse.{captureImage, computeExcludedApps}
ComputerUseSwift.CaptureWindow.capture
ComputerUseSwift.PhantomCursor.{show, hide, reorderAllAboveTargets}
ComputerUseSwift.CollisionWatch.{watch, unwatch}
ComputerUseSwift.WindowCover.{hide, show}
ComputerUseSwift.InstalledAppsCache.list / InstalledApp(WithRunning)
ComputerUseSwift.chicago{Register, Unregister, NotifyExpected}EscapeMethod_
```

Density of system API references: `AXUIElement` 449 occurrences, `CGImage` 146, `CGWindowList` 32, `NSWorkspace` 32, `CGEvent` 25, `ScreenCaptureKit` 5, `osascript` 0, `IOHIDPostEvent` 0.

**The design this reveals** (not just an API list):

- **Operations go through the accessibility tree, not coordinate clicks**: `AXDispatch` first "ascends" from the element to find a clickable/editable/selectable ancestor (`ascendToPressable/Textual/Selectable`), and also has to handle "a sheet from the same process overlapping it" (`enclosingSameProcessSheet`). This is meant to sidestep the failures of coordinate clicking on popups/overlays.
- **Structured results**: `Outcome` / `ReasonCode` / `Result: Codable` — the native side encodes "success/invalid/unsupported + reason code" back to JS instead of throwing exceptions.
- **Human-agent conflict has dedicated machinery**: `CollisionWatch.watch/unwatch` (detects whether the user has intervened or taken over the operation), `WindowCover.hide/show` (covers the target window while operating).
- **There is a "phantom cursor"**: `PhantomCursor.show/hide/reorderAllAboveTargets` — used to show the user where the agent is clicking, without actually moving the system pointer.
- **Screenshots come with an exclusion list**: `ScreenshotForComputerUse.computeExcludedApps` — computes which apps must not end up in the frame before capturing.
- **`chicago*EscapeMethod`**: a set of symbols that register/unregister an "escape hatch" (the name looks like an internal codename), presumably to let the user interrupt the agent mid-operation.

## 4. Finding B: `libcomputer_use_input` = **low-level input injection (CGEvent)**

A cdylib written in Rust (build path `/Users/runner/work/apps/apps/packages/desktop/computer-use-input/target/{x86_64,aarch64}-apple-darwin/release/deps/`). System API references in the decompiled output: `CGEventCreate` 16, `CGEventPost` 12, `CGEventSetFlags` 12, `CGEventKeyboardSetUnicodeString` 4, `NSEvent` 7; the symbols include `MouseEvent` / `KeyboardEvent` / `ScrollWheelEvent` / `KeyboardLayoutInputSource` / `KeyTranslate`.

**The division of labour is clear**: the Swift library is responsible for "finding the element to operate on, deciding whether it can be operated on, and explaining the result clearly"; the Rust library is responsible for "actually sending out the keyboard/mouse events", handling keyboard layouts and Unicode text input (`CGEventKeyboardSetUnicodeString` sidesteps layout differences).

## 5. Finding C: `audio-capture.node` = CoreAudio

`_napi_register_module_v1` is present (a Node-API addon); `AudioUnit` 26 occurrences, `AudioObject` 23, and **no** `ScreenCaptureKit`/`CATapDescription`. That is: recording goes through CoreAudio (AudioUnit/HAL), not the screen-recording APIs.

The JS side (`raw/chunks2/2127__x-isNativeAudioAvailable.js`) loads it by the path `./vendor/audio-capture/<arch>-<platform>/audio-capture.node`, which means it is an addon **vendored per platform/architecture** — the copy inside the Bun single-file artifact is the one for macOS arm64.

## 6. The JS ↔ native interface surface (matching across layers)

On the JS side (`raw/chunks2/0788__chunk-c8t4wb5r.js` around @69006), immediately after reading the AX operation result it calls `setPhantomCursor(screenPt.x, screenPt.y, windowId, isClick)`, and splices the native `outcome` / `reasonCode` / `axError` / `descentPath` (the element ancestor chain, collapsed per role into `Role×N`) into the observation text handed to the model.

In other words, the chain is:

```
JS decides "where to click" → the native AX layer executes and returns a structured result → JS draws the phantom cursor + writes the role/ancestor chain into the context for the model to see
```

**This answers the question in document 03 about "the computer-use tools have no visible implementation on the JS side"**: the implementation is in these three native libraries.

## 7. The complete answer to "can Ghidra be used for decompilation"

| Layer | Conclusion |
|---|---|
| JS source (`__BUN` 41.6 MB) | Already plaintext, no decompilation needed; Ghidra is actually worse at it |
| JSC bytecode (68–178 MB) | **Ghidra cannot do it** — there is no processor/loader for JavaScriptCore bytecode, the format changes with the JSC version, and there is no stable public specification. The only way to force it is to write your own loader |
| Native code (`__TEXT` 66 MB + embedded libraries 8.4 MB) | **Yes, and effectively so** — every finding in this document comes from here |

Addendum: running Ghidra over the **main binary** is not worth it — the 159 MB `__BUN` segment is all data, so only `__TEXT` should be analysed; and that part is mostly the Bun runtime (Zig/C++), which adds nothing on "prompt / multi-agent design". **The three embedded libraries are the ones genuinely worth decompiling**: they are small, they have symbols, and they map directly onto product capabilities.

## 8. Not done / not verified

- Only **static decompilation** was performed: no dynamic verification (computer-use was never run, and these libraries were never hooked).
- The **semantics of `chicago*EscapeMethod` and `CollisionWatch` are inferred** (from symbol names and call relationships); the full implementations were not read.
- The **x86_64 builds** of the three libraries (`macho0` / `macho2`) were not analysed separately; only arm64 was looked at.
- The main binary's `__TEXT` segment was **not analysed** (Bun runtime), and the default allow set of the sandbox profile's file-read/write rules has still not been reconstructed.
- The artifacts are decompiled text (`out/*.txt`, roughly 10 MB of C code in total); no function-by-function review was done, only a summary of the symbol surface and system APIs.

## 9. Reproducing

```bash
cd <repo>
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
GH=/opt/homebrew/Cellar/ghidra/12.1.4/libexec/support/analyzeHeadless
for pair in "cua macho1" "input macho5" "audio macho6"; do
  set -- $pair
  "$GH" ghidra-proj $1 -import work/embedded/$2.bin \
        -postScript DumpDecomp.java "-" out/$1-all.txt -scriptPath ghidra-scripts
done
grep "^// ====" out/cua-all.txt | head        # function list (Swift names recovered)
```

## 10. Addendum: `chicago*` — the family name of the computer-use native API

Searching the binary for the `chicago` prefix shows that it is an entire family of **native method names exposed by ObjC to JS** (not an internal codename but real API names):

```
chicagoCaptureRegion         chicagoCaptureExcluding        chicagoPrepareDisplay
chicagoResolvePrepareCapture chicagoListInstalled           chicagoListInstalledWithRunning
chicago-hide / chicago-open (a pair of strings inside a Swift closure)
```

Strings in the same region reveal the implementation details:

- It goes through **ScreenCaptureKit**: `ScreenCaptureKit requires macOS 14.0`, `Region capture returned nil (permission missing or SCContentFilter failure)`
- Screenshots are returned as a **JPEG base64 data URL**: `data:image/jpeg;base64,`
- The parameter contract is written into the error text: `captureRegion: expected (allowedBundleIds, regionX, regionY, regionW, regionH, outputWidth, outputHeight)`, `resolveBundleIds: expected names: string[]`
- `com.apple.finder` is exempted by default; a missing permission has its own text, `Screen Recording permission not granted`

In other words: beyond `PhantomCursor` / `AXDispatch` / `CollisionWatch` there is another layer of **interfaces aimed at "looking at the screen"** (region capture, excluding given apps, display preparation, installed-app listing), and "which apps should be kept out of the frame" is made into a parameter.

> Still not verified: the correspondence between these methods and their call sites on the JS side (the same strings cannot be found in the JS corpus, which suggests they are bridged dynamically through the ObjC runtime), and the exact purpose of `chicagoRegister/Unregister/NotifyExpectedEscapeMethod` — **inferred** to relate to the "interrupt / escape" mechanism.

## 11. Addendum: why decompilation "failed" — two different causes (with Ghidra source evidence)

Across 5,217 functions the failures and warnings fall into two classes of **completely different nature**:

### A. Hard failures = timeouts, not incapability (3 functions, all recovered)

Three functions first reported `decompile incomplete: Exception while decompiling …: process: timeout`. Raising the per-function budget from 90 s to 400 s recovered all three. Measured wall time (including ~25–35 s of JVM + Ghidra startup):

| Function | Size | Measured total | Decompilation alone |
|---|---|---|---|
| `FUN_0005bc3c` (input) | 696 B | 153 s | ~120 s |
| `FUN_0005bef4` (input) | 1,136 B | 130 s | ~100 s |
| `FUN_000478f0` (audio) | 2,132 B | 179 s | ~150 s |

**Why so slow for such small functions**: all three carry `Type propagation algorithm not settling`. In Ghidra's decompiler source that warning fires when the type-propagation pass repeats **≥7 times without converging** (`coreaction.cc:5441`; the comment reads `This constant arrived at empirically`). The time goes into the type fixpoint iteration, not into function size — a 696-byte function taking ~120 s is the proof. All three are 284–476 lines of pseudocode with 5–10 `while` loops, 4–7 `goto`s and no `switch`.

> Conclusion: a **budget problem**, fixed by raising the budget. It is not "this function cannot be decompiled".

### B. Quality limit = computed indirect jumps (861 occurrences, permanent)

`/* WARNING: Could not recover jumptable at <addr>. Too many branches */` appears **861 times** (per function: cua 488/2817 = 17.3%, input 213/1821 = 11.7%, audio 133/579 = 23.0%).

Evidence from Ghidra's own C++ source (shipped with the install):

- The warning comes from `JumpTable::recoverAddresses()` at `jumptable.cc:2642`, thrown when every jump model fails.
- The chain is `JumpAssisted` (CALLOTHER-style) → `JumpBasic` → `JumpBasic2` (`jumptable.cc:2287-2302`), each bounded by `max_jumptable_size`.

**The trigger is that the binary genuinely contains computed branches.** Example: `swift56override_swift_task_future_wait` at 0x1b7c, with the warning pointing at 0x1c50 — where the raw bytes are `00 00 1f d6`, i.e. **`br x0`**: a tail dispatch through a register. Swift tail dispatch / coroutine resume, Rust `match` lowering and C++ thunks all emit this, and the target set cannot be enumerated statically.

**Consequence**: that jump table degrades into an opaque indirect jump in the pseudocode (Ghidra adds `Treating indirect jump as call`), while the rest of the function still decompiles. It is also the usual reason arm64 shows more jump-table warnings than x86: `br` is a register-indirect jump with no `jmp [table + idx*8]` memory operand for the analyzer to follow.

### C. Other quality warnings (whole corpus)

| Warning | Count | Meaning |
|---|---|---|
| `Type propagation algorithm not settling` | 32 | type fixpoint iterated ≥7 times without converging (a time-cost signal) |
| `Removing unreachable block` | 110 | statically unreachable blocks (including code after `noreturn`) |
| `Control flow encountered bad instruction data` | 13 | disassembly treated data as code |
| `Unknown calling convention` | 133 | missing symbol/ABI information (stripped Rust/C++ internal functions) |

> In one line: **"failure" comes in two kinds — budgetary (timeout, fixed by a bigger budget) and structural (computed indirect jumps whose targets cannot be enumerated). The latter does not stop pseudocode from being produced; it only leaves the control flow incomplete.**

## 12. Results after maxing out the budget (2026-10-14 re-run)

Re-ran all three libraries with everything opened up: **a fresh project plus a 7200 s/file analysis timeout** (default 300 s), **1200 s per function** (default 90 s), **jump-table cap 16384** (default 1024), maxInstructions 20M, maxPayload 512 MB. Scripts: [`tools/run_ghidra_max.sh`](../tools/run_ghidra_max.sh) and [`ghidra-scripts/DumpDecompMax.java`](../ghidra-scripts/DumpDecompMax.java).

| Library | Functions | Incomplete | Jump-table warnings | Type-propagation | Decompiled text | Slow (≥20 s) |
|---|---|---|---|---|---|---|
| cua (Swift) | 2817 → 2817 | 0 → 0 | 491 → **491** | 5 → 5 | 4.45 → 4.45 MB | 0 (worst 8 s) |
| input (Rust) | 1821 → 1821 | **2 → 0** | 235 → **235** | 13 → 15 | 3.74 → 3.71 MB | 2 (worst 153 s) |
| audio (C++) | 579 → 579 | **1 → 0** | 135 → **135** | 14 → 15 | 1.83 → 1.82 MB | 2 (worst 175 s) |

**Finding 1: budget fixes timeouts, not structural limits.**
- The three previously incomplete functions (`FUN_0005bc3c`, `FUN_0005bef4`, `FUN_000478f0`) went from an 80-character stub to 7–11 KB of full pseudocode — that is what budget buys.
- Not a single jump-table warning disappeared (491/235/135, identical per function to round one): they were never blocked by the 1024-entry cap or by time — **the targets genuinely cannot be computed** (`br xN` register-indirect jumps). Raising the cap 16× and the time 13× changes nothing, so this is now experimental rather than inferred.

**Finding 2: typing quality improved slightly.** Per-function comparison (hash after stripping whitespace/comments):

| Library | Comparable functions (unique names) | Identical | Different | Fixed | Worse |
|---|---|---|---|---|---|
| cua | 2091 | 1821 | 270 | 0 | 0 |
| input | 1792 | 1711 | 81 | 2 | 0 |
| audio | 578 | 553 | 25 | 1 | 0 |

The differences fall into two kinds, **both spot-checked**:
- **Cosmetic** (most): variable numbering and type spelling, e.g. `AXWindow AVar9` → `AVar7`, `long *` → `qword *`, `uVar5` ↔ `uVar6`; the same lines and structure.
- **Genuine improvement**: some functions go from `undefined8 uVar2;` to concrete types and symbol names, e.g. `pthread_mutex_t *ppVar1; ppVar1 = _malloc(0x40);`. Corpus-wide `undefined*` occurrences: input −2.8%, audio −3.5%, cua −0.1%.
- **No function got worse or fell back to incomplete.**

**Finding 3: one hypothesis refuted.** I suspected the jump-table failures came from unrelocated Mach-O pointers. Decoding the `LC_DYLD_INFO_ONLY` rebase stream: macho1 has 1,797 slots needing rebasing, but their on-disk values (e.g. `0x7851c`) are already **valid pre-slide vmaddrs for a base-0 image** (arm64 Mach-O adds the slide at load time) ⇒ **not a relocation problem**, consistent with Finding 1.

**Reproduce**: `bash tools/run_ghidra_max.sh` (~15 minutes, writes `out/max-{cua,input,audio}.txt`); comparison via `tools/compare_ghidra_runs.py` and `tools/diff_decomp_runs.py`.
