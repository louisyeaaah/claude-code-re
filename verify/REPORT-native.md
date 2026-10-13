# 步骤 4 · 硬核层：字节码区完整性与原生层

> 对象：`~/.local/share/claude/versions/2.1.287`（Mach-O arm64，227,827,120 字节）
> 配套工具：`otool`、`file`（系统自带），`zstd`（/opt/homebrew/bin/zstd），`raw/carve_modules.py`

## 1. 结论速览

1. 整份文件的结构已定死：**`__TEXT`(0–66.6 MB) + `__DATA_CONST` + `__DATA` + `__BUN`(68.2–227.2 MB，159 MB) + `__LINKEDIT`**。所有 JS/字节码/嵌入原生库都在 **`__BUN,__bun`** 这一个节里。
2. `__BUN` 内部三段：**字节码/字符串表区（68.2–177.8 MB）→ JS 模块源码区（177.8–219.0 MB，41.6 MB）→ 嵌入原生库区（219.0–227.2 MB，8.4 MB）**。
3. **提示词没有"只存在于字节码里"的副本**：字节码区的字符串表与源码区的提示词是同一批文本，抽查的提示词串全部能在源码语料里找到。之前"43,607 条在源码里找不到"是运行期字符串（Bun/Rust/JSC 内部）与转义差异造成的假缺口。
4. 尾部 8.4 MB **不是 JS 字节码，而是嵌进去的原生动态库**，其中有：
   - `@rpath/libComputerUseSwift.dylib`（**x86_64 + ARM64 两份，Swift**）
   - `libcomputer_use_input.dylib`（**Rust**，构建路径泄漏 `/Users/runner/work/apps/apps/packages/desktop/computer-use-input/target/{x86_64,aarch64}-apple-darwin/release/deps/`）
   - `@rpath/audio-capture.node`（Node 原生插件）
5. 除 JS 模块外还有 **231 个非 chunk 的 bunfs 资源**（`SKILL-*.md[.zst]`、`README-*`、`SCHEMA-*`、`NOTICE-*`，其中 132 个 `.zst`）。这部分**没有逐个提取**（见 §5 未完成项）。

## 2. Mach-O 分段

```
__PAGEZERO    vmaddr 0x0            filesize 0
__TEXT        vmaddr 0x100000000    fileoff        0  filesize  66,633,728
__DATA_CONST  vmaddr 0x103f8c000    fileoff 66,633,728  filesize   1,425,408
__DATA        vmaddr 0x1040e8000    fileoff 68,059,136  filesize     147,456
__BUN         vmaddr 0x1042dc000    fileoff 68,206,592  filesize 158,957,568   ← 全部嵌入内容
__LINKEDIT    vmaddr 0x10da74000    fileoff 227,164,160 filesize     662,960
```

`__BUN` 里只有一个节 `__bun`（size 158,949,736）——Bun 的 `--compile` 把模块图、源码、资源、嵌入库全塞进这一个节。

## 3. 字节码区完整性核对（步骤 4a）

做法：把非源码区（`__BUN` 的 68.2–177.8 MB、219.0–227.2 MB）里所有 ≥24 字符的可打印串抽出来，按"句子型"过滤后逐个在 2174 个模块源码里查。

| 口径 | 数量 |
|---|---|
| 非源码区可打印串（≥24） | 163,486 |
| 其中"句子型"候选 | 77,098 |
| 在源码语料里找不到 | 43,607（56.6%） |
| 加上"提示词味道"过滤后仍找不到 | 2,737 |
| 人工抽查后确认属于 Claude Code 提示词、却真的不在源码里的 | **0** |

抽查过程（`verify/bytecode-gap-check` 与两轮人工复核）：

- 43,607 条里绝大多数是 **Bun / Rust / JavaScriptCore 运行时**的字符串（`wtf8`、`RobinHoodHashTable`、`assertion failed`、bash 补全、错误页 CSS、词表数据……），本就不属于 Claude Code。
- 看似"Claude Code 提示词"的少数条目（如 `When a finished piece of work is meant for other people or agents…`、`Why Claude Code refused to start…`、`Those prefixes match byte for byte…`）**在源码语料里都能找到**（`raw/chunks2/`）——第一轮判为缺口是因为字节码字符串表存的是**解码后的整串**，而源码里是转义/拼接形式，比对口径不同。
- 结论：**源码区就是完备的提示词来源**；字节码区不含独有提示词。这也解释了为什么 `strings` 抓到的 UTF-16 副本（73–80 MB）与源码一一对应。

## 4. 嵌入的原生库（步骤 4b）

在 `__BUN` 尾部 8,374,397 字节（文件偏移 **219,452,723** 起）里扫 Mach-O 魔数，找到 7 个 Mach-O 头（其中 2 个是伪造命中）：

| blob 内偏移 | 架构 | 类型 | 安装名 / 来源 |
|---|---|---|---|
| `0x000fd4` | x86_64 | DYLIB | `@rpath/libComputerUseSwift.dylib`（含 `__swift5_typeref`、`__constg_swiftt` 等 Swift 节） |
| `0x137fd4` | ARM64 | DYLIB | `@rpath/libComputerUseSwift.dylib`（同一库的 arm64 版） |
| `0x26532d` | x86_64 | DYLIB | `/Users/runner/work/apps/apps/packages/desktop/computer-use-input/target/x86_64-apple-darwin/release/deps/libcomputer_use_input.dylib` |
| `0x33032d` | ARM64 | DYLIB | 同上，`aarch64-apple-darwin` 版 |
| `0x429630` | ARM64 | DYLIB | 依赖 `@rpath/audio-capture.node`、`/usr/lib/libobjc.A.dylib` |

含义（推断，基于上述一手路径与节名）：**"computer use" 不是纯 JS 实现**，而是 JS 侧（`mcp__cua__*` / 屏幕控制工具）调用一组原生库：Rust 写的输入注入库 + Swift 封装，另有音频采集的 N-API 插件。构建路径显示它们来自 Anthropic 的 monorepo（`apps/packages/desktop/computer-use-input`），并被打进单文件产物。

> 这也解释了 03/06 文档里工具清单中的 `ComputerUse` 相关能力为何没有出现在 JS 模块里：**实现不在 JS 侧**。

## 5. 未完成 / 未验证

1. **231 个非 chunk 资源未逐个提取**。已确认路径表（`/$bunfs/root/SKILL-*.md[.zst]`、`README-*`、`SCHEMA-*`、`NOTICE-*`，132 个 `.zst`）存在，并用 `zstd -d` 对全文件 169 处 zstd 帧做了尝试：25 帧解压成功，但内容全是 **Bun 运行时自身的东西**（错误页 CSS、bash 补全、Bun 的 JS shim），没有解出 Claude Code 的 SKILL 资源——说明这些资源的帧切分方式与我的"魔数到下一个魔数"切片假设不符，需要按 bunfs 文件表逐个定位。
   - 影响有限：已知的几份 skill/prompt 正文（`# Skillify`、`# Claude Code Doctor`、`# Workflow authoring reference`、`# Dream`）**在 JS 模块里都有逐字副本**（见 08），所以提示词覆盖不受影响。
2. `HOOKS_WORKER_URL` 指向 `/$bunfs/root/src/plugins/functionHooks/hooks-worker/hooks-worker.js`，但该文件既不在 2174 个模块里，也没从资源区解出——**其实现仍未读到**（与 06 的结论一致）。
3. 字节码本身**没有反编译**。JSC 字节码没有公开的反编译器；本步只做了"完整性核对"（证明源码区完备），没有把字节码还原成可读 IR。若确实需要，只能做指令级统计（例如逐帧 opcode 直方图），对提示词/多 agent 主题没有增量价值。
4. 7 个 Mach-O 头里有 2 个是数据里恰好出现的魔数（解析出荒谬的 `ncmds=1036213520`），已剔除；嵌入库里是否还有未识别的小组件（如 `audio-capture.node` 本体）**未继续分解**。

## 6. 复现

```bash
# 分段与节
otool -l ~/.local/share/claude/versions/2.1.287

# 尾部 blob 切出（最后一个模块正文之后）
python3 raw/carve_modules.py          # 生成 modules.json（含 2173 的 end / binary_tail 元数据）
python3 - <<'PY'
import json
m=[x for x in json.load(open("raw/modules.json")) if x["idx"]==2173][0]
d=open("~/.local/share/claude/versions/2.1.287","rb").read()
open("work/tail-blob.bin","wb").write(d[m["binary_tail"]["abs_start"]:])
PY

# 完整性核对
python3 verify/bytecode_gap_check.py

# 嵌入的原生库
python3 - <<'PY'
import re, struct
blob=open("work/tail-blob.bin","rb").read()
for i,o in enumerate([m.start() for m in re.finditer(rb"\xcf\xfa\xed\xfe", blob)]):
    cpu,sub,ft,ncmds,sz = struct.unpack_from("<iiIII", blob, o+4)
    open(f"work/embedded/macho{i}.bin","wb").write(blob[o:o+3_000_000])
PY
file work/embedded/*.bin && otool -D work/embedded/macho0.bin
```

## 7. 权限门与沙箱：原生侧的实际情况（补充）

`codesign` 与字符串扫描给出的结论：

```
Identifier=com.anthropic.claude-code     TeamIdentifier=Q6L2SF6YDW     Format=Mach-O thin (arm64)
flags=0x10000(runtime)                    Timestamp=2 Oct 2026 at 2:11:41 am
entitlements: com.apple.security.automation.apple-events,
              com.apple.security.cs.allow-jit,
              com.apple.security.cs.allow-unsigned-executable-memory,
              com.apple.security.cs.disable-library-validation,
              com.apple.security.device.audio-input
```

要点：

- **CLI 自身没有 macOS App Sandbox 权限**（无 `com.apple.security.app-sandbox`），而是带硬化运行时 + JIT 许可 + Apple Events 自动化许可 + 麦克风许可。也就是说"权限门"是**应用层自己实现的**，不是操作系统强制的。
- 操作系统级的隔离是**由 CLI 主动调用**的：二进制里能找到 `sandbox-exec`(3)、`sandbox_init`(15)、`seatbelt`(2)、`(version 1)`(4)、`allow file-read`(9)、`deny network`(2) —— 即 macOS 上用 seatbelt profile 起子进程；Linux 侧对应 `bwrap`(64) 与 `seccomp`(96)。
- 这与 06 文档的结论拼在一起才完整：**JS 侧决定"要不要问用户"，原生/系统侧决定"跑起来之后能碰到什么"**——两层是独立实现，前者可被 flag/设置改写，后者是进程边界。

> 补充（本步内已补做）：**sandbox profile 不是原生代码拼的，而是在 JS 侧拼的**——`raw/chunks2/0205__chunk-5vadtxaa.js` 的 `PV()` 直接构造 seatbelt profile 字符串数组（`(version 1)` + `(deny default (with message …))` + Mach IPC 白名单 + 可选的 trustd/apple-events + 由 `_a()`/`RV()`/`kV()` 生成的 file-read/file-write 规则），再由 `sandbox-exec` 启动子进程。逐字片段见 [`seatbelt-profile.md`](seatbelt-profile.md)（37 条）。默认放行集合已补做，见 [`REPORT-sandbox.md`](REPORT-sandbox.md)（含 `sandbox.enabled` 默认 false、读写规则构造顺序、内置禁写清单）。仍未做的：Linux 侧 `bwrap`/`seccomp` 的对应代码。
