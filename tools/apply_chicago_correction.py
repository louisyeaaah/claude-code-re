#!/usr/bin/env python3
"""把 §13（chicago 更正）追加进 REPORT-ghidra 的中英版，并修正 §10 里的过时推断。"""
import pathlib

ZH_SEC = pathlib.Path("work/chicago-zh.md").read_text(encoding="utf-8")
EN_SEC = pathlib.Path("work/chicago-en.md").read_text(encoding="utf-8")

OLD_ZH = '> 仍未验证：这些方法与 JS 侧调用点的对应关系（JS 语料里搜不到同名字符串，说明经 ObjC runtime 动态桥接），以及 `chicagoRegister/Unregister/NotifyExpectedEscapeMethod` 的确切用途——**推断**与"中断/逃生"机制有关。'
NEW_ZH = ('> **2026-10-14 更正**：上面两个"未验证"已被 §13 推翻/落实——`chicago*` 是 Swift 侧命名前缀，'
          'N-API 注册后 JS 侧看到的是 `computerUse.<命名空间>.<方法>`（所以 JS 里 grep 不到 `chicago` 是设计如此，不是动态桥接）；'
          'Escape 三兄弟是一个 **CGEventTap**（拦截用户的 Escape 中断键），详见 §13。')

OLD_EN = ('> Still not verified: how these methods map to JS call sites (the JS corpus has no matching strings, suggesting an ObjC runtime bridge), '
          'and the exact purpose of `chicagoRegister/Unregister/NotifyExpectedEscapeMethod` — **inferred** to relate to an escape/interrupt mechanism.')
NEW_EN = ('> **Corrected 2026-10-14**: both "not verified" items above are resolved or overturned in §13 — `chicago*` is a Swift-side naming prefix, '
          'and after N-API registration JS sees `computerUse.<namespace>.<method>` (so finding no `chicago` string in JS is by design, not dynamic bridging); '
          'the escape trio is a **CGEventTap** intercepting the user\'s Escape interrupt key.')

for path, sec, old, new in (("verify/REPORT-ghidra.md", ZH_SEC, OLD_ZH, NEW_ZH),
                            ("verify/REPORT-ghidra.en.md", EN_SEC, OLD_EN, NEW_EN)):
    p = pathlib.Path(path)
    s = p.read_text(encoding="utf-8")
    if "## 13." in s:
        print("已有 §13，跳过", path)
        continue
    if old in s:
        s = s.replace(old, new)
        print("已修正 §10 过时句:", path)
    else:
        print("!! §10 旧句未匹配（可能措辞不同）:", path)
    p.write_text(s.rstrip() + "\n" + sec, encoding="utf-8")
    print("已追加 §13:", path)
