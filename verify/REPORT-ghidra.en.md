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
