# 附：用 Ghidra 反编译 Claude Code 的原生层（2026-10-14）

> 结论先说：**Ghidra 能用，而且这次真挖出东西了——但它反编译的是"嵌入的原生库"，不是 JS，也不是 JSC 字节码。**
> 对象：Claude Code v2.1.287 的 `__BUN` 段尾部嵌进去的三个原生库。

## 1. 安装与配置（本机实际步骤）

```bash
brew install ghidra          # 12.1.4（formula），自动带上依赖 openjdk@21 21.0.12.1
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
GH=/opt/homebrew/Cellar/ghidra/12.1.4/libexec/support/analyzeHeadless
```

两个坑：

1. `brew install ghidra` 会写 `/opt/homebrew` 与 `~/Library/Caches/Homebrew`，都在本会话工作区之外——第一次必须放宽文件权限才能装。
2. Ghidra 每次启动都想写 `~/Library/ghidra/ghidra_<ver>_PUBLIC`（JAVA_HOME 缓存），也会被挡住。解法是把用户配置目录重定向进工作区：在 `libexec/support/launch.properties` 里把
   `#VMARGS=-Dapplication.settingsdir=` 改成
   `VMARGS=-Dapplication.settingsdir=<repo>/ghidra-cfg`
   （**注意**：这是 keg 内文件，`brew upgrade ghidra` 会覆盖，升级后要重设。）

反编译脚本：[`ghidra-scripts/DumpDecomp.java`](../ghidra-scripts/DumpDecomp.java)——遍历函数、调 `DecompInterface` 输出 C、支持名字过滤（`-` 表示全部）。

```bash
"$GH" ghidra-proj cua -import work/embedded/macho1.bin \
      -postScript DumpDecomp.java "-" out/cua-all.txt -scriptPath ghidra-scripts
```

## 2. 反编译结果规模

| 库 | 对应文件 | 函数数 | 反编译成功 | 输出 |
|---|---|---|---|---|
| `libComputerUseSwift.dylib`（arm64） | `work/embedded/macho1.bin` | 2,817 | 2,817 | 4.3 MB C |
| `libcomputer_use_input.dylib`（arm64） | `work/embedded/macho5.bin` | 1,821 | 1,819 | 4.0 MB C |
| `audio-capture.node`（arm64） | `work/embedded/macho6.bin` | 579 | 578 | 2.1 MB C |

Ghidra 12 内置 **Swift 名字还原**（分析日志里就有 `Swift Type Metadata Analyzer`），所以 Swift 那 2817 个函数名是可读的（`ComputerUseSwift.AXDispatch.typeText(in:)` 这种），这是它相对 `nm`/r2 的最大优势。

## 3. 发现 A：`libComputerUseSwift` = **无障碍（AX）层**

从还原出的符号里能直接读出整个能力面：

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

系统 API 的引用密度：`AXUIElement` 449 处、`CGImage` 146、`CGWindowList` 32、`NSWorkspace` 32、`CGEvent` 25、`ScreenCaptureKit` 5、`osascript` 0、`IOHIDPostEvent` 0。

**读出来的设计**（不只是 API 列表）：

- **操作走无障碍树、不走坐标点击**：`AXDispatch` 先在元素上"向上爬"找可点击/可编辑/可选择的祖先（`ascendToPressable/Textual/Selectable`），还要处理"同进程 Sheet 遮挡"（`enclosingSameProcessSheet`）。这是为了绕开坐标点击在弹窗/浮层上的失败。
- **结果结构化**：`Outcome` / `ReasonCode` / `Result: Codable` —— 原生侧把"成功/无效/不支持 + 原因码"编码回 JS，而不是抛异常。
- **人机冲突有专门机制**：`CollisionWatch.watch/unwatch`（检测用户是否插手/抢走了操作）、`WindowCover.hide/show`（操作期间遮挡目标窗口）。
- **有一个"幻影光标"**：`PhantomCursor.show/hide/reorderAllAboveTargets` —— 用来向用户展示 agent 正在点的位置，而不真的移动系统指针。
- **截图带排除名单**：`ScreenshotForComputerUse.computeExcludedApps` —— 截图前先算出哪些 App 不该进画面。
- **`chicago*EscapeMethod`**：一组注册/注销"逃生通道"的符号（名字像内部代号），推测是让用户能在 agent 操作过程中打断。

## 4. 发现 B：`libcomputer_use_input` = **底层输入注入（CGEvent）**

Rust 写的 cdylib（构建路径 `/Users/runner/work/apps/apps/packages/desktop/computer-use-input/target/{x86_64,aarch64}-apple-darwin/release/deps/`）。反编译结果里的系统 API 引用：`CGEventCreate` 16、`CGEventPost` 12、`CGEventSetFlags` 12、`CGEventKeyboardSetUnicodeString` 4、`NSEvent` 7；符号里有 `MouseEvent` / `KeyboardEvent` / `ScrollWheelEvent` / `KeyboardLayoutInputSource` / `KeyTranslate`。

**分工很清楚**：Swift 库负责"找到该操作的元素、判断能不能操作、把结果讲清楚"；Rust 库负责"真的把键鼠事件发出去"，并处理键盘布局与 Unicode 文本输入（`CGEventKeyboardSetUnicodeString` 绕开布局差异）。

## 5. 发现 C：`audio-capture.node` = CoreAudio

`_napi_register_module_v1` 存在（Node-API 插件）；`AudioUnit` 26 处、`AudioObject` 23 处，**没有** `ScreenCaptureKit`/`CATapDescription`。即：录音走 CoreAudio（AudioUnit/HAL），不是屏幕录制 API。

JS 侧（`raw/chunks2/2127__x-isNativeAudioAvailable.js`）按 `./vendor/audio-capture/<arch>-<platform>/audio-capture.node` 的路径加载，说明它是**按平台/架构 vendored** 的插件——Bun 单文件产物里那份就是给 macOS arm64 用的。

## 6. JS ↔ 原生的接口面（跨层对上）

JS 侧（`raw/chunks2/0788__chunk-c8t4wb5r.js` @69006 附近）读完 AX 操作结果后立刻调用 `setPhantomCursor(screenPt.x, screenPt.y, windowId, isClick)`，并把原生的 `outcome` / `reasonCode` / `axError` / `descentPath`（元素祖先链，按 role 折叠成 `Role×N`）拼进给模型的观察文本。

也就是说这条链是：

```
JS 决定"点哪里" → 原生 AX 层执行并返回结构化结果 → JS 画幻影光标 + 把 role/ancestor 链写进上下文给模型看
```

**这解释了 03 文档里"computer-use 相关工具在 JS 侧看不到实现"的疑问**：实现就在这三个原生库里。

## 7. 对"Ghidra 能不能用来反编译"的完整回答

| 层 | 结论 |
|---|---|
| JS 源码（`__BUN` 41.6 MB） | 已明文，不需要反编译；Ghidra 反而更差 |
| JSC 字节码（68–178 MB） | **Ghidra 做不到**——没有 JavaScriptCore 字节码的 processor/loader，格式随 JSC 版本变、无稳定公开规范。硬要做只能自写 loader |
| 原生代码（`__TEXT` 66 MB + 嵌入库 8.4 MB） | **可以，且有效**——本文的全部发现都来自这里 |

补充：对**主二进制**跑 Ghidra 不划算——159 MB 的 `__BUN` 段全是数据，应该只分析 `__TEXT`；而那部分主要是 Bun 运行时（Zig/C++），对"prompt / 多 agent 设计"没有增量。**真正值得反编译的就是这三个嵌入库**，它们小、有符号、且直接对应产品能力。

## 8. 未做 / 未验证

- 只做了**静态反编译**：没有动态验证（没跑过 computer-use，也没 hook 过这些库）。
- `chicago*EscapeMethod`、`CollisionWatch` 的**语义是推断**（基于符号名与调用关系），未读完整实现。
- 三个库里的 **x86_64 版本**（`macho0` / `macho2`）没单独分析，只看了 arm64。
- 主二进制的 `__TEXT` 段**没有分析**（Bun 运行时），sandbox profile 的 file-read/write 默认放行集合仍未还原。
- 产物是反编译文本（`out/*.txt`，共约 10 MB C 代码），未做逐函数审读，只做了符号面与系统 API 的归纳。

## 9. 复现

```bash
cd <repo>
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
GH=/opt/homebrew/Cellar/ghidra/12.1.4/libexec/support/analyzeHeadless
for pair in "cua macho1" "input macho5" "audio macho6"; do
  set -- $pair
  "$GH" ghidra-proj $1 -import work/embedded/$2.bin \
        -postScript DumpDecomp.java "-" out/$1-all.txt -scriptPath ghidra-scripts
done
grep "^// ====" out/cua-all.txt | head        # 函数清单（Swift 名已还原）
```
