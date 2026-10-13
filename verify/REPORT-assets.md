# Claude Code v2.1.287 内嵌资源盘点报告（168/169 个 zstd 帧）

> 对象：`~/.local/share/claude/versions/2.1.287`（227,827,120 字节，sha256 前 16 位 `6eab8333fe212155`）
> 素材：[work/assets/](work/assets/) 下 168 个已解压文件 + [index.json](work/assets/index.json)；抽取脚本 [tools/extract_assets.py](tools/extract_assets.py)
> 方法：zstd 魔数扫描 + `zstandard` 解压；**不是**按名字表精确映射（见 §5）

## 0. 结论速览

- 二进制里能扫到 **169** 个 zstd 帧，成功解压 **168** 个，解压后合计 **11,283,111 字节（11.28 MB）**：Claude 侧 135 个（9,908,273 B / 9.91 MB），Bun 运行时侧 33 个（1,374,838 B / 1.37 MB）。
- 唯一失败的帧（index 33，`0x3b7a43c`）在 **Bun 区**：帧头声明需要外部 zstd 字典（`Dictionary mismatch`），且紧邻字节是 Bun 字符串表——更像魔数误命中。**Claude 侧 135 个帧全部解压成功。**
- 两区划分不是猜的：Bun 侧帧挤在 `0x388cbb3`–`0x3a02f95`（59.3–60.8 MB），Claude 侧帧挤在 `0xd0dfe8e`–`0xd858d9d`（219.0–226.9 MB），中间 151 MB 是 JSC 字节码与模块区。
- 名字表（`/$bunfs/root/<name>-<hash>.<ext>[.zst]`）在 `0xd85b83d`–`0xd87eac9`：非 chunk 条目 **230** 个、chunk 条目约 2169 个——这就是早前报告里“231 个非 chunk 资源”的出处。
- 名字与内容**不能**一一推出来：本文用二进制内 JS 加载器引用 + 内容指纹只钉死了 **11** 条精确对应（白板 6 个文件 + mermaid/hljs/Chart.js/PSL/函数钩子 .d.ts），其余只能给出“帧序 = 名字序”的单调关系。
- 名字表的 `.zst` 后缀**不可靠**：`mermaid.min.js`、`chart.umd.min.js`、`hljsBundle.generated.min.js` 都不带 `.zst`，但它们确实是 zstd 帧。
- 帧之间还有**未压缩**的兄弟资源（“没有 .zst 后缀那批”的落点）：Claude 区 3 处非 1 字节间隙共 4,721,613 字节 = 2 个 WOFF2 字体 + ≥4 个设计/幻灯片提示词文档 + ≥6 段 Mach-O + `audio-capture.node` + 10 KB 的 autonomous-loop 提示词。

## 1. 方法与可复现

### 1.1 抽取流程

1. 读整个二进制，正则扫 `\x28\xb5\x2f\xfd`（zstd 魔数）→ 169 个候选偏移；
2. 每个偏移取 `d[o:o+3_000_000]`，交给 `zstandard.ZstdDecompressor().decompress(..., max_output_size=16_000_000)`；
3. UTF-8 解码（`errors=replace`），按 frontmatter `name:` 或首个标题生成 slug 写盘，记录偏移、解压字节数、sha256 前 16 位、区域。

关键行：[extract_assets.py:15-16](tools/extract_assets.py#L15-L16)（魔数扫描 + 解压器）、[extract_assets.py:42](tools/extract_assets.py#L42)（区域判定 `o < 0x4000000`）。区域判定只影响归类，不影响解压结果。

### 1.2 为什么 `zstd -d` 直接切片会失败

连续帧之间由**恰好 1 个 `0x00` 填充字节**隔开（实测 gap=1），而帧长度没有前缀——边界只能靠解码确定，魔数扫描只给下一帧起点。用 `/opt/homebrew/bin/zstd` 做的一手对照：

| 切法 | 命令 | 结果 |
|---|---|---|
| 本帧起点 → 下一魔数（含填充字节） | `zstd -d -c slice_exact.zst` | 退出码 0，但 stderr 报 `unknown header`（多出尾部 1 字节） |
| 起点 → 起点 + 3 MB 固定窗口 | `zstd -d -c slice_over.zst` | `unsupported format`，失败 |
| 截断到前 1000 字节 | `zstd -d -c slice_short.zst` | `Read error (39) : premature end`，失败 |
| 起点前移 500 字节 | `zstd -d -c slice_prev.zst` | `unsupported format`，失败 |

一句话：先扫魔数定起点、再靠解码定终点（或容忍 1 字节填充）；CLI 拿字节区间硬切得不到可用结果。

### 1.3 成功率与失败帧

- 169 帧 / 成功 168（99.4%）；Claude 侧 135/135，Bun 侧 33/34。
- 失败帧 index 33：`off=0x3b7a43c`，`Dictionary mismatch`。帧头描述符 `0x62` 表示带 1 字节 dictionary ID（解码器要求外部字典），但该处前后是 Bun 的字符串表（`elselinklogsglob`、`pretestNODE />`），且距 Bun 帧簇有 ~1.5 MB 空洞。**两种解释都无法排除**：真帧但需字典 / 魔数误命中。

### 1.4 为什么分成两个区域（bun 33 vs claude 135）

单文件产物是 `bun build --compile` 的可执行文件：前面是 Bun 运行时自带资产，后面才是 Claude Code 自己的 `$bunfs/root/` 载荷。

| 区域 | 帧数 | 偏移范围 | 解压字节 | 内容特征 |
| `bun` | 33 | `0x388cbb3`–`0x3a02f95`（59.3–60.8 MB） | 1,374,838 | Bun 错误页 CSS（asset-000）、RSC 客户端逻辑（003）、bun 补全（005/007）、npm 包名表（008，162 KB）、`node:` polyfill（010/013/016/024/032）、util/path/net/tls/buffer 兼容层 |
| `claude` | 135 | `0xd0dfe8e`–`0xd858d9d`（219.0–226.9 MB） | 9,908,273 | 本文 §2 的 135 个资源；紧接其后就是名字表 `0xd85b83d`–`0xd87eac9` |

阈值 `0x4000000`（64 MB）只是把两簇分开的经验值，落在 60.8 MB 与 219.0 MB 之间的 151 MB 空洞里，对归属没有影响。

## 2. 总表：Claude 侧 135 个资源（按大小降序）

「类型」是本文归类：三方=第三方 vendored；技能=带 `---` frontmatter 的 SKILL/命令文档；技能配套=技能自带的模板与脚本；参考=文档；前端=HTML；脚本=JS/Python；类型声明=`.d.ts`；数据=JSON。摘要均为逐文件读开头若干行后的改写；标“未细读”的按字面描述。

| 字节 | 行 | 抽出文件名 | 类型 | 一句话摘要 |
|---|---|---|---|---|
| 3,566,058 | 3587 | `asset-048-asset.txt` | 三方 | mermaid 11.16.1 完整打包（3.5 MB）；文件内还带 DOMPurify 3.4.0、lodash 等依赖的许可声明（见 §3.4） |
| 593,163 | 47 | `asset-035-asset.txt` | 三方 | highlight.js 11.11.1 浏览器 IIFE 包，186 种语法；文件头写明由 scripts/generate-hljs-browser-bundle.ts 生成，BSD-3-Clause |
| 573,702 | 14914 | `asset-044-asset.txt` | 类型声明 | 函数钩子（function hooks）插件 API 的 TypeScript 声明；头部注明 EARLY ACCESS、由引擎写在 mod 目录旁的 .claude-plugin/types/claude-code/index.d.ts |
| 329,237 | 4554 | `asset-162-asset.txt` | 前端 | whiteboard 模板（329 KB，<title>Whiteboard</title>，内联 @ant/cds 令牌表） |
| 317,800 | 2253 | `asset-143-Model-Migration-Guide.md` | 参考 | Model Migration Guide：迁移步骤、per-SDK 语法差异、破坏性变更与废弃参数；路由 /claude-api migrate |
| 208,522 | 14 | `asset-034-asset.txt` | 三方 | Chart.js v4.5.1 的 UMD 打包（首行 banner 声明 MIT）；内含 Colors/Decimation/Filler/Legend 等插件 |
| 167,048 | 1 | `asset-063-asset.txt` | 三方 | 公共后缀表（PSL）JSON：来源 publicsuffix.org，许可 MPL-2.0，版本 2026-09-08_12-18-37_UTC（ICANN+PRIVATE 段） |
| 154,540 | 2710 | `asset-159-asset.txt` | 前端 | whiteboard 模板（154 KB，<title>Whiteboard</title>，外链 Google Fonts） |
| 127,802 | 3094 | `asset-041-asset.md` | 技能配套 | workshop-page 直出 HTML 模板（*.workshop.html 的钦定模板）；写明发布前结构校验的硬规则（脚本须逐字节一致等） |
| 117,526 | 2962 | `asset-040-asset.md` | 技能配套 | workshop 工件 HTML 模板（HTML 注释里的 frontmatter：name: workshop）；注明四个机械填充槽 {{TITLE}}/{{TAB_TITLE}}/{{EYEBROW}}/{{SUMMARY}} |
| 105,678 | 1142 | `asset-163-asset.txt` | 脚本 | whiteboard helper = **merge-state.mjs**（live 变体；用法注释自称 `node merge-state.mjs`）：读板面状态、追加元素并避让已有元素 |
| 101,940 | 936 | `asset-054-asset.md` | 脚本 | Claude Test 主 CLI：spec 写入、git 提交状态、runs 目录与日志（推断为 ct.mjs） |
| 100,774 | 595 | `asset-118-Building-LLM-Powered-Applications-with-Claude.md` | 参考 | Building LLM-Powered Applications with Claude：先选“面”（surface）再写代码；正文含 {{FABLE_NAME}}/{{OPUS_NAME}} 等模板占位与“训练先验可能已过期”警告 |
| 96,305 | 1769 | `asset-157-asset.txt` | 前端 | 96 KB 自包含 HTML 模板：<title> 处是 `<!-- SLOT: TITLE ...` 槽位说明；推断为 artifact/plan 类模板之一 |
| 95,251 | 158 | `asset-043-Environment.md` | 参考 | # Environment 上下文槽位说明：三类槽位与 <user_environment_to_replace> 占位块 |
| 94,008 | 1532 | `asset-148-With-stdout-stderr-redirected-to-a-pipe-as-under.md` | 脚本 | prefix_diff.py：对比两次 Messages 请求，指出 thinking block 绑定部分的差异 |
| 88,532 | 1748 | `asset-038-asset.md` | 技能配套 | artifact-pr-review 的 HTML 片段模板（无 doctype/html/head 包裹）；注释要求把标题/描述/diff/路径全部转义 |
| 88,266 | 1482 | `asset-160-asset.txt` | 脚本 | whiteboard helper = **board.mjs**（solo 变体；用法注释自称 `node board.mjs`）：读页面内嵌的 board 状态与 PNG 快照，写回可再发布页面 |
| 80,310 | 513 | `asset-166-Plugin-eval-claude-plugin-eval-and-skill-doctor.md` | 参考 | Plugin eval 参考：case.yaml 字段、graders、mock MCP、运行选项、退出码、HTML 报告 |
| 77,274 | 2232 | `asset-045-asset.txt` | 脚本 | 以 `//// <路径>` 注释拼接的多模块 JS（collector/*：create-collector、hold-of、mock-clock…）；[REPORT-plugin-api.md](verify/REPORT-plugin-api.md) 判定为函数钩子的 `claude plugin test` 套件源码——本轮未细读，按该报告口径转述 |
| 70,477 | 857 | `asset-067-asset.md` | 脚本 | Claude Test 运行日志读取：逐行 JSON 判定错误应答与状态 |
| 69,242 | 340 | `asset-084-Storybook-source-shape.md` | 参考 | Storybook source shape：Storybook 是保真度 oracle 而非运行时；Playwright+chromium 为必需 |
| 69,156 | 338 | `asset-127-Hill-Climbing-on-an-Eval.md` | 参考 | Hill-Climbing on an Eval |
| 66,582 | 1066 | `asset-149-With-stdout-stderr-redirected-to-a-pipe-as-under.md` | 脚本 | drop_block_probe.py：回放已捕获会话，报告 API 丢弃了什么、为什么 |
| 65,592 | 1547 | `asset-072-asset.txt` | 技能配套 | workshop 的 decisions 脚本：页面上的决策块交互 |
| 64,004 | 249 | `asset-146-Preserved-Thinking---Keeping-Earlier-Reasoning-V.md` | 参考 | Preserved Thinking - 让早前推理跨轮次保持有效 |
| 59,209 | 289 | `asset-082-Package-source-shape.md` | 参考 | Package source shape：无 Storybook 时改用 dist + .d.ts 作为组件源 |
| 59,098 | 501 | `asset-071-Claude-Test-the-conversation-side.md` | 技能 | Claude Test 主技能：用自然语言 spec 在后台跑 web 应用并回 PASS/FAIL + 截图 |
| 58,092 | 244 | `asset-122-Cost-Optimization---Cutting-Spend-per-Completed.md` | 参考 | Cost Optimization：以“每个完成任务的花费”而非 token 单价为优化单位 |
| 56,307 | 919 | `asset-057-asset.txt` | 脚本 | Claude Test 配置层：RC 文件、私有目录、键名校验与告警（推断为 config.mjs） |
| 55,699 | 1005 | `asset-085-asset.md` | 脚本 | design-sync 转换器主脚本（package-build.mjs）：把设计系统打成 DS-project 布局 |
| 55,191 | 235 | `asset-124-Building-an-Eval-for-a-Claude-Powered-Applicatio.md` | 参考 | Building an Eval |
| 51,938 | 805 | `asset-086-asset.md` | 脚本 | package-validate.mjs：产物目录的形状校验 + 渲染抽样检查 |
| 48,945 | 237 | `asset-150-Prompt-Audit---Finding-and-Removing-Dated-Prompt.md` | 参考 | Prompt Audit：找出并移除过时的提示写法 |
| 46,110 | 753 | `asset-097-asset.md` | 脚本 | compare.mjs：抓自包含 preview 与 storybook 真图做对照 |
| 44,225 | 577 | `asset-152-Tool-Use-Concepts.md` | 参考 | Tool Use Concepts：工具使用的概念基础 |
| 42,953 | 498 | `asset-070-Claude-Test-runner-drive-the-app-in-a-browser-ju.md` | 技能 | Claude Test 内部技能：在后台浏览器里按 spec 驱动应用（含 browser_* MCP 工具白名单） |
| 42,525 | 688 | `asset-036-artifact-pr-review.md` | 技能 | artifact-pr-review 技能：把 GitHub PR 变成结构化评审简报（结论、建议、可视化解释、决策块），正文含 HTML 模板 |
| 40,528 | 725 | `asset-039-workshop.md` | 技能 | workshop 技能：与用户一次一个决策地把设计做出来，并发布成可迭代文档 |
| 39,653 | 98 | `asset-147-Preserved-Thinking---Causes-Fixes-and-the-Keep-L.md` | 参考 | Preserved Thinking - 成因、修复与 Keep 清单 |
| 38,063 | 1087 | `asset-046-asset.md` | 技能配套 | plan 工件 HTML 模板（name: plan）；含 {{TITLE}} 等填充契约与 @ant/cds vanilla 令牌内联说明 |
| 37,817 | 682 | `asset-093-Where-things-are.txt` | 参考 | Where things are：design-sync 的产物清单与文件地图 |
| 35,661 | 504 | `asset-141-Managed-Agents---Tools-Skills.md` | 参考 | Managed Agents - Tools & Skills |
| 34,396 | 455 | `asset-130-Managed-Agents---Endpoint-Reference.md` | 参考 | Managed Agents - Endpoint Reference |
| 33,603 | 500 | `asset-064-asset.txt` | 脚本 | Claude Test 技能解析：parseSkillMd 等技能元数据解析 |
| 33,036 | 297 | `asset-151-Prompt-Caching---Design-Optimization.md` | 参考 | Prompt Caching - 设计与优化：前缀匹配不变量 |
| 32,832 | 359 | `asset-132-Managed-Agents---Core-Concepts.md` | 参考 | Managed Agents - Core Concepts |
| 32,005 | 144 | `asset-050-Function-hooks-the-long-form.md` | 参考 | 函数钩子长文：插件是什么、引擎如何加载 mod、能钩到什么 |
| 31,711 | 442 | `asset-126-Cost-reduction-search-how-to-structure-it.md` | 参考 | 降本检索该怎么组织 |
| 31,080 | 500 | `asset-037-artifact-pr-review.md` | 技能 | 同技能的另一个版本：同为 PR 评审简报，强调 PR 内容是不可信输入、需 HTML 转义 |
| 30,120 | 542 | `asset-089-asset.txt` | 脚本 | lib/dts.mjs：用 ts-morph 解析 <Name>Props 的结构类型 |
| 29,118 | 287 | `asset-113-Upgrading-the-anthropic-Python-SDK-0.x---1.x.md` | 参考 | anthropic Python SDK 0.x → 1.x 升级 |
| 28,619 | 292 | `asset-059-asset.txt` | 脚本 | Claude Test 环境报告：逐文件扫描，符号链接与非普通文件也上报状态 |
| 28,236 | 847 | `asset-074-asset.txt` | 技能配套 | CDS 令牌块：从 workshop-page 模板逐字节切出，供宿主页内嵌 |
| 28,225 | 126 | `asset-083-design-sync.md` | 技能 | design-sync 技能：把 React 设计系统转换并推到 claude.ai/design |
| 27,892 | 204 | `asset-125-Eval-health-checklist.md` | 参考 | Eval 健康检查清单 |
| 27,847 | 282 | `asset-140-Managed-Agents---Self-Hosted-Sandboxes.md` | 参考 | Managed Agents - Self-Hosted Sandboxes |
| 27,340 | 271 | `asset-052-Onboarding-the-machine-first-then-the-starter-su.md` | 参考 | Claude Test 上手文档：先机器、后起步套件，再讲与人的分工 |
| 26,203 | 260 | `asset-136-Managed-Agents---Multiagent-Sessions.md` | 参考 | Managed Agents - Multiagent Sessions |
| 25,497 | 328 | `asset-062-asset.txt` | 脚本 | Claude Test 工具装载：读文件 + 哈希 + pathToFileURL 动态加载 |
| 25,248 | 263 | `asset-056-asset.txt` | 脚本 | Claude Test 运行态与端口探测：ownPorts，并向页面回答 JSON 状态 |
| 25,159 | 576 | `asset-049-asset.txt` | 脚本 | AppifactRepl 工具的内置 SDK：把 stdin 上的代码当单个 async 函数跑一次，含 claude.use(db/files/assets) 接口 |
| 25,041 | 290 | `asset-134-Managed-Agents---Events-Steering.md` | 参考 | Managed Agents - Events & Steering |
| 24,065 | 366 | `asset-161-whiteboard.md` | 技能 | whiteboard（live 变体）：多人实时看到彼此笔迹与光标，本会话在板上以小人像表示在场 |
| 23,240 | 417 | `asset-101-asset.md` | 脚本 | resync.mjs：re-sync 总驱动，输出机器可读 verdict |
| 22,987 | 167 | `asset-129-Live-Documentation-Sources.md` | 参考 | Live Documentation Sources：WebFetch 用的实时 URL 清单 |
| 22,604 | 651 | `asset-155-Tool-Use---TypeScript.md` | 参考 | Tool Use - TypeScript |
| 22,529 | 289 | `asset-065-asset.txt` | 脚本 | Claude Test 工具安装：installTools、toolsDir、锁文件（推断为 tools.mjs） |
| 22,228 | 296 | `asset-121-Anthropic-CLI-ant.md` | 参考 | Anthropic CLI `ant`：把 API 资源暴露成 shell 子命令 |
| 20,946 | 88 | `asset-047-artifact-design.md` | 技能 | artifact-design 技能：写任何 Artifact 之前的设计准则入口 |
| 20,442 | 566 | `asset-112-Claude-API---Python.md` | 参考 | Claude API - Python |
| 19,799 | 275 | `asset-123-HTTP-Error-Codes-Reference.md` | 参考 | HTTP 错误码参考 |
| 19,708 | 629 | `asset-115-Tool-Use---Python.md` | 参考 | Tool Use - Python |
| 19,332 | 365 | `asset-078-Cowork-Plugin-Authoring.md` | 参考 | Cowork 插件编写：从零建插件，或按组织定制现有插件 |
| 19,067 | 567 | `asset-107-Managed-Agents---Go.md` | 参考 | Managed Agents - Go |
| 19,002 | 210 | `asset-053-asset.md` | 脚本 | Claude Test 脚本：登录/登出与凭据管理（logoutCmd/loadConfig，角色推断为 ct-auth.mjs） |
| 18,900 | 363 | `asset-102-Claude-API---C.md` | 参考 | Claude API - C#：命名空间与示例 |
| 18,429 | 343 | `asset-091-asset.txt` | 脚本 | lib/source-storybook.mjs：解析 storybook-static/index.json 并配对 story 名 |
| 18,007 | 316 | `asset-080-asset.txt` | 脚本 | 分类调色板校验（JS 版）：与 asset-081 同源 |
| 17,026 | 446 | `asset-110-Managed-Agents---Java.md` | 参考 | Managed Agents - Java |
| 16,553 | 343 | `asset-168-run-skill-generator.md` | 技能 | run-skill-generator 技能：生成/改进 run-<unit> 技能（教 agent 如何构建、启动、驱动本项目） |
| 16,387 | 1 | `asset-068-asset.txt` | 数据 | 固定的 @playwright/mcp 客户端可见工具清单快照（单行 JSON） |
| 16,294 | 296 | `asset-096-asset.md` | 脚本 | preview-rebuild.mjs：单组件 preview 的快速重编译（内循环） |
| 16,121 | 339 | `asset-128-Hillclimb-state-schema-v2.md` | 参考 | Hillclimb state schema v2：state.json 字段定义 |
| 15,993 | 149 | `asset-144-Claude-Model-Catalog.md` | 参考 | Claude Model Catalog：精确 model ID 清单（含 claude-opus-4-5/4-6/4-7、claude-haiku-4-5、claude-mythos-preview 等） |
| 15,869 | 247 | `asset-158-whiteboard.md` | 技能 | whiteboard（solo 变体）：共享草图画布；用户画完点 Publish，本会话被唤醒后读板并画回去 |
| 15,829 | 259 | `asset-092-asset.txt` | 脚本 | lib/story-imports.mjs：preview 编译期的 story 模块解析策略（设计为可 fork） |
| 15,785 | 306 | `asset-081-thresholds.md` | 参考 | thresholds.md：调色板校验的阈值与用法；对应 Python 版 validate_palette.py |
| 15,723 | 257 | `asset-098-asset.md` | 脚本 | package-capture.mjs：package 形状没有参照图，逐 preview 单独抓图评分 |
| 15,710 | 406 | `asset-153-Claude-API---TypeScript.md` | 参考 | Claude API - TypeScript |
| 15,686 | 326 | `asset-088-asset.txt` | 脚本 | lib/bundle.mjs：esbuild 打成 window.<GLOBAL> 的 IIFE，并写 @ds-bundle 头 |
| 14,601 | 224 | `asset-055-asset.md` | 脚本 | Claude Test 浏览器驱动：wait-text / wait-gone 等命令实现（推断为 ctbrowser.mjs） |
| 14,341 | 357 | `asset-167-Example-Electron-desktop-GUI-app.md` | 参考 | Example: Electron / desktop GUI app：交付物应是 driver 脚本，而不是“npm start 会开窗口”的说明 |
| 14,277 | 162 | `asset-066-asset.txt` | 脚本 | Claude Test 守卫：对会打出密钥的工具调用做校验（namesSecret，推断为 guard.mjs） |
| 14,065 | 164 | `asset-061-asset.txt` | 脚本 | Claude Test hosts 处理：yamlScalar、resolver pin 规则（推断为 hosts.mjs） |
| 13,764 | 237 | `asset-100-asset.md` | 脚本 | lib/remote-diff.mjs：本地新构建 vs 远端 _ds_sync.json 的两分区 diff |
| 13,563 | 443 | `asset-111-Managed-Agents---PHP.md` | 参考 | Managed Agents - PHP |
| 13,548 | 85 | `asset-137-Managed-Agents---Onboarding-Flow.md` | 参考 | Managed Agents - Onboarding Flow |
| 13,432 | 284 | `asset-095-asset.txt` | 脚本 | lib/docs.mjs：组件文档发现与 guidelines 拷贝 |
| 13,375 | 231 | `asset-069-Claude-Test-the-spec-author-background-nobody-is.md` | 技能 | Claude Test 内部技能：后台起草 spec 文件（user-invocable: false、context: fork；含极长 allowed/disallowed-tools 白名单） |
| 13,341 | 76 | `asset-138-Managed-Agents---Overview.md` | 参考 | Managed Agents - Overview |
| 12,912 | 226 | `asset-133-Managed-Agents---Environments-Resources.md` | 参考 | Managed Agents - Environments & Resources |
| 12,688 | 166 | `asset-058-asset.txt` | 脚本 | Claude Test 项目发现：从 dev server 输出推断端口（vite/next/astro 等，推断为 discover.mjs） |
| 12,308 | 267 | `asset-165-verify.md` | 技能 | verify 技能：提交前端到端跑一遍受影响流程，验证行为而非只看测试/类型 |
| 12,123 | 180 | `asset-060-asset.txt` | 脚本 | Claude Test 围栏代理：16 KB 头缓冲、net/tls 转发（推断为 fence-proxy.mjs） |
| 12,043 | 220 | `asset-131-Managed-Agents---Common-Client-Patterns.md` | 参考 | Managed Agents - Common Client Patterns |
| 12,029 | 218 | `asset-087-asset.txt` | 脚本 | lib/common.mjs：纯函数工具（文件系统与字符串） |
| 11,950 | 239 | `asset-108-Claude-API---Java.md` | 参考 | Claude API - Java |
| 11,922 | 255 | `asset-114-Streaming---Python.md` | 参考 | Streaming - Python |
| 11,779 | 312 | `asset-073-asset.txt` | 技能配套 | 决策组件样式：从 workshop-page 模板逐字节切出 |
| 11,626 | 203 | `asset-164-prototype.md` | 技能 | prototype 技能：把想法变成可点开、可点击的单页 Artifact |
| 11,602 | 396 | `asset-077-Component-Schemas.md` | 参考 | 插件组件 schema 参考：skills/agents/commands/hooks 等组件的位置与字段 |
| 11,602 | 179 | `asset-119-Admin-API-Organization-Management.md` | 参考 | Admin API（组织管理） |
| 11,560 | 363 | `asset-116-Managed-Agents---Python.md` | 参考 | Managed Agents - Python |
| 11,362 | 201 | `asset-135-Managed-Agents---Memory-Stores.md` | 参考 | Managed Agents - Memory Stores（beta agent-memory-2026-07-22） |
| 11,321 | 143 | `asset-142-Managed-Agents---Webhooks.md` | 参考 | Managed Agents - Webhooks |
| 11,131 | 123 | `asset-145-Platform-Availability.md` | 参考 | Platform Availability：1P / P-AWS / Bedrock / Vertex / Foundry 的特性矩阵 |
| 11,027 | 389 | `asset-156-Managed-Agents---TypeScript.md` | 参考 | Managed Agents - TypeScript |
| 10,892 | 247 | `asset-075-asset.md` | 技能配套 | artifact-tool body 片段：数据表格模板（含 SLOT: TITLE） |
| 10,800 | 223 | `asset-099-asset.txt` | 脚本 | lib/sync-hashes.mjs：哈希配方的单一来源（_ds_sync.json / sourceKeys） |
| 10,559 | 211 | `asset-076-asset.md` | 技能配套 | artifact-tool body 片段：报告模板 |
| 10,494 | 394 | `asset-117-Managed-Agents---Ruby.md` | 参考 | Managed Agents - Ruby |
| 10,109 | 23 | `asset-042-Plugin-eval-and-skill-doctor---quick-reference.md` | 参考 | claude plugin eval 与 /skill-doctor 速查（24 行）：可用范围、作用、入口 |
| 9,696 | 257 | `asset-103-Claude-API---cURL-Raw-HTTP.md` | 参考 | Claude API - cURL / 原始 HTTP |
| 9,596 | 182 | `asset-094-asset.txt` | 脚本 | lib/previews.mjs：每组件一个 preview .tsx |
| 9,508 | 221 | `asset-154-Streaming---TypeScript.md` | 参考 | Streaming - TypeScript |
| 9,489 | 228 | `asset-109-Tool-Use---Java.md` | 参考 | Tool Use - Java（注解式工具） |
| 9,068 | 156 | `asset-139-Managed-Agents---Scheduled-Deployments.md` | 参考 | Managed Agents - Scheduled Deployments |
| 9,024 | 193 | `asset-079-Reference-palette.md` | 参考 | 参考调色板：数据可视化方法的参考实例，可直接替换为目标品牌取值 |
| 8,814 | 48 | `asset-051-plugin-authoring.md` | 技能 | plugin-authoring 技能：在 Claude Code 里做 mod（pane/band/状态行/toast/hook），可本会话热重载 |
| 8,736 | 101 | `asset-120-Agent-Design-Patterns.md` | 参考 | Agent Design Patterns |
| 8,653 | 369 | `asset-104-Managed-Agents---cURL-Raw-HTTP.md` | 参考 | Managed Agents - cURL / 原始 HTTP |
| 8,462 | 190 | `asset-105-Claude-API---Go.md` | 参考 | Claude API - Go |
| 8,432 | 162 | `asset-090-asset.txt` | 脚本 | lib/css.mjs：令牌文件拷贝、@font-face 抽取、styles.css 生成 |
| 8,377 | 220 | `asset-106-Tool-Use---Go.md` | 参考 | Tool Use - Go |

## 3. 分类

### 3.1 技能（带 `---` frontmatter 的 14 个）

| i | name | 行数 | 字节 | description 摘要（前 ~50 字） | JS 语料里能否找到该 description |
|---|---|---|---|---|---|
| 36 | `artifact-pr-review` | 689 | 42,525 | Create a PR review artifact - a structured review br… | 能（1 个 chunk） |
| 37 | `artifact-pr-review` | 501 | 31,080 | Create a PR review artifact - a structured review br… | 能（1 个 chunk） |
| 39 | `workshop` | 726 | 40,528 | Build a design together with the user, one decision … | 能（1 个 chunk） |
| 47 | `artifact-design` | 89 | 20,946 | Design guidance and fundamentals for Artifacts.… | 能（1 个 chunk） |
| 51 | `plugin-authoring` | 49 | 8,814 | Make a mod: a live pane, band, status line, toast or… | 能（1 个 chunk） |
| 69 | `(无 name:)` | 232 | 13,375 | Internal to Claude Test — drafts spec files in the b… | 找不到 |
| 70 | `(无 name:)` | 499 | 42,953 | Internal to Claude Test — runs the specs in a backgr… | 找不到 |
| 71 | `(无 name:)` | 502 | 59,098 | Check that the web app in this repo still works, wit… | 找不到 |
| 83 | `design-sync` | 127 | 28,225 | Push a React design system to claude.ai/design. This… | 能（1 个 chunk） |
| 158 | `whiteboard` | 248 | 15,869 | Create a whiteboard artifact - a shared sketch canva… | 能（1 个 chunk） |
| 161 | `whiteboard` | 367 | 24,065 | Create a whiteboard artifact - a live sketch canvas … | 能（1 个 chunk） |
| 164 | `prototype` | 204 | 11,626 | Turn an idea into a working proof of concept and pub… | 能（1 个 chunk） |
| 165 | `verify` | 268 | 12,308 | Verify that a code change actually does what it's su… | 能（1 个 chunk） |
| 168 | `run-skill-generator` | 344 | 16,553 | Author or improve the run-<unit> skill - a per-proje… | 能（1 个 chunk） |

**它们和 JS 语料里的 skill 提示词是什么关系：描述重复、正文独有。** 一手证据（[raw/chunks/c1171.js](raw/chunks/c1171.js)）：

- 语料里注册技能时写的是元数据 + 一个取正文的加载器，例如 `getPromptForCommand` 里 `let{SKILL_MD:h}=await On(), g=Hs(h[e]).content.trimStart()`——正文是运行时从 `/$bunfs/root/SKILL-*.md.zst` 解出来的；
- 用每个技能正文中段任取 4 条 60–180 字符的探针去 grep 语料：**全部 0 命中**（asset-158/161/164/165/39/83/36/168 共 32 条探针），而用 frontmatter `description` 的前 70 字符去 grep：**11/14 命中**（未命中的 3 个是 Claude Test 内部技能 69/70/71，它们不在 c1171.js 的技能表里）。
- 也就是说：早前语料分析看到的 skill 文本只是**注册元数据**（name/menuDescription/description/whenToUse/argumentHint/allowed-tools），真正的技能正文（几十到几百 KB 的 SKILL.md）只存在于这些压缩资源里——这是本次抽取补上的最大一块。
- 另有非 frontmatter 的技能文档：asset-166（Plugin eval，514 行）、asset-118（Building LLM-Powered Applications，596 行）等以 `#` 开头的技能体，同样只此一份。

### 3.2 参考文档

- 参考类共 **66** 个，占 Claude 侧字节的绝大部分。超过 100 KB 的只有 2 个：Model Migration Guide（317,800 B / 2254 行，迁移步骤 + per-SDK 语法 + 破坏性变更，路由 `/claude-api migrate`）与 Building LLM-Powered Applications with Claude（100,774 B / 596 行，先选“面”再写代码，正文里有 `{{FABLE_NAME}}`/`{{OPUS_NAME}}` 模板占位）；紧随其后是 Plugin eval 参考（80,310 B）、Hill-Climbing on an Eval（69,156 B）、Storybook source shape（69,242 B）、Cost Optimization（58,092 B）、Building an Eval（55,191 B）。
- Managed Agents 家族（**20** 篇 = 13 篇同名文档 + 7 篇语言/绑定文档）：Overview / Core Concepts / Endpoint Reference / Environments & Resources / Tools & Skills / Events & Steering / Multiagent Sessions / Memory Stores（`agent-memory-2026-07-22` beta）/ Scheduled Deployments / Self-Hosted Sandboxes / Webhooks / Common Client Patterns / Onboarding Flow，外加 cURL、Go、Java、PHP、Python、Ruby、TypeScript 七篇绑定 README（见 §5 的名称映射说明）。
- 按标题统计的其余脉络：`Claude API - *` 6 篇（C#/Go/Java/Python/TypeScript/cURL）、`Tool Use *` 5 篇（概念 + 4 语言）、`Streaming *` 2 篇（Python/TypeScript）、`Example: *` 1 篇（Electron）。
- 评测与成本主题（8 篇）：Building an Eval（55 KB）、Eval health checklist（27.9 KB）、Hill-Climbing on an Eval（69.2 KB）、Hillclimb state schema v2（16.1 KB）、Cost Optimization（58.1 KB）、Cost-reduction search（31.7 KB）、Prompt Audit（48.9 KB）、Prompt Caching（33.0 KB）。
- 迁移与兼容主题：Model Migration Guide（317.8 KB）、Preserved Thinking 两篇（64.0 KB + 39.7 KB）+ 两个可执行探针（`prefix_diff.py` 94 KB、`drop_block_probe.py` 66.6 KB）、Upgrading the anthropic Python SDK 0.x→1.x（29.1 KB）。
- 元数据类：Claude Model Catalog（16.0 KB，150 行，给的都是精确 model ID：`claude-opus-4-5`/`4-6`/`4-7`、`claude-haiku-4-5`、`claude-mythos-preview` 等）、Platform Availability（11.1 KB，1P/P-AWS/Bedrock/Vertex/Foundry 矩阵）、Live Documentation Sources（23.0 KB）、HTTP Error Codes（19.8 KB）、Admin API（11.6 KB）、Anthropic CLI `ant`（22.2 KB）、Agent Design Patterns（8.7 KB）、Tool Use Concepts（44.2 KB）。

### 3.3 前端 / HTML 资源

| i | 字节 | 行 | 特征串 | 说明 |
|---|---|---|---|---|
| 157 | 96,305 | 1770 | `<title><!-- SLOT: TITLE —` | 自包含 HTML 模板，槽位化（推断为 artifact/plan 类模板；未细读全文） |
| 159 | 154,540 | 2711 | `<title>Whiteboard</title>` + Google Fonts 外链 | whiteboard（solo/board.mjs 组合）的页面模板 |
| 162 | 329,237 | 4555 | `<title>Whiteboard</title>` + `@ant/cds` 令牌表 | whiteboard（live/merge-state 组合）的页面模板 |
| 40 | 117,526 | 2963 | `name: workshop`（HTML 注释 frontmatter） | workshop 工件模板，{{TITLE}} 等四个机械填充槽 |
| 41 | 127,802 | 3095 | `name: workshop-page` | 直出 HTML 版 workshop 模板 + 发布前结构校验规则 |
| 46 | 38,063 | 1088 | `name: plan` | plan 工件模板（PLAN_TEMPLATE） |
| 38 | 88,532 | 1749 | `Artifact-tool body fragment` | PR 评审的 body 片段（无 doctype 包裹） |
| 75 | 10,892 | 248 | `<!-- SLOT: TITLE -->Data table` | artifact body 片段：数据表 |
| 76 | 10,559 | 212 | `<!-- SLOT: TITLE -->Report` | artifact body 片段：报告 |

配套脚本/样式（同样只此一份）：asset-072（workshop decisions 脚本，65.6 KB / 1548 行）、asset-073（决策组件样式，11.8 KB）、asset-074（CDS 令牌块，28.2 KB）。

### 3.4 vendored 第三方库

| i | 字节 | 库 | 版本 | 来源 / 许可线索（文件内首几行） | 二进制里的名字 |
|---|---|---|---|---|---|
| 48 | 3,566,058 | mermaid | 11.16.1 | 加载器里拼的 banner：`/*! mermaid v11.16.1 · MIT · Copyright (c) 2014 - 2022 Knut Sveidqvist */`；bundle 内另含 DOMPurify 3.4.0（Apache-2.0 + MPL-2.0）与 lodash（MIT）的许可声明 | `/$bunfs/root/mermaid.min.js` |
| 35 | 593,163 | highlight.js | 11.11.1 | 首行注明由 `scripts/generate-hljs-browser-bundle.ts` 生成；`BSD 3-Clause License, Copyright (c) 2006, Ivan Sagalaev`；186 种语法 | `/$bunfs/root/hljsBundle.generated.min.js` |
| 63 | 167,048 | public suffix list | 2026-09-08 | 单行 JSON：`{"source":"https://publicsuffix.org/list/public_suffix_list.dat","license":"MPL-2.0","version":"2026-09-08_12-18-37_UTC"…}` | `/$bunfs/root/psl-data.json-ffeefa5c.txt.zst` |
| 34 | 208,522 | Chart.js | 4.5.1 | banner：`Chart.js v4.5.1 … (c) 2025 Chart.js Contributors … Released under the MIT License` | `/$bunfs/root/chart.umd.min.js` |

四个都是**未改写的上游打包**（保留 banner 与许可声明），用途可从加载器看出：mermaid/hljs/chart 由 `loadMermaidBundleJs` / `loadHljsBundleJs` / `loadChartBundleJs` 按需读入 Artifact 渲染；PSL 供 Claude Test 的围栏代理判断主机归属。这一版没有发现 ESLint 或其他 linter 的 vendored 副本（在 Claude 侧资源里 grep `eslint` 只命中 bun 区的 asset-008/013 包名表与 polyfill）。

### 3.5 类型声明与测试基建

- **asset-044（573,702 B / 14,915 行）= `claude-code.d.ts`**，函数钩子插件 API 的完整 TypeScript 声明（头部自述 EARLY ACCESS、由引擎写在 `<mod>/.claude-plugin/types/claude-code/index.d.ts`）。该主题**已由 [REPORT-plugin-api.md](verify/REPORT-plugin-api.md)（450 行）专门分析**（worker 沙箱、136 个 hook 点、内置 10 个插件等），本文只做一句交叉引用，不重复分析；同一主题的其余资源为 asset-045（`plugin test` 套件）、asset-050（长文，145 行）、asset-051（plugin-authoring 技能，49 行）。
- 测试基建：Claude Test 插件一整套（按内容命中 **16** 个已抽取文件：52,53,54,55,56,57,59,62,64,65,66,67,69,70,71,91；含 3 个技能 + CLI/browser/config/discover/guard/hosts/proxy 等脚本 + `spec-format`），design-sync 转换器一整套（命中 **17** 个：82–88,90,92,93,94,96,97,98,99,100,101；加载器声明的 `SKILL_FILES` 共 24 项，其余未落盘）。

### 3.6 插件运行时家族（速查）

判定口径：按文件内容里的关键字命中（因此一个文件可能同时属于两个家族，例如 040/041 既含 workshop 也提到 whiteboard）。
- 白板（9 个：40,41,72,158,159,160,161,162,163）：两个变体各 3 个文件——SKILL.md + template.html + helper（`board.mjs` / `merge-state.mjs`）；
- workshop / plan（8 个：39,40,41,46,72,73,74,162）：模板 + decisions 脚本 + 样式/令牌；
- design-sync（17 个：82–88,90,92,93,94,96,97,98,99,100,101）：技能 + 转换器脚本 + 两份 source shape 文档 + `Where things are` 地图；
- Claude Test（16 个：见 §3.5）；
- plugin eval / skill-doctor（2 个：42,166）：速查 + 514 行参考；
- 函数钩子（3 个：44,50,51）：.d.ts + 长文 + 技能。

注意这些家族在二进制里都是**按插件打包在一起**的（帧序与加载器的 `SKILL_FILES` 对象一一对应），可用它反推“哪几个资源属于同一个插件”。

## 4. 对之前结论的修正

- 早前 [README.md:312](README.md#L312) 写“**231 个非 chunk 资源（`SKILL-*.md[.zst]` 等）未逐个提取**”。现在：**168/169 个 zstd 帧已全部尝试解压，其中 Claude 侧 135 个全部成功并落盘**（9.91 MB）。
- “231”这个量级可以复现但不能精确对齐：本文用 `/$bunfs/root/[A-Za-z0-9._@+-]+` 重扫名字表得到非 chunk 条目 **229–230** 个（取决于结尾字节切法；字符串在表里不是 NUL 结尾，而是紧邻下一个条目），chunk 条目约 2169 个。差额 1–2 条无法确认是哪两条。
- 因此覆盖率应这样表述：**Claude 侧名字表里约 230 个非 chunk 资源中，135 个（≈59%）已作为 zstd 帧落盘**；剩下的不是“没找到”，而是三类：(a) 未压缩存储的兄弟文件——已在帧间间隙里实证到 2 个 WOFF2 字体、`audio-capture.node`（444 KB Mach-O）、≥6 段 Mach-O、≥4 个设计/幻灯片提示词文档、10 KB autonomous-loop 提示词，合计 4,721,613 字节，**但本轮没有落盘**；(b) 安装布局名（如 `/$bunfs/root/template.html`、`/board.mjs` 这类无 hash 的名字，与 hash 名的 `.zst` 是同一份内容的两种写法）；(c) `.node` / `.woff2` / `.ts` / `.tsx` 这类本来就不是文本的资源。
- 另一处需要纠正的直觉：**名字表的 `.zst` 后缀不能当压缩判据**。带 `.zst` 的非 chunk 名字只有 80 个，却有 135 个 Claude 侧帧；`mermaid.min.js`、`chart.umd.min.js`、`hljsBundle.generated.min.js` 都是无 `.zst` 名但确为 zstd 帧。
- 之前把名字表位置记作“0xd87e9b0 附近”；实测该处只是名字表**尾部**（`/$bunfs/root/drop_block_probe-…` 到 `template-eg8004mh.md`），整张表从 `0xd85b83d` 起、到 `0xd87eac9` 结束，并且**被 chunk 名占满前半段**。

## 5. 未验证 / 读不到

- **1 个帧解压失败**（index 33，Bun 区）：见 §1.3。无法判定它是真资源还是魔数误命中；可用“带字典的 zstd 解码”或“Bun 的资产清单结构”继续验证，本轮**未验证**。
- **名字与内容的对应关系不精确**。我们按偏移聚类抽取，不靠名字表映射。可确认的只有 11 条：
  - 白板 6 条（一手证据：二进制内加载器源码 `chunk-zqxb1n4f.js` / `chunk-4atxqh9y.js` 与 [raw/chunks/c1171.js](raw/chunks/c1171.js) 里的 `Et()==="live"?Dn():Mn()`）——`SKILL-7f2555bf.md.zst`+`template.html-af756034.txt.zst`+`board.mjs-0bf8864f.txt.zst` = asset-158/159/160（solo，助手文件自称 `board.mjs`），`SKILL-8e6c8b5d.md.zst`+`template.html-94ff54c0.txt.zst`+`merge-state.mjs-49ddf23e.txt.zst` = asset-161/162/163（live，引用 `merge-state.mjs`）；
  - mermaid / highlight.js / Chart.js / PSL / `claude-code.d.ts` 5 条（内容 banner 或加载器名字直配，见 §3.4 与 §3.5）。
- **其余约 124 个帧只能给出区间，不能钉死名字**。可核对的规律是“名字序 = 帧序”的单调关系：用 16 个能靠内容认出的锚点（chart/hljs/plugin-eval-quickref/claude-code.d.ts/mermaid/PSL/cost-optimization/build-eval/eval-hillclimb/model-migration/preserved-thinking/白板 4 个/plugin-eval）做检查，名字表下标与帧序号的差从 −33 单调漂到 +52，即**两列同序但条目数不同**（名字多于帧），所以严格 1:1 对齐只能通过 80/135（59%）的类型抽查，不能作为映射依据。
- **未细读**的文件：asset-045（拼接的插件测试套件源码，仅读了首尾）、asset-157（96 KB 模板，仅读了头部槽位）、asset-072（1548 行 decisions 脚本）、asset-093（683 行 design-sync 地图）等；表内摘要只覆盖开头若干行，未做全文语义分析。
- **Claude Test 脚本与名字的对应是推断**（§2 表中标“推断为 X.mjs”的 7 条）：依据是内容特征（`logoutCmd`、`ownPorts`、`installTools`、`parseSkillMd`、`namesSecret`、`RC_FILE`、`vite|next|astro` 端口启发）与加载器列出的 27 个文件名，未逐一对齐 hash。
- **bun 区 33 个资源只做了首行级识别**（错误页 CSS、polyfill、补全、包名表等），未逐一确认上游来源与版本。
- 名字表里的 `sourcemap.json` 之类条目是我的正则切出的假名（`sourcemap.js` + 后续字节），不是独立资源；正文未采用。

## 附录 A：可核对的命令与特征串

- 帧数：`python3 -c "import re;d=open('/Users/yezhipeng/.local/share/claude/versions/2.1.287','rb').read();print(len(re.findall(rb'\x28\xb5\x2f\xfd',d)))"` → `169`
- 名字表：`0xd85b83d`–`0xd87eac9`；非 chunk 段从最后一个 `chunk-` 名字之后开始（本机实测起点 `0xd87e5b0` 之前）
- 关键特征串：`claude-opus-4-7`（asset-144）、`{{FABLE_NAME}}`（asset-118）、`name: workshop-page`（asset-041）、`EARLY ACCESS`（asset-044）、`agent-memory-2026-07-22`（asset-135）、`wOF2`（帧 k=7 后的字体间隙）、`@rpath/audio-capture.node`（帧 k=10 后的 444 KB 间隙）
- 白板映射：`grep -ao 'var [A-Za-z]*="/\$bunfs/root/SKILL-[0-9a-z]*\.md\.zst"' binary` 可复现；`chunk-zqxb1n4f.js` = solo、`chunk-4atxqh9y.js` = live

## 附录 B：本次使用的判定口径

- 一手证据：文件内容、二进制偏移与字节、加载器源码、`zstd` CLI 实验；
- 推断：区域划分阈值、家族归属、Claude Test 脚本角色、asset-157/045 的用途；
- 未找到：ESLint vendored 副本（Claude 侧）；`verify/REPORT-plugin-api.md`（不存在，故 §3.5 不引用而是首手摘要）；失败帧的真实身份。

