# Claude Code v2.1.287 的提示词写法：可量化的一手观察

> 方法：`raw/census.py` 从 4060 个内嵌 JS chunk 里抽出全部字符串/模板字面量（476,109 条），
> 过滤出「≥80 字符、含空格与换行、含 you/your/user/tool/the 等指代词、去重、剔除许可证头」的 772 条提示词型字面量（2.67 MB）后统计。
> 复现：`cd raw && python3 census.py`（去重版脚本见本文件末尾附录）。

## 1. 体量分布

| 指标 | 数值 |
|---|---|
| 提示词型字面量（去重后） | **772 条**，合计 2.67 MB |
| 长度中位数 | **552 字符** |
| p75 / p90 / p99 | 1,722 / 6,401 / 48,681 字符 |
| 全部字符串字面量 | 476,109 条（含代码里的短串） |

结论：不是"一个大提示词"，而是**几百个几百字的小块**。中位数 552 字符意味着大量提示词比一屏还短——它们靠**装配**而不是靠长度生效。

## 2. 指令标记的分布（计数 = 出现次数 / 含该词的字面量数）

| 标记 | 次数 | 文档数 | 解读 |
|---|---|---|---|
| `e.g.` | 164 | 82 | 最高频——**每条规则几乎都配例子** |
| `instead of` | 111 | 37 | 用"替代方案"而非"禁止"来纠偏 |
| `Do not` | 94 | 65 | 主要否定形式 |
| `unless` | 92 | 68 | 几乎每条禁令都带**例外条件** |
| `required` | 89 | 44 | 参数/条件约束 |
| `If you` | 85 | 62 | 条件—动作句式 |
| `Never` / `NEVER` | 63 / 35 | 44 / 18 | 大写 NEVER 只留给极少数红线 |
| `only when` | 56 | 40 | 收紧适用范围 |
| `Don't` | 49 | 30 | 口语化否定 |
| `do NOT` | 35 | 25 | 局部强调（大小写混排） |
| `MUST` | 34 | 29 | 义务型，少于否定型 |
| `Always` / `ALWAYS` | 24 / 12 | 18 / 12 | 少于否定型 |
| `for example` | 32 | 18 | 例子的另一种写法 |
| `IMPORTANT:` | 21 | 17 | 段落级强调 |
| `Prefer` | 19 | 18 | 表达偏好而非禁令 |
| `Avoid` | 15 | 15 | 同上 |
| `CRITICAL` | 14 | 13 | 少见于系统提示词，多见于 skill/命令 |

**读法**：`e.g.`(164) + `instead of`(111) + `unless`(92) 三项都高于 `NEVER`(35)。这套提示词的写法偏向**"给条件、给替代、给例子"**，而不是靠大写禁令压制。大写 `NEVER` 留给了真正的红线（把整份建议文档交给你的那种级别）。

## 3. 七种规则句式（附原文样本）

### ① 禁令 + 例外（unless）
```
Do not proceed unless you expected them.
No model turn unless the plugin asks for one.
```
> 只写"不要做 X"会让模型在边界情况下僵住；补一句 `unless ...` 就交代了什么时候可以。

### ② 禁止 + 替代（instead of / rather than）
```
When true, the sandbox runtime deterministically denies hosts not in allowedDomains instead of prompting.
Prefer the Edit tool for modifying existing files — it only sends the diff.
Prefer to create a new commit rather than amending an existing commit.
```
> 与"不要做 X"相比，`instead of / rather than` 直接把模型的下一步动作指定了，**不留自行发挥的空间**。

### ③ 条件—动作（If you …）
```
If you did not check, say you did not check.
If you find yourself repeating what a subagent is doing, you should not have spawned it.
If you told the user this was saved or remembered, tell them plainly that it was not.
```
> 句式高度一致：可观测的触发条件（自己做过什么、发现什么）+ 立刻可执行的动作。这类句子可以逐条进测试集。

### ④ 不要写文档式红线（NEVER，大写）
```
- NEVER create documentation files (*.md) ...
- NEVER invoke `grep` or `rg` as a Bash command.
- NEVER run destructive git commands (push --force, reset --hard, checkout .)
- NEVER create files unless they're absolutely necessary for achieving your goal.
- The assistant NEVER uses the <shutdown> tool or even mentions the possibility of ending the conversation.
```
> 全文只有 ~18 条字面量用到大写 NEVER，且每条都对应一个真实高频事故（乱建 md、绕过专用工具、破坏性 git、自说自话地结束会话）。

### ⑤ 偏好排序（Prefer / Avoid）
```
Prefer choices whenever the likely answers can be listed.
Prefer modelUsage for token/cost accounting.
Prefer denying the enclosing directories.
- Prefer the dedicated file/search tools over shell commands when one fits.
```
> 用"优先 A 于 B"代替"禁止 B"，保留合理例外，也更容易和工具实现一致。

### ⑥ 冲突裁决（X wins）
```
Managed, --settings and user settings choose the level (the most restrictive wins); project and local settings can only lower it, never raise it.
An explicit value always wins.
Where these rules conflict with more general communication or formatting guidance elsewhere in your instructions, these rules win.
```
> 多条规则并存时必然冲突，**显式写出优先级**比让模型猜要便宜得多。这条模式在权限系统里已经被工程化（`first-wins` / `merge` 之类），在提示词里也应照做。

### ⑦ 先给结论、再给做法（Lead with …）
```
Report what actually happened, not what you intended.
Lead with the outcome. Your first sentence after finishing should answer "what happened" ...
Report outcomes faithfully: if tests fail, say so with the output; if a step was skipped, say that ...
```
> 面向输出的规则一律先定义**成品的第一个句子长什么样**，再讲过程纪律。

## 4. 结构套路（非句式，但同样可复用）

1. **小节标题即指令**：`# Executing actions with care`、`# Reporting outcomes`、`# Delivering work`——标题本身说明这一节的判据。
2. **列表项长度受控**：多数条目 1~3 句；需要长篇解释时才给 3.6 KB 的整节（`# Executing actions with care`），且内部仍然是清单结构。
3. **例子优先于形容**：风险不讲"危险"，讲 `force-push / git reset --hard / 改 CI`；口径不讲"要准确"，讲 `if tests fail, say so with the output`。
4. **反面案例成对出现**：`text like "Let me read the file:" ... should just be "Let me read the file." with a period.`——正反例写在一起。
5. **同一机制备多档文案**：system-reminder 说明 3 档、沟通规则 3 档（终端 / focus / 特定客户端），按载体切换而不是写一篇万能长文（见 [`01-system-prompt.md`](01-system-prompt.md)）。
6. **动态内容只讲"这一轮"**：静态块用 `NEVER / always`，动态块用 `this session / right now / the user has ... enabled`，用措辞把有效期说清楚。
7. **占位符化**：大量原文是 `${toolName}` / `${language}` / `${n}` 模板，同一段文案复用到不同工具/形态（如 TodoWrite 与 TaskCreate 共用一句话），减少文案漂移。

## 5. 未验证 / 口径说明

- 统计对象是**内嵌的字符串字面量**，其中包含工具参数说明、配置项文档、错误提示等非"提示词"文本；772 条是过滤后的近似集合，不是精确的"发给模型的提示词"清单。
- 计数受去重口径影响（同一段文案出现在多个 chunk 会被去重），绝对数字只用于比较相对频率，不宜当作"系统提示词里有 94 个 Do not"。
- 未做跨版本对比（本机另有 2.1.272~2.1.286 五个版本文件），写法是否在版本间演化未验证。

## 附录：复现脚本要点

`raw/census.py`：状态机扫描（处理 `'`/`"`/反引号模板字面量与 `${}` 嵌套、注释）→ 收集字面量 → 过滤（≥80 字符、含空格与换行、含指代词、剔除许可证头、按前 120 字符去重）→ 计数标记与长度分位。
