> English version. 中文原版：[REPORT-plugin-api.md](REPORT-plugin-api.md)

# Claude Code v2.1.287 · function hooks (the plugin API)

**Subject**: the function hooks subsystem in v2.1.287 (`GIT_SHA:"3c446a1b98aceb99a6cdee0f84a8bea42f4a8937"`, `BUILD_TIME:"2026-10-01T16:02:06Z"`) — an API for writing plugins in TS/JS that hook the main loop and draw UI.

**Sources**: `work/assets/asset-044-asset.txt` (14,914 lines; the API's full TypeScript declarations, headed `// Claude Code function hooks: the plugin API's TypeScript declarations.`) / `asset-045-asset.txt` (2,232 lines; the `claude plugin test` kit's source) / `asset-050-Function-hooks-the-long-form.md` (first-party long form) / `asset-051-plugin-authoring.md` (first-party SKILL.md) / `raw/chunks2/*.js` (2,174 modules) / `extracted/06-quirks.md` (an earlier pass, "the 06 doc" below). Citations: `work/assets/asset-044-asset.txt:4791` (line) or `raw/chunks2/0374__chunk-mphp7acd.js@1268258` (byte offset, located with `grep -b -o`). Evidence grades: verbatim = bytes actually read; inferred = from symbol names/call sites; not found = explicitly absent.---

## 0. Executive summary

1. **This is a genuinely wired subsystem, not types only.** A plugin module runs in its own Bun Worker (`raw/chunks2/0374__chunk-mphp7acd.js@1268258`), with the worker half in `raw/chunks2/0150__x-thepluginsenvironmentwasunloaded.js`. The rollout switch `tengu_plugin_hooks_modules` **defaults on** (`raw/chunks2/0329__chunk-110gm4an.js:24`, verbatim `var mUt=!0;`).
2. **The binary already ships 10 built-in plugins written against this API** (`raw/chunks2/1651…1661`; 6 export `registerPlugin`), including `cc-plugin-claude-test`, `cc-plugin-telemetry`, `cc-plugin-sec-default`, `cc-plugin-mermaid`, `cc-plugin-agents-md`, `cc-plugin-responsive-mode`, `cc-plugin-mods-guide`.
3. **The sandbox is VM-level and verifiable**: a module is evaluated as a `vm.SourceTextModule` inside `vm.createContext(nullProto, {codeGeneration:{strings:!1,wasm:!1}})`, with exactly 13 globals, and `import()` is refused by a runtime-injected `importModuleDynamically` — matching the type declaration's "no DOM, no Node" paragraph point by point.
4. **The hook-point count is an order of magnitude past the 06 doc's 33**: 33 is only the settings-hook `classic.*` band; this build has **136** name-hookable events (43 engine + 33 classic + 60 `$` calls).
5. **`$.ui.mount` is not on a plugin's `$`, it is on the test's `$`** (`asset-044-asset.txt:14039-14054`); **`plugin test` is early access and hidden by default** (`earlyAccess:"hooksModules"`, `raw/chunks2/0766__chunk-ywkfhf88.js:1`), and modules stay held in an untrusted workspace until the person accepts trust (`raw/chunks2/1245__chunk-f5w4pbxy.js@9695`).
6. **The gap in the 06 doc §1.6 is now closed**: it said the worker's IPC protocol, lifecycle and timeout policy were **not found** (`extracted/06-quirks.md:581`); this pass found both halves (§5.2).

---

## 1. What this API is

### 1.1 What a mod is made of

The header (from `asset-044-asset.txt:1-7`, abridged):

```
// Claude Code function hooks: the plugin API's TypeScript declarations.
//
// EARLY ACCESS: this surface may change between releases without notice.
// Written by the engine each time it loads a mod from a folder the person
// owns, beside that mod as .claude-plugin/types/claude-code/index.d.ts; ...
```

The three-file shape an author sees (`asset-051-plugin-authoring.md:6-10`):

```
WHERE TO WRITE IT. Write each mod in its own child folder of `${CLAUDE_DEV_MODS_DIR}`: `${CLAUDE_DEV_MODS_DIR}/<mod-name>/`, three files written directly:

- `.claude-plugin/plugin.json`: `{ "name": "<mod-name>", "version": "0.1.0", "description": "<one line>" }`
- `hooks/hooks.json`: `{ "modules": ["./register.tsx"] }`, one path, relative to that file
- `hooks/register.tsx` (or `.ts`): the hooks module, `export const register: Register = (on, options) => { ... }`, the type imported from `'claude-code'`
```

A plugin has **exactly one** hooks module, exporting `register(on, options)` (`asset-050-Function-hooks-the-long-form.md:14`); using `$.state` adds a fourth file, the `types/index.d.ts` contract (`asset-051:12`). **The test fixture confirms the shape**: when `claude plugin test` fabricates a plugin it writes those three files (`ue(e,n,r)` around `raw/chunks2/0769__x-CHILD_ARGV_LENGTH.js@13818`) — `plugin.json` holds only `{"name":"…"}`, `hooks.json` holds `{"modules":["./register.js"]}`, and the third file holds `export function register(on) { … }`.

### 1.2 What the manifests look like

**`hooks/hooks.json`** — the JS-side zod schema (`raw/chunks2/0055__chunk-hrhfcbdv.js@131757`) gives four fields and two hard rules verbatim:

```
hooks:    "The hooks provided by the plugin, in the same format as the one used for settings"
modules:  max 1 — "hooks.json `modules` names one hooks module per plugin; a second entry is refused"
          "The hooks module: one path, relative to this hooks.json, of a module exporting register(on).
           The module, and every file it imports from the plugin, is named like code (...)
           and is an ES module whatever its suffix. What it hooks and calls is read from its source
           before it loads; `claude plugin validate` shows the result."
surface:  'hooks.json `surface` is gone: name the module in the Client element, `Client({ module: "./board.tsx", key })`'
```

The refine rule: ``"hooks.json must have `hooks` (the hook matchers) or `modules` (hooks modules), or both"``.

**`plugin.json`** fields (`asset-050:62`, `asset-051:8/12`, `asset-044-asset.txt:7153-7165`): `name`, `version`, `description`, `types` (a self-contained `.d.ts` contract for a noun the plugin adds to `$`), `dependencies` (a dependency's contract is laid into `.claude-plugin/types/<plugin>/index.d.ts`), `userConfig` (options the person fills in), `hooks`, `mcpServers`, `evals`. Where options land and how they are checked (`:7153-7160`): the fields the manifest's `userConfig` declares, defaults filled in, stored in settings.json `pluginConfigs[<plugin>].options` (sensitive ones in secure storage), validated against the declared `type` **before the module loads**; a required field with no value fails the load, naming the field.

### 1.3 How a hooks module is loaded

**(a) The runtime environment is a separate Worker.** The host-side factory, verbatim:

```js
// raw/chunks2/0374__chunk-mphp7acd.js@1268258
function geo(){ let e=new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT*vts),
                    n=new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT*Ets);
  return { worker: new Worker(Nvt(), Ovt(e,n)), stamp: new Int32Array(e), marks: new Int32Array(n) } }
```

The worker URL comes from `Nvt()` (`@1267204`): packaged, it is the build constant `HOOKS_WORKER_URL` (`/$bunfs/root/src/plugins/functionHooks/hooks-worker/hooks-worker.js`); in development it degrades to `new URL("../../../hooks-worker/hooks-worker.ts", import.meta.url)`. The log line is verbatim ``"hooks worker spawned (one for every plugin)"`` (`@1728382`) — **one worker per process, serving every plugin**.

**(b) Eight allowed file suffixes** (`raw/chunks2/0055__chunk-hrhfcbdv.js@75380`): `pnr={".ts":"ts",".tsx":"tsx",".jsx":"jsx",".js":"js",".mjs":"js",".cjs":"js",".mts":"ts",".cts":"ts"}`, `var oZe=Object.keys(pnr);` — the key set is verbatim `.ts .tsx .jsx .js .mjs .cjs .mts .cts`, matching the prose (`asset-044-asset.txt:19-21`): "The module, and every file it imports from the plugin, is named `.ts`, `.tsx`, `.jsx`, `.js`, `.mjs`, `.cjs`, `.mts` or `.cts` (a file named otherwise is not loaded)".

**(c) An ES module; no `require`; `import()` does not load** (`asset-044-asset.txt:21-23`):

```
// otherwise is not loaded) and is an ES module whatever its suffix: there
// is no `require`. A file of the plugin is imported with an `import`
// declaration. A module holding `import()` does not load.
```

Two independent enforcements: a **source scan**, `var UIe=/\bimport\s*\(/;` in `raw/chunks2/0374__chunk-mphp7acd.js` (run over the module and every file it links); and a **runtime backstop**, an always-throwing `importModuleDynamically` injected at `raw/chunks2/0146__chunk-hhxhpvxp.js@152175`:

```
'import() is not available: a hooks module imports its own files ' +
  'with an import declaration',
```

evaluation then goes through `new Kn.SourceTextModule(vJn,{context:o,identifier:S7e,importModuleDynamically:c})` (`0146@152847`).

**(d) Sandbox constraints, verified one by one.**

| The claim | Where | Verification |
|---|---|---|
| no DOM, no Node | `:19`, `:13706-13707` | ✅ Enforced. `raw/chunks2/0146__chunk-hhxhpvxp.js@206807-206945`: `var Lf=Object.freeze({strings:!1,wasm:!1}); var Ff=Object.freeze({codeGeneration:Lf}); function mzo(){let e=ip(),t=$f.createContext(e,Ff); …}`, and `ip=()=>Object.create(null)` (`0146@158956`) — the context is a null-prototype object the host fills with just 13 names |
| no code generation (`eval`/`new Function` throw; no `WebAssembly`) | `:13707-13709` | ✅ Enforced — it is exactly those two `vm` options, `codeGeneration:{strings:!1,wasm:!1}` |
| the globals are only `h`, `Fragment`, the JSX namespace and web APIs | `:15-19`, `:13714-13838` | ✅ Exact match. The bootstrap source in `0146` calls `define('…')` exactly 13 times: `AbortSignal, AbortController, TextEncoder, TextDecoder, URL, URLSearchParams, atob, btoa, structuredClone, crypto, performance, h, Fragment` |
| no timers (hooks wait on `$.clock`, a surface module on `surface.every`) | `:13711-13712` | ✅ None of the 13 names is `setTimeout`/`setInterval` |
| no fs / no network / no process (the test environment likewise) | `:30` | ✅ An API fact: none of the 13 globals does I/O; files, network and processes only go through `$` |

**(e) A surface module (`Client`)'s environment**: the same sandbox plus one `console`. `raw/chunks2/0764__chunk-ybjnt5d8.js@4015` verbatim: `let {sandbox:u,context:f}=mzo()` … `Object.assign(u,{console:KGo(S,`[${c}] surface`)})`, matching `asset-044-asset.txt:13710-13712`.

### 1.4 The gates a module passes

1. **The rollout switch**: `raw/chunks2/0329__chunk-110gm4an.js` is 25 lines total, verbatim:

```js
var RYe="tengu_plugin_hooks_modules";
var mUt=!0;
var YJ=()=>k(RYe,mUt);
var _Ue=()=>YJ()&&!Gr("hooks")&&!yr();
var zgn=()=>_Ue()&&!Wb()&&!Ty();
```

`mUt=!0` means **on by default**; `Gr("hooks")`, `yr()`, `Wb()`, `Ty()` are the ground-level gates (`disableAllHooks`/`allowManagedHooksOnly`/policy — see the aliases in `raw/chunks2/0799__x-HOOKS_MODULES_FLAG.js`: `canLoadUserHooksModules`, `canLaunchLoadUserHooksModules`).

2. **Workspace trust**: in an untrusted session modules are held until the person accepts. The post-trust callback in `raw/chunks2/1245__chunk-f5w4pbxy.js@9695` verbatim calls `loadHooksModulesHeldForTrust(T,x)`; the branch at `@8155` reads ``"continuing as an untrusted session (hooks and project settings env stay off)"``.
3. **Tier and order**: five tiers, outer is more authority — `asset-044-asset.txt:11875`: `const TIERS: readonly ["prepend","user","append","builtin","core"];`, whose comment (`:11857-11864`) says `prepend`/`append` are the managed plugins an administrator lists, `user` everything a person installs, `builtin` the plugins bundled in the binary, `core` the engine's innermost link.
4. **A `plugin.register` veto** (`asset-044-asset.txt:7204-7221`): core answers `{ allow: true }`, any hook above may answer `{ refuse: reason }`, and the module does not load — "no step, no hooks, no tools or commands".

**The scan is exact and it is the admission rule** (`asset-044-asset.txt:7223-7269`, `PluginRegisterUses`): before loading, the host reads off the source the patterns the module registers, the `noun.method` calls it makes on `$`, the literal variable names its `$.env` calls spell, and the literal `{plugin,key}` pairs its `$.state` calls name. The comment: "Exact, since a module that spells `on`, `$`, `$.env` or a `$.state` reference other than literally does not load." Runtime really refuses on that list: `Wne()` at `0374@1274791` throws ``"its hooks module does not call it (host rule; the scan lists …)"``.

---

## 2. The capability surface

### 2.1 `Register` / `On` / `EngineInterface`

```ts
// asset-044-asset.txt:8641
export type Register = (on: On, options: PluginOptions) => unknown;
// asset-044-asset.txt:4854-4856
export type HooksModule = { register: Register };
// asset-044-asset.txt:6319-6322
export type On = {
    <P extends Pattern>(pattern: P, hook: NoInfer<HookFor<P>>): Registration<HookFor<P>>;
    <P extends Pattern, const M extends MatcherFor<P>>(pattern: P, matcher: M, hook: NoInfer<MatchedHook<P, M>>): Registration<MatchedHook<P, M>>;
};
```

`On`'s semantics (`asset-044-asset.txt:6308-6318`): `pattern` is one event name, a namespace glob (`classic.*`), everything (`*`) or an exclusion (`!tool.*`); registrations for one event nest in load order, **first registered outermost**; a repeat throws. `Registration.catch` (`:8651-8660`) gives a failed hook one grace retry, one per registration.

`EngineInterface` (`:4192-4193`) is an **empty interface** `extends CoreEngineInterface {}` — the anchor a plugin uses to merge a noun onto `$`; a plugin noun may not be one of the engine's own (`tool`/`session`/`ui`, `:7147-7151`). `HookFor` (`:4840`) folds `*`, a single event and a glob into **one** generic signature; the comment says why not an overload set: `as an overload set the language service offers no tool-name completions inside e.tool === "`.

### 2.2 Every hook point

An event name is `CoreEventOf & NounEventOf`, and `CoreEventOf = EngineEventOf & ClassicEventOf & OpEventOf` (`:3397`). **No plugin noun is declared in this build**, so `NounEventOf` is empty (`:6275`: "Empty until a plugin declares a noun").

| Band | Count | Defined at | Examples |
|---|---|---|---|
| engine's own, `EngineEventOf` | **43** | `:3714-4192` | `tool.call`, `ui.render`, `session.append`, `prompt.compose`, `turn.step`, `engine.create` |
| classic (settings hooks), `ClassicEventOf` | **33** | `:1076-1083`, union at `:4842` | `classic.PreToolUse`, `classic.Stop`, `classic.SessionStart` |
| `$` calls as events, `OpEventOf` | **60** | `:6381-6710` | `fs.write`, `http.fetch`, `clock.every`, `tool.register`, `ui.open` |
| plugin nouns, `NounEventOf` | **0** (this build) | `:6280-6282` | — |
| **name-hookable total** | **136** | | |

**Only two events stream** (`:11445`): `export type StreamingEventName = 'turn.step' | 'process.spawn';` — a hook on either must be an `async function*` (`:11447-11453`, `asset-050:29-30`).

The 43 engine events (`:3723-4178`, declaration order): `tool.call` `tool.check` `ui.render` `ui.resolve` `ui.press` `ui.input` `ui.select` `ui.message` `ui.scroll` `ui.focus` `agent.offer` `agent.spawn` `prompt.submit` `prompt.fill` `prompt.suggest` `prompt.edit` `prompt.section` `prompt.context` `prompt.compose` `prompt.attachment` `tool.describe` `command.run` `command.describe` `config.set` `config.describe` `telemetry.log` `telemetry.mark` `skill.prompt` `attribution.text` `session.start` `session.receive` `session.append` `session.send` `session.compact` `session.attach` `session.detach` `session.measure` `session.end` `plugin.register` `turn.start` `turn.step` `turn.complete` `engine.create`.

The 33 classic events (the `HookInput` union at `:4842`, in order): `PreToolUse` `PostToolUse` `PostToolUseFailure` `PostToolBatch` `PermissionDenied` `Notification` `UserPromptSubmit` `UserPromptExpansion` `SessionStart` `SessionEnd` `Stop` `StopFailure` `SubagentStart` `SubagentStop` `PreCompact` `PostCompact` `PreModelSwitch` `PostModelSwitch` `PermissionRequest` `Setup` `TeammateIdle` `TaskCreated` `TaskCompleted` `Elicitation` `ElicitationResult` `ConfigChange` `InstructionsLoaded` `WorktreeCreate` `WorktreeRemove` `CwdChanged` `FileChanged` `DirectoryAdded` `MessageDisplay`.

The 60 `$`-call events (`:6386-6700`): `model.complete/classify/fork`, `audio.play/speak`, `mcp.call/connect`, `session.cwd/root/model/turns/id/messages/repo/surface/surfaces/authorize/usage/version`, `turn.abort`, `prompt.read`, `tool.list/register`, `command.list/register`, `config.list`, `agent.list/register`, `ui.toast/status/log/notice/invalidate/open/close/panes/copy/blit`, `fs.read/write/list/exists/stat/ancestors`, `store.get/set/delete/keys`, `state.get/set`, `clock.now/sleep/after/every`, `http.fetch`, `process.run/spawn`, `settings.read`, `env.get/set`.

**Why a `$` call counts as an event** (`:6373-6379`): "The calls on `$` the host serves, as events … every one is hookable by name and by `on("*")`. A hook above the caller passes it on, rewrites it, refuses it with `{ deny }` or answers with `{ value }`; core is the host's implementation. The calling hook alone is skipped, and `next.origin` names the caller." — **when one plugin calls `$`, another can intercept it**.

### 2.3 The namespaces and methods on `$`

`CoreEngineInterface` (`:2130-3385`) has **21 namespaces**:

| Namespace | Methods / members | Location |
|---|---|---|
| `plugin` | `name`, `root` | :2134-2143 |
| `ui` | `notice` `invalidate` `blit` `resolve` `log` `ask` `toast` `status` `open` `close` `panes` `scroll` `focus` `copy` | :2148-2365 |
| `model` | `complete` `fork` `classify` | :2369-2438 |
| `audio` | `play` `speak` | :2439-2474 |
| `mcp` | `call` `connect` | :2475-2515 |
| `session` | `messages` `cwd` `root` `model` `turns` `id` `repo` `surface` `surfaces` `usage` `version` `append` `authorize` | :2516-2695 |
| `turn` | `abort` | :2696-2714 |
| `prompt` | `read` `fill` | :2715-2780 |
| `tool` | `list` `register` | :2781-2833 |
| `command` | `list` `register` | :2834-2874 |
| `config` | `list` | :2875-2905 |
| `telemetry` | `log` `mark` | :2906-2943 |
| `agent` | `list` `register` | :2944-2996 |
| `fs` | `read` `write` `list` `exists` `stat` `ancestors` | :2997-3117 |
| `store` | `get` `set` `delete` `keys` | :3125-3151 |
| `state` | `get` `set` | :3158-3191 |
| `clock` | `now` `sleep` `after` `every` | :3200-3239 |
| `http` | `fetch` | :3243-3265 |
| `process` | `run` `spawn` | :3272-3328 |
| `settings` | `read` | :3337-3353 |
| `env` | `get` `set` | :3362-3384 |

**The edges, from the source**: `$.fs` rejects a read or write over 4 MiB, rejects a network location untouched and keeps the OS errno (`:2994-2995`); `$.http.fetch` goes "through the host (never the plugin's own network)", and an `auth` handle rides https only, to a first-party host (`:3245`, `:3249-3250`); `$.process` is **CLI only**, takes no shell, defaults to 30 s (ten minutes at most) and caps each stream at 4,194,304 bytes (`:3267`, `:3274-3285`); `$.settings.read` is **read only** (`:3330-3331`); `$.env.get/set` take the variable name as a string literal, so what a module reads and writes is read off its source (`:3358-3360`); `$.session.messages` returns at most 4096 entries (`:2527`); `$.session.append` writes text blocks alone and only rows the plugin itself originates (`asset-050:115`).

### 2.4 A hook's input/output contract and its budget

- **Signature** `($, e, next)` (`:4489-4494`): `$` is frozen, the same object at every invocation; `e` is frozen to every depth (a rewrite is a copy passed to `next`); `next` is "the rest of the chain", and a chain a hook raises through `$` skips this hook while running every other one (the recursion skip).
- **`e` is plain data**: `asset-044-asset.txt:4465-4467`, "Plain data, frozen to every depth." It is cloned field by field as it crosses to the worker; anything else throws (see §5.3).
- **What `next` carries** (`:6094-6167`): `next(e)`; `next.to(e, tier)` (skipping the links between this hook's own tier and that one); `next.signal` (aborts when the dispatch is abandoned); `next.is(pattern, e)`; `next.event`; `next.origin` (who raised it: plugin name + tier; the engine reads as `{plugin:"engine",tier:"core"}`); `next.trace` (an entry per link beneath); `next.budget`.
- **The budget** (`:4782-4808`):

```ts
readonly ms: 10_000;        // a hook's budget per dispatch, its own time
readonly catchMs: 1_000;    // a .catch handler's grace
readonly lingerMs: 5_000;   // how long it may run after next.signal aborted
```

The load-bearing sentence (`:4775-4777`): "Each bounds the hook's OWN time: the clock stops while a `next(e)` call or any `$` call of the hook's is in flight (a `$.clock` wait excepted)". Overrunning means the hook is absent (unless it registered a `.catch`) and the chain goes on. The failure shape is `HookFailure.kind` of `'throw' | 'timeout'` (`:4818-4830`).

---

## 3. The UI model

### 3.1 Where the elements come from: `$.ui.resolve(e)`, not globals

`asset-044-asset.txt:24-26` says it outright:

```
// The elements a
// render hook draws with (`Box`, `Text`, `Button`, ...) are not globals:
// they come from the surface's table,
//   const { Box, Text } = $.ui.resolve(e)
```

The important part of `$.ui.resolve`'s semantics (`:2195-2210`) is that **it is a read, not a dispatch** — "the engine ran `ui.resolve` (the other hooks, then core) at load, per surface and component". A narrowed `e.surface` gives that table exactly; unnarrowed gives the union (so shared names type-check). An element is "a constructor from props to the frozen plain-data element" (`:3550-3558`): `<Box gap={1}>…</Box>` compiles to `h(Box,{gap:1},…children)`, so the table's constructors **are** the JSX tags; `h` and `Fragment` are the only two JSX globals in the environment (`:13726-13735`).

### 3.2 The four surfaces' tables

The summary is at `:3568-3574` and the four tables at `:3576-3643`:

| Surface | Elements |
|---|---|
| `terminal` | `Box` `Text` `Button` `Input` `Select` `Link` `Code` `Markdown` `Client` `Raster` `Image` |
| `desktop` | the above without `Raster`/`Image`, plus `Svg` |
| `mobile` | `Box` `Text` `Button` `Svg` `Link` `Code` `Markdown` (**no `Input`/`Select`**; the source says the mobile app draws no field yet, not a limit of the device or the protocol) |
| `vscode` | the desktop table without `Client` (the source says `ui_client_module`, `ui_client_press` and `ui_message` name no surface today) |

`RenderSurface = 'terminal' | 'desktop' | 'mobile' | 'vscode'` (`:9663`). There are 15 drawable **components** (`:8680`): `AskUserQuestion` `UserMessage` `AssistantMessage` `ToolUse` `ToolResult` `ToolGroup` `ToolProgress` `CommandOutput` `Spinner` `TurnDuration` `InfoNotice` `SessionMode` `PromptHint` `AbovePrompt` `Pane`. The permission dialog is **not** among them — the engine draws it alone, and a plugin adds context with `$.ui.notice` (`:8676-8678`). A render hook returns a `RenderElement` (`:8682-8690`): "a plain-data tree of elements … Props are an allowlisted subset of Ink's Box/Text props … a tree with any other prop fails validation **as a whole** and the engine's own component is drawn with the original props."

### 3.3 What `$.ui.mount` means (on the test side)

**`$.ui.mount` is not on a plugin's `$`.** The method list of `CoreEngineInterface.ui` (`:2148-2365`) has no `mount`; it appears only on `claude-code/testing`'s `Engine` type:

```ts
// asset-044-asset.txt:14039-14053
export type EngineMount = {
    mount: <P extends RenderSurface, C extends RenderComponent>(target: MountTarget<P, C>) => Promise<Mounted<P, C>>;
};
```

Its semantics (`:14040-14052`): "Raises the plugins' drawing of the component on the surface and holds it, as that surface showing the instance does. Resolves once the tree validated and every `Client` in it drew once." `surface` must be named (**there is no default**; the runtime message at `asset-045:1358-1366` reads `${RENDER_SURFACE_NAMES.join(', ')}; there is no default`), and the returned `Mounted` is trimmed to the acts that surface's table has (`:14500-14510`: "no `input` on `mobile`, no `key` on `vscode`"). The header's example (`:45-58`):

```ts
test('notes add up on every surface that takes input', async $ => {
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ plugin: 'notes', surface, ...BAND })
    await ui.input({ key: 'new', text: 'milk' })   // expect((await ui.find({ key: 'count' }))?.text).toBe('1 note')
```

`:41-43` states what this kind of test is: it exercises the mod's hooks, the tree they return under each surface's rules and its `Client` modules, "**never a surface's paint** (Ink's, the desktop page's)."

### 3.4 The hard points of the drawing contract

`Pane` is the one component a plugin opens itself (`$.ui.open`, `:2270-2291`): asked by something the person did (a command they typed, a prompt, a press) it is placed at any width; unasked it needs 144 columns (110 once asked), and below that it **waits, undrawn**. A `Button` is a leaf whose `onPress` closure stays in the plugin's own environment while the host holds only a handle (`:8691-8698`). `Raster`/`Image` are terminal-only, and `$.ui.blit` repaints a mounted one without a render pass (`:2174-2194`). A render hook **may not write** `$.state` (`:3175-3181`, "Refused while a `ui.render` hook draws"); a redraw comes from `$.ui.invalidate` or from a `state.get` subscription (`:2154-2156`).

---

## 4. Testing and validation

### 4.1 The `claude-code/testing` contract

Declared from `asset-044-asset.txt:13842`, exporting five things:

```ts
export const describe: (name: string, body: () => void) => void;   // :13928
export const test: (name: string, ...rest: TestRest) => void;      // :14855
export const expect: Expect;                                      // :14125
export const mock: Mock;                                          // :14441
export const tier: (tier: PluginTier) => void;                    // :14906
```

- **`test`** (`:14844-14855`): "One test: it passes when its body returns or resolves, and fails when it throws, rejects or outlasts its time (**5000 ms**, or `timeoutMs`). The body gets the engine's `$` and an `on` whose hooks sit beneath every plugin". `TestBody = ($: Engine, on: On) => unknown` (`:14864`), `TestOptions = { plugins?, timeoutMs?, options? }` (`:14872-14887`).
- **`tier`** (`:14900-14906`): "Says which tier the plugin under test loads in, **once, at the top of the file**: `prepend`, `user` (when unsaid), `append` or `builtin`."
- **`describe`** (`:13921-13928`): "its body runs **at once**, while the file loads."
- **`expect`**: `Expecting & Matching` (`:14116`), the matcher table from `:14215`; `AsyncMatchers` runs the same checks against what a promise settles with (`:13880-13886`).
- **`$.classic`**: the test's `$` also carries `classic` (`:14001-14003`), as in `await $.classic.SessionStart({ source: 'clear' })`; `PreToolUse` is the exception, riding `$.tool.call` (`:13896-13996`). The test's `$` also has `ui.press`/`ui.input`/`ui.select`/`mount` (`:13979`).

### 4.2 What `mock`'s clock / store / env mean

```ts
// asset-044-asset.txt:14403-14431
export type Mock = {
    clock: (on: On, options?: MockClockOptions) => MockClock;
    store: (on: On, entries?: Readonly<Record<string, unknown>>) => void;
    env: (on: On, variables: Readonly<Record<string, string>>) => void;
};
```

None of the three replaces a global; each registers hooks on the test's own `on` and answers from beneath (`:14400-14401`: "The world beneath the plugins, mocked noun by noun: each member registers hooks of the test's `on`, visible where the test calls it."). The implementations in asset-045, verbatim:

```js
// asset-045-asset.txt:1112-1118 (mockClock)
on('clock.now', () => ({ value: clock.now() }));
on('clock.sleep', hold); on('clock.after', hold); on('clock.every', hold);
// :1187-1190 (mockEnv)
on('env.get', ($, e) => { const value = held[e.name]; return { value: typeof value === 'string' ? value : undefined }; });
// :1204-1213 (mockStore)
on('store.get', ($, e) => ({ value: held.get(e.key) }));   // set / delete / keys likewise
```

`MockClock`'s five acts (`:14447-14491`): `now()`; `advance(ms)` (resolving each wait due on the way, in order, letting the event loop settle after each); `set(ms)`; `settle()` (= `advance(0)`); `sleep(ms)`. A held wait is dropped when its dispatch aborts, and is let go after ten seconds of real time (treated as a hook that overran). The implementation caps one advance at 10,000 fires (`asset-045:1016`), past which it throws "an interval shorter than the advance?".

### 4.3 What `claude plugin test` does

The command table (`raw/chunks2/0766__chunk-ywkfhf88.js:1`):

```js
test:{usage:"plugin test [dir]",description:"Run a mod's tests",earlyAccess:"hooksModules"}
```

`earlyAccess` decides whether it shows in help at all (the same table gives `plugin eval` `earlyAccess:"pluginEval"`). Registration (`raw/chunks2/1435__x-registerPluginCommands.js@20608`) is `n.command("test [dir]",{hidden:!0})`, and any other spelling prints ``"claude plugin test: not run from this spelling. Use `claude …`"``. The entry dispatch (`raw/chunks2/0006__x-inntypeofn.js@5164`) first computes a refusal reason, returns with `process.exitCode=1` when there is one, and otherwise pulls `pluginTestMain` from `import("/$bunfs/root/chunk-01653fey.js")` and runs `t.slice(2)`:

```js
let [{loadFastPathPolicy:e},i,{pluginTestRefusal:o}]=await Promise.all([...]),
    s=o({helperError:await e(l),isRolloutOn:i.hooksModulesRolloutOn(),canLoadUserModules:i.canLoadUserHooksModules()});
if(t[2]==="--file"&&s!==void 0){ ... REPORT_MARK ... }
if(s!==void 0){ process.stderr.write(`claude plugin test: ${s}\n`),process.exitCode=1; return }
```

The two refusal reasons (`raw/chunks2/0768__chunk-9d5bhh5t.js`): ``"hooks modules are turned off in this process: the rollout switch served off, and a plugin's tests run only while it is on"`` / ``"hooks modules are turned off here (disableAllHooks, allowManagedHooksOnly or a policy)"``.

**The kit itself** (`raw/chunks2/0769__x-CHILD_ARGV_LENGTH.js`, bun's `chunk-01653fey`): `test()`/`describe()`/`tier()` only push cases into `collector` (`asset-045:10-59`), and after `collector.close()` nothing may register again; `run()` runs every case in order and `JSON.stringify`s the result (`asset-045:1893-1901`), led by `REPORT_MARK = "claude-plugin-test-report "` (`raw/chunks2/0765__chunk-vvhdd9fn.js:11`); each case first opens a seat with `openSeat(plugins, tier, options)` and then wraps the body in `timed(body, timeoutMs)` (`asset-045:1819-1828`, `1867-1888`). The seat is where the engine surface is handed over: `openSeat` calls `host.open` / `host.call` / `host.mount` / `host.pressed` and the rest (`asset-045:1573-1617`).

- **`claude-code/testing` is a virtual module**: `re="claude-code/testing"`, evaluated inside a `vm` context with `new ht.SourceTextModule(...)` (`raw/chunks2/0769__x-CHILD_ARGV_LENGTH.js@36000-37000`); the kit's own module root is `he="@/src/plugins/functionHooks/plugin-test/testing"`, and an import outside it is refused: ``"the kit's ${n} imports ${e}, which is outside the kit"``.
- The kit must be installed explicitly: `asset-045:921-922` — ``"'claude-code/testing' runs under claude plugin test; nothing here installed it"``.

### 4.4 What `claude plugin validate` does

The command table, verbatim (`raw/chunks2/0766__chunk-ywkfhf88.js:1`):

```js
validate:{usage:"plugin validate <path>",description:"Validate a plugin or marketplace manifest, or the skills, agents, and commands in a directory"}
```

Two options at registration (`raw/chunks2/1435__x-registerPluginCommands.js@13750`): `--strict` ("Treat warnings as errors (exit 1). Use in CI …") and `--json`. Its role, from `asset-044-asset.txt:8-11`: "reads a plugin's manifest and its hooks module's source the way the engine will and reports what the module hooks and calls and everything the engine would refuse, before any session loads it."

The report's contents are `PluginRegisterUses` (`:7230-7269`): `events` (the patterns `on(...)` names, in registration order), `calls` (`noun.method`, sorted, each once), `env.reads`/`env.writes`, `state.reads`/`state.writes`. It also checks the types contract (`asset-050:62`: "`claude plugin validate` checks the contract") and whether the `$.state` keys the module names are in it (`asset-051:12`).

---

## 5. Relationship to the main harness

### 5.1 Where it sits in the artifact

The build constant leaks the source path (`raw/chunks2/0374__chunk-mphp7acd.js@1267204`):

```js
HOOKS_WORKER_URL:"/$bunfs/root/src/plugins/functionHooks/hooks-worker/hooks-worker.js"
```

That string repeats alongside the version constant in `raw/chunks2/1330__x-update.js` and elsewhere (it is baked into the frozen literal every module shares). The paths the type declarations cite are all `src/plugins/functionHooks/...` too, e.g. `"src/plugins/functionHooks/types/render/render-component.ts"` at `raw/chunks2/0055__chunk-hrhfcbdv.js@555636`, and the kit's `@/src/plugins/functionHooks/plugin-test/testing`. **Inferred**: `src/plugins/functionHooks/` is this subsystem's source root.

### 5.2 The worker's startup and the two-half protocol

**The host half** (`raw/chunks2/0374__chunk-mphp7acd.js`): `geo()` builds the `Worker` plus two `SharedArrayBuffer`s (`stamp`/`marks`, cross-thread progress stamps, `@1268258`); the global handle `$vt()` exposes `setSpawner / spawnWorker / setReloader / reloadModule / setLoadedNotifier / notifyLoaded`; **one worker serves every plugin** (`@1728382`); a `ping`/`pong` heartbeat that goes unanswered rules the worker "wedged (a hook spinning without yielding)", blames a named plugin, unloads it and respawns the worker (`UO()` `@1705533`, `$Pt()`, `FPt()`); `OAe()` (`@1264941`) loads one module, `WIe()` hot-reloads one, `hB()` unloads a set, and `PPt()` is the whole-set load state machine.

**The worker half** (`raw/chunks2/0150__x-thepluginsenvironmentwasunloaded.js`, 11,939 bytes total): `import{workerData as S}from"worker_threads"` (`@4895`), `self.onmessage` receives host messages, `K(self)` closes (`@11930`). The protocol, message by message:

| host → worker | worker → host |
|---|---|
| `ping` `load` `unload` `build` `resolve` `call` `dispatch` `dispatch_stream` `stream_pull` `stream_close` `next_result` `next_error` `next_step` `abort` `press` `press_release` | `pong` `loaded` `load_error` `built` `built_error` `resolved` `resolve_error` `call_result` `call_error` `result` `error` `stream_step` `press_result` `press_error` `log` `hook_failed` `unhandled` |

The worker also gives each plugin environment its own `MessagePort` (the `case"load"` branch in `0150` takes a `port`), carrying `next` `next_abort` `next_pull` `next_close` `op` `op_abort` `op_pull` `op_close` (worker → plugin) and `flush` `op_result` `op_abort` (plugin → worker). An `op` is the remote call of one `$.<noun>.<method>`, arguments in `args` and the answer in `value`.

**This closes the 06 doc's gap.** `extracted/06-quirks.md:581`, verbatim:

```
2. **hooks-worker.js 本体**：只有构建期路径常量（`chunks/c0682.js @32968`）与测试/作者侧代码（`chunks/c1409.js`、`chunks/c3083.js`）。worker 的 IPC 协议、生命周期、超时策略**未找到**——"存在"是一手证据，"如何工作"未知。
```

The state now: **the worker bundle itself still does not appear as a carveable module in `raw/chunks2/`** (it is a separate `$bunfs` entry only ever referenced by URL) — that layer is still not found; but **the worker-side implementation code is found** (`0150`), and **the host's IPC, lifecycle and timeout policy are found** (`0374`). The conclusion moves from "it exists" to "the mechanism is known".

### 5.3 A plugin hook's I/O contract

The cross-worker I/O contract can be stated precisely as what does and does not cross the line:

- **The event payload**: the host serializes `e` into the `dispatch` message; the worker side calls `d.dispatch({id,event,payload,environments,leftOut,origin,raise,floors,cutAt}, …)`.
- **The return value**: the worker answers `{type:"result",id,…}`; an unclonable value reports ``"result not cloneable: …"``.
- **Streaming**: `dispatch_stream` / `stream_pull` / `stream_step` / `stream_close`, and a chunk must be plain data too (``"a chunk that is not plain data: …"``).
- **`next`'s round trip**: worker → host `{type:"next",id,nextId,argument,floors}`, answered by `next_result`/`next_error`; an abort goes as `{type:"next_abort",…}`.
- **A `$` call**: worker → host `{type:"call",callId,environmentId,call,callers}`, answered by `call_result`/`call_error`; the failure text carries ``"$.${a.name}.${a.method} returned a value that is not plain data"``.
- **Admission is scan-as-allowlist**: before any `$.X` runs, the host looks up that plugin's scan (`Wne()` at `0374@1274791`) and refuses outright when `X` is not in `calls`.
- **A few operations only a plugin may call**: `var aoe=new Set(["ui.open","ui.toast","ui.status","ui.log","ui.notice","ui.ask","tool.register","command.register","agent.register","prompt.fill","prompt.suggest"]);` near `0374@1274791` — this group is treated specially in the host-check table (`D=aoe.has(e)` decides whether the argument gets one extra transform). **Inferred**: it is the allowlist of request/UI-shaped operations.
- **A same-thread bypass**: `0374@1712522` has `a.CLAUDE_CODE_HOOKS_SAME_THREAD?"same-thread":"worker"`; `xPt()` relies on it to decide whether an already-loaded module can be reused (`@1712575`). It serves built-ins and debugging, not the ordinary plugin path.
- **Events that force a full reload**: `0374@1710573`: `var wPt=["engine.create","plugin.register"];` — a module hooking either cannot be reused incrementally, and the whole set folds again.

### 5.4 Relationship to the 06 doc's 33 hook events

**It is a subset relationship, not the same thing.**

- The 06 doc's 33 are the **settings hook** events (command/http/mcp_tool/script/prompt/agent from a `hooks` config), drawn from the union of `hook_event_name`. In this build that is exactly the `HookInput` union at `asset-044-asset.txt:4842`, and it **counts to 33 exactly**.
- function hooks exposes them **unchanged as `classic.<Event>`** (`:1066`: ``export type ClassicEventName = `classic.${ClassicHookEvent}`;``), with `e` being what that hook receives on stdin (`:1069-1074`). `classic.PreToolUse` differs in shape: its `e` is a `ToolCallEnvelope`.
- The chain's order (`:1072-1073`): "The chain is [managed settings hooks, …hooks modules, the other settings hooks as core], so a managed block ends it above every module." **Managed settings hooks outermost, plugin modules in the middle, the remaining settings hooks as core innermost.**
- Beyond those 33, function hooks adds **43 + 60 = 103** further event points (§2.2).
- Two hard details the 06 doc recorded hold here too: `classic.PreToolUse` is not a call in its own right (the runtime throws, at `raw/chunks2/0769__x-CHILD_ARGV_LENGTH.js@~14300`, ``"$.classic.PreToolUse is no call on the engine's $: the engine raises it inside tool.call, so a test calls $.tool.call"``); and a matcher narrows on fields like `e.props.origin.kind` (`asset-050:103`).
- The rollout switch the 06 doc recorded is confirmed verbatim, except that the earlier pass did not read what `mUt=!0` means — **it defaults on**.

---

## 6. Verdict: how wired it is

**In this build it is a genuinely wired, usable subsystem, not "types only".** On four levels of evidence:

**(1) The rollout switch defaults on.** `raw/chunks2/0329__chunk-110gm4an.js:24` is verbatim `var mUt=!0;`; `YJ=()=>k(RYe,mUt)` reads `tengu_plugin_hooks_modules` from GrowthBook and falls back to `!0`. The ways it can be turned off are enumerated too (`HOOKS_MODULES_FLAG_SOURCE` in `raw/chunks2/0330__chunk-98jdspgk.js`: `override` / `payload` / `disk` / `disabled` / `fallback`).

**(2) There are real call sites, sensibly distributed.** At least: loading after trust is accepted (`raw/chunks2/1245__chunk-f5w4pbxy.js@9695`); worker instantiation and respawn (`0374@1268258`, `@1728382`, `@1724606`); remote-surface render requests (`raw/chunks2/0105__chunk-xep95vq1.js@570097`, the `hooked:` field, and `@570771`, `client_modules`); the CLI commands (`0006__x-inntypeofn.js@5164`, `1435__x-registerPluginCommands.js@13750`/`@20608`); plugin-folder watching and hot reload (`bIt()`'s debounce and `SIt()`'s breaker, `OIt()`'s `watchPlugins`/`release`, all in `0374`).

**(3) The binary already ships 10 plugins written against it.** Each of `raw/chunks2/1651…1661` carries a `hooksModule:` field (shaped `eS({name:…,hooksModule:iU(import.meta.dir,<module>,()=>name())})`), and 6 of them also export `registerPlugin`; the built-in loader requires a module to export `registerPlugin` or throws (`raw/chunks2/0095__chunk-sthe7p0e.js@66491`: ``"a built-in module has no registerPlugin function: …"``). Names that can be confirmed: `claude-test` (1651/1654), `cc-plugin-mermaid` (1653), `cc-plugin-responsive-mode` (1654), `cc-plugin-sec-default` (1657, carrying `seat(` and `decidesClassicEvent` — a policy plugin seated in the `prepend`/`append` tiers that decides classic events), `cc-plugin-agents-md` (1658), `cc-plugin-telemetry` (1659, whose closure mentions both the `"anthropic"` and `"collector"` streams), `cc-plugin-mods-guide` (1661).

**(4) It has first-class documentation and a skill.** `assets/` holds the complete `asset-050` (long form) and `asset-051` (the `plugin-authoring` SKILL.md), and the skill lays the type files beside the mod folder (`asset-051:14`).

**But it is still EARLY ACCESS, with visible unfinished edges**: the declaration header says so itself (`:3`); `plugin test` is `earlyAccess:"hooksModules"` and `{hidden:true}`; a dead field in `hooks.json` was turned into an explicit error (`surface: bbt({error: 'hooks.json \`surface\` is gone: …'})` near `raw/chunks2/0055__chunk-hrhfcbdv.js@131757`); the surface tables say what is not done yet (`mobile` has no `Input`/`Select`, `:3610-3614`, "The table grows when the app draws them"; `vscode` has no `Client`, `:3625-3631`); and **the `hooks-worker.js` bundle itself is still not found** (§7).

**In one line**: the type declaration is the contract written for people, but the machinery behind that contract — the worker, the sandbox, the lifecycle, scan admission, the built-in plugins, the CLI, hot reload, the UI wire protocol — **all exists in this binary and is called**; it is not hidden, only wrapped in a rollout switch that defaults on and a CLI subcommand that is hidden by default.

---

## 7. Not found / to verify

- **The `hooks-worker.js` bundle** (the `$bunfs` entry `HOOKS_WORKER_URL` names): **not found**. Only the URL constant and the worker's internal bridge code (`0150`).
- **The full semantics of `CLAUDE_CODE_HOOKS_SAME_THREAD`**: **partial**. The branch is at `0374@1712522`, but which context a module is evaluated in on that path, and whether it skips the `vm` sandbox, are **not found**.
- **Whether anything beyond the 13 sandbox globals is injected**: **inferred no** (`ip()=Object.create(null)` plus 13 `define` calls); but what `FBe(t,pbe)` (`0146@206978`) installs into the context was **not read verbatim**. The same grade applies to the business reason for the `aoe` allowlist (11 operations): **inferred** to be request/UI-shaped operations with no enumerable host check; the source states no reason.
- **The exact mapping from `cc-plugin-diff` / `cc-plugin-tips` / `cc-plugin-plugin-authoring` / `cc-plugin-claude-test` to those ten `hooksModule:` files**: **partial**, inferred from string co-occurrence, not resolved one by one. **A plugin-side bypass that draws without `ui.render`**: **not found**; every drawing goes through `ui.render` + `$.ui.resolve`.
---

## Appendix: citation index

**Type declarations (`work/assets/asset-044-asset.txt`)**: `:1-11` header and EARLY ACCESS · `:19-26` environment/suffixes/`import()`/where elements come from · `:30-31` the test environment · `:1066-1091` classic event names and inputs · `:2130-3385` CoreEngineInterface (21 namespaces) · `:3397` what CoreEventOf is made of · `:3546-3648` the element tables and four surfaces · `:3714-4192` the 43 engine events · `:4192-4205` EngineInterface/Built · `:4398-4457` EventCalls · `:4463-4498` EventName/EventOf/Events · `:4782-4830` HookBudget/HookFailure · `:4842` the 33 classic inputs union · `:4854-4856` HooksModule · `:6094-6193` Next/NextBudget · `:6258-6306` NounEvent · `:6308-6322` On · `:6371-6710` OpEventOf (the 60) · `:7147-7269` PluginNoun/PluginOptions/PluginRegister* · `:8641-8660` Register/Registration · `:8680-8690` RenderComponent/RenderElement · `:9663` RenderSurface · `:11445` StreamingEventName · `:11857-11875` Tier/TIERS · `:13696-13838` globals and the 13 names · `:13842-14914` all of claude-code/testing.

**The test kit (`work/assets/asset-045-asset.txt`)**: `:10-59` collector · `:114` TIMEOUT_MS=5000 · `:911-935` install/handover · `:1016` FIRES_PER_ADVANCE_MAX · `:1112-1126` mockClock · `:1182-1214` mockEnv/mockStore · `:1216-1224` mock · `:1340-1413` mount/mounted · `:1566-1618` openSeat · `:1813-1888` runCase/timed · `:1890-1917` run/test/tier.

**JS implementation (`raw/chunks2/`)**: `0006__x-inntypeofn.js@5164` plugin test dispatch · `0055__chunk-hrhfcbdv.js@75380` the suffix table · `@131757` the hooks.json schema · `0146__chunk-hhxhpvxp.js@58914` the globals bootstrap source · `@152175` the `import()` refuser · `@152847` SourceTextModule · `@158956` `ip()` · `@202514` `kVr()` · `@206807-206945` codeGeneration and `mzo()` · `0150__x-thepluginsenvironmentwasunloaded.js` the worker half (whole file) · `0329__chunk-110gm4an.js` the rollout switch (whole file) · `0330__chunk-98jdspgk.js` the switch's sources · `0374__chunk-mphp7acd.js@1262700` the native-module refusal · `@1264941` `OAe()` · `@1267204` `Nvt()` · `@1268258` `geo()` · `@1274791` `aoe` + scan admission · `@1705533` worker death · `@1710573` `wPt` · `@1712522` same-thread · `@1724606`/`@1728382` respawn and instantiation · `0764__chunk-ybjnt5d8.js@4015` the surface sandbox + console · `0765__chunk-vvhdd9fn.js:11` REPORT_MARK · `0766__chunk-ywkfhf88.js:1` the CLI table and earlyAccess · `0768__chunk-9d5bhh5t.js` pluginTestRefusal · `0769__x-CHILD_ARGV_LENGTH.js@13325` pluginTestMain · `@13818` the three-file fixture · `@36000-37000` the virtual module's vm evaluation · `0799__x-HOOKS_MODULES_FLAG.js` the export aliases · `0095__chunk-sthe7p0e.js@66491` the built-in module's registerPlugin check · `1245__chunk-f5w4pbxy.js@8155`/`@9695` the trust gate · `1435__x-registerPluginCommands.js@13750` validate registration · `@20608` test registration · `1651-1661` the 10 built-in hooks-module plugins · `1923__x-marketplaceAddHandler.js@17949` the validate handler.

**First-party prose**: `asset-050-Function-hooks-the-long-form.md` (`:9-31` what it is and the event surface, `:33-62` types and contracts, `:64-75` developing and `plugin test`, `:77-103` `ui.render` in depth, `:105-120` `session.append`, `:122-135` long-lived work, `:137-144` registering tools and agent types) · `asset-051-plugin-authoring.md` (`:6-18` the three files and where types land, `:20-41` the shape table, `:42-48` checking and reading refusals).

**The earlier pass**: `extracted/06-quirks.md:5` the 33 hook events · `:18-126` §1 the hooks system · `:125-126` §1.6 hooks-worker and functionHooks · `:557` the rollout-switch table · `:581` "the worker's IPC protocol not found".
