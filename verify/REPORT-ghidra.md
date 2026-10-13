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
| `audio-capture.node`（arm64） | `work/embedded/macho6.bin` | 579 | **579** | 2.1 MB C |

> 2026-10-14 补记：先前 3 个函数（input 2 个、audio 1 个）报的是 **decompile timeout**，把单函数预算从 90 s 放宽到 400 s 后**全部成功**——即 5,217/5,217 全部反编译完成。这 3 个都是无名运行时函数（`FUN_*`，带类型传播警告），对产品结论无增量。

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

## 10. 补记：`chicago*` —— computer-use 原生 API 的家族名

在二进制里检索 `chicago` 前缀，发现它是一整族 **ObjC 暴露给 JS 的原生方法名**（不是内部代号，而是真实 API 名字）：

```
chicagoCaptureRegion         chicagoCaptureExcluding        chicagoPrepareDisplay
chicagoResolvePrepareCapture chicagoListInstalled           chicagoListInstalledWithRunning
chicago-hide / chicago-open（Swift 闭包里的字符串对）
```

同一段里的字符串揭示了实现细节：

- 走 **ScreenCaptureKit**：`ScreenCaptureKit requires macOS 14.0`、`Region capture returned nil (permission missing or SCContentFilter failure)`
- 截图以 **JPEG base64 data URL** 回传：`data:image/jpeg;base64,`
- 参数契约写成错误文案：`captureRegion: expected (allowedBundleIds, regionX, regionY, regionW, regionH, outputWidth, outputHeight)`、`resolveBundleIds: expected names: string[]`
- 默认豁免 `com.apple.finder`；权限缺失有专门文案 `Screen Recording permission not granted`

也就是说：在 `PhantomCursor` / `AXDispatch` / `CollisionWatch` 之外，还有一层**面向"看屏幕"的接口**（区域截图、排除指定 App、显示器准备、已安装 App 列表），并把"哪些 App 该被排除在画面外"做成参数。

> 仍未验证：这些方法与 JS 侧调用点的对应关系（JS 语料里搜不到同名字符串，说明经 ObjC runtime 动态桥接），以及 `chicagoRegister/Unregister/NotifyExpectedEscapeMethod` 的确切用途——**推断**与"中断/逃生"机制有关。

## 11. 补记：反编译"失败"的两类原因（附 Ghidra 源码依据）

跑完 5,217 个函数后，失败/告警分两类，**性质完全不同**：

### A. 硬失败 = 超时，不是能力不足（3 个函数，已全部恢复）

三个函数最初报 `decompile incomplete: Exception while decompiling …: process: timeout`。把单函数预算从 90 s 放宽到 400 s 后**全部成功**。实测它们真正需要的时间（含 JVM + Ghidra 启动约 25–35 s）：

| 函数 | 大小 | 实测总耗时 | 反编译本身约 |
|---|---|---|---|
| `FUN_0005bc3c`（input） | 696 B | 153 s | ~120 s |
| `FUN_0005bef4`（input） | 1,136 B | 130 s | ~100 s |
| `FUN_000478f0`（audio） | 2,132 B | 179 s | ~150 s |

**为什么小函数这么慢**：它们的输出里都带 `Type propagation algorithm not settling`。Ghidra 反编译器源码里这条告警的触发条件是类型传播 pass 重复 **≥7 次仍未收敛**（`coreaction.cc:5441`，注释原文 `This constant arrived at empirically`）。也就是说时间花在类型不动点迭代上，与函数体积无关——696 字节的函数跑 ~120 s 就是证据。这三者都是 284–476 行伪代码、含 5–10 个 `while` 与 4–7 个 `goto`、无 `switch` 的循环/状态机式函数。

> 结论：这是**预算问题**，放宽即可；不存在"这个函数反编译不了"。

### B. 质量类限制 = 计算型间接跳转（861 处，永久）

`/* WARNING: Could not recover jumptable at <addr>. Too many branches */` 共 **861 处**（按函数计：cua 488/2817 = 17.3%、input 213/1821 = 11.7%、audio 133/579 = 23.0%）。

Ghidra 源码依据（随安装包一起提供 C++ 源码）：

- 该告警出自 `jumptable.cc:2642` 的 `JumpTable::recoverAddresses()`：当所有跳转模型都失败时抛出。
- 尝试链是 `JumpAssisted`（CALLOTHER 型）→ `JumpBasic` → `JumpBasic2`（`jumptable.cc:2287-2302`），每个都受 `max_jumptable_size` 上限约束。

**触发原因是二进制里确实是计算型跳转**。示例：`swift56override_swift_task_future_wait` 在 0x1b7c，告警指向 0x1c50，该处原始字节是 `00 00 1f d6`，即 **`br x0`** —— 目标在寄存器里的尾部分派。Swift 的 tail dispatch / 协程恢复、Rust 的 `match` 降级、C++ thunk 都会生成这种跳转；静态上无法枚举目标集合。

**后果**：那张跳转表在伪代码里退化成不透明间接跳转（Ghidra 会补一句 `Treating indirect jump as call`），但函数其余逻辑照常还原。这也是 arm64 上"跳转表告警比例高于 x86"的常见原因——`br` 是寄存器间接跳转，没有 x86 那种 `jmp [table + idx*8]` 的显式内存操作数形态。

### C. 其它质量告警（全库计数）

| 告警 | 次数 | 含义 |
|---|---|---|
| `Type propagation algorithm not settling` | 32 | 类型不动点迭代 ≥7 次未收敛（时间开销的信号） |
| `Removing unreachable block` | 110 | 存在静态不可达块（含 `noreturn` 之后的代码） |
| `Control flow encountered bad instruction data` | 13 | 反汇编把数据当成了代码 |
| `Unknown calling convention` | 133 | 符号/ABI 信息缺失（剥离过的 Rust/C++ 内部函数） |

> 一句话总结：**"失败"分两种——预算性的（超时，放宽即可）与结构性的（计算型间接跳转，无法静态枚举目标）。后者不阻止出伪代码，只是让控制流不完整。**

## 12. 榨干预算后的结果（2026-10-14 补跑）

按"能开的都开"重跑了一遍三个库：**全新项目 + 分析阶段超时 7200s/文件**（默认 300s）、**每函数 1200s**（默认 90s）、**跳转表上限 16384**（默认 1024）、maxInstructions 20M、maxPayload 512MB。脚本：[`tools/run_ghidra_max.sh`](../tools/run_ghidra_max.sh) + [`ghidra-scripts/DumpDecompMax.java`](../ghidra-scripts/DumpDecompMax.java)。

| 库 | 函数 | 未完成 | 跳转表告警 | 类型传播告警 | 反编译文本 | 慢函数(≥20s) |
|---|---|---|---|---|---|---|
| cua (Swift) | 2817 → 2817 | 0 → 0 | 491 → **491** | 5 → 5 | 4.45 → 4.45 MB | 0 个（最慢 8s） |
| input (Rust) | 1821 → 1821 | **2 → 0** | 235 → **235** | 13 → 15 | 3.74 → 3.71 MB | 2 个（最慢 153s） |
| audio (C++) | 579 → 579 | **1 → 0** | 135 → **135** | 14 → 15 | 1.83 → 1.82 MB | 2 个（最慢 175s） |

**结论一：预算只能修"超时"，不能修"结构性"。**
- 3 个原先 incomplete 的函数（`FUN_0005bc3c`/`FUN_0005bef4`/`FUN_000478f0`）从 80 字符的桩变成 7–11 KB 完整伪代码——**这是预算能买到的东西**。
- 跳转表告警**一个都没少**（491/235/135，与第一轮逐条相同）：说明它们不是被 1024 条上限卡住，也不是被时间卡住，而是**目标真的算不出来**（`br xN` 寄存器间接跳转）。把上限抬 16 倍、时间抬 13 倍都不动，这条结论现在是实验坐实的，而不是推断。

**结论二：顺带把类型质量抬高了一点。** 逐函数比对（规范化去空白/注释后哈希）：

| 库 | 可比函数（唯一名） | 完全相同 | 有差异 | 修复 | 变坏 |
|---|---|---|---|---|---|
| cua | 2091 | 1821 | 270 | 0 | 0 |
| input | 1792 | 1711 | 81 | 2 | 0 |
| audio | 578 | 553 | 25 | 1 | 0 |

差异分两类，**抽样核实过**：
- **外观类**（多数）：变量编号与类型拼写变化，例如 `AXWindow AVar9` → `AVar7`、`long *` → `qword *`、`uVar5` ↔ `uVar6`；同函数行数与结构不变。
- **实质改进**：部分函数从 `undefined8 uVar2;` 变成具体类型并用上符号名，例如 `pthread_mutex_t *ppVar1; ppVar1 = _malloc(0x40);`。全库 `undefined*` 出现次数：input −2.8%、audio −3.5%、cua −0.1%。
- **没有任何函数变坏或退回 incomplete。**

**结论三：还有一个被证伪的猜想。** 我一度怀疑跳转表失败是因为 Mach-O 指针未重定位。解析 `LC_DYLD_INFO_ONLY` 的 rebase 流后：macho1 有 1,797 个待重定位槽，但它们在磁盘上的值（如 `0x7851c`）本来就是**该镜像基址下的合法 vmaddr**（arm64 Mach-O 在加载时加 slide，文件里存的是 slide 前地址）⇒ **不是重定位问题**，与结论一一致。

**复现**：`bash tools/run_ghidra_max.sh`（约 15 分钟，产出 `out/max-{cua,input,audio}.txt`），对比脚本 `tools/compare_ghidra_runs.py`、`tools/diff_decomp_runs.py`。
