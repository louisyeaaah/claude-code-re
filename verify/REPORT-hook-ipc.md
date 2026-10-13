# Hook IPC：hooks-worker 是怎么跑起来的

> 补齐 `06-quirks.md` 里"hooks-worker 本体未找到"的缺口。对象仍是 Claude Code v2.1.287。
> 一句话：**它不是一个 socket，而是一个 `Worker` 线程 + 两块 `SharedArrayBuffer` 的无锁协调**。
> 相关：`06-quirks.md`（33 个 hook 事件与 matcher 语义）、`REPORT-plugin-api.md`（插件 API 面）。

## 结论速览

1. hooks 跑在**独立线程**里：`new Worker(HOOKS_WORKER_URL, {name:"hooks", workerData:{stamp, marks}})`（`raw/chunks2/0374__chunk-mphp7acd.js` @1268211 一带）。
2. 宿主与 worker 之间用**两块共享内存**做快速协调：`stamp`（单槽，存放当前活跃 hook 的 id）与 `marks`（标记数组），全部经 `Atomics.load` 无锁读。
3. 生产环境的 worker 脚本路径是 `/$bunfs/root/src/plugins/functionHooks/hooks-worker/hooks-worker.js`；开发态回退到源码相对路径 `../../../hooks-worker/hooks-worker.ts`（Windows 下额外处理 `B:/~BUN/root/` 前缀）。
4. 生命周期由**心跳 + 在途计数**管理：`heartbeat` / `awaitingPong`，以及 `inFlight / pendingCalls / pendingLoads / pendingBuilds / pendingPresses / pendingResolves` 六类在途计数；只有全部归零且心跳对得上，才判定为空闲（`ePt()`）。
5. 支持**热重载**：`reloadModule(path)` + `notifyLoaded(names)` —— 插件模块可以在会话中途换掉。
6. 调用有**超时兜底**：`LAe()` 定时后用统一错误拒绝该次调用（`DAe()` 从 pending 表里摘除并 reject）。

## 1. 线程与共享内存

```js
var Ovt = (e, n) => ({ name: "hooks", workerData: { stamp: e, marks: n } });

function geo() {
  const stamp = new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT * vts);
  const marks = new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT * Ets);
  return { worker: new Worker(Nvt(), Ovt(stamp, marks)), stamp: new Int32Array(stamp), marks: new Int32Array(marks) };
}
```

- `Nvt()` 解析 worker 脚本 URL：优先 `HOOKS_WORKER_URL`（bunfs 内的 `hooks-worker.js`），Windows 上把 `B:/~BUN/root/` 前缀转成 `file://`；解析不到就退回模块相对路径 `../../../hooks-worker/hooks-worker.ts`。**生产与开发两条路径同时存在于代码里**。
- 读共享状态的两个函数：

```js
var ZAt = (e) => e.names.get(Atomics.load(e.stamp, c7e));         // 当前活跃 hook
function hse(e) {                                                  // 标记优先级扫描
  const { stamp: n, names: r } = e;
  return [...Array.from({ length: n.length - Tjt }, (s, g) => Atomics.load(n, Tjt + g)),
          Atomics.load(n, K7n)]
         .filter((s) => s !== 0).map((s) => r.get(s)).find((s) => s !== undefined);
}
```

`stamp` 是一个"当前在跑哪个 hook"的公告板，`marks` 是一组可由双方置位的标记（`0` = 未置位），**用原子读而不是消息传递**——这样宿主要在热路径上知道"现在是不是某个 hook 在拦截"时，不需要往返一次消息。

## 2. 生命周期与在途计数

```js
function ePt(e) {
  if (!(e.inFlight.size === 1 && e.pendingCalls.size === 0 && e.pendingLoads.size === 0 &&
        e.pendingBuilds.size === 0 && e.pendingPresses.size === 0 && e.pendingResolves.size === 0)) return;
  const [r] = e.inFlight, [s, g] = r ?? [], h = e.awaitingPong?.n;
  if (!(s !== void 0 && g !== void 0 && h !== void 0)) return;
  ...
}
```

宿主侧维护一张状态表：

```js
var Hvt = () => ({ names: new Map, dispatches: new Map, pendingLoads: new Map, dispatchCounter: 0,
                   died: void 0, opControllers: new Map, work: new Map, servedCalls: new Map, callCounter: 0 });
```

- `heartbeat` / `awaitingPong`：定期 ping，等 pong；`K0()` 负责清掉心跳定时器。
- `opControllers`：每个"环境/操作"一个 AbortController，按前缀批量中止（`JAt()` 删控制器并 abort，`gse()` 结束对应的操作流）。
- 超时：`LAe(e, n, r)` 设一个定时器，到点统一 reject；`DAe(e)` 从 pending 表里摘除并 reject（`Ceo()` 负责 unref）。
- `$ne(e, n, r)` 维护每个名字的 `{ops, epoch}`：`ybe(r)` 为真时计 0，否则计 1（**推断**：区分阻塞型与异步型 hook 的占用）。

## 3. 热重载

```js
function $vt() {
  const e = Ys(), n = Ys(), r = Ys();
  return { setSpawner: e.set, spawnWorker: () => (e.get() ?? geo)(),
           setReloader: n.set,
           reloadModule: (s) => n.get()?.(s) ?? Promise.reject(Error("hooks host not loaded yet; nothing to reload")),
           setLoadedNotifier: r.set, notifyLoaded: (s) => r.get()?.(s) };
}
```

`reloadModule(path)` 让宿主把某个插件模块**换掉并重新加载**，`notifyLoaded(names)` 把"已加载的 hook 名单"广播出去（`Fne()` 调用它）。这解释了为什么插件开发者能在会话中途改插件：worker 是常驻的，模块是可替换的。

## 4. 与前面报告的关系

| 报告 | 覆盖的是 |
|---|---|
| `06-quirks.md` | **事件面**：33 个 hook 事件、matcher 语义、输入/输出契约与上限 |
| 本报告 | **执行机构**：worker 线程、共享内存、心跳、在途计数、热重载、超时 |
| `REPORT-plugin-api.md` | **插件面**：插件能 import 什么类型、能挂哪些实现、UI 与测试基建 |

三层叠起来才完整：事件 → 调度到 worker → worker 里跑插件代码。

## 5. 未完成 / 未验证

1. **worker 另一侧的协议细节未读出**：`hooks-worker.js` 本体（bunfs 内那个文件）没有单独解出来；本报告描述的是**宿主侧**（主线程）的行为。
2. `vts` / `Ets`（两块共享内存的长度）、`c7e` / `Tjt` / `K7n`（槽位索引）、`KKe`（超时基数）等常量值**未逐个读出**。
3. `n0o`…`ePt()` 里 `inFlight.size === 1` 这个约束的语义（**推断**：同一时刻只允许一个 hook 处于"活跃"）未在运行时验证。
4. `marks` 的置位方（宿主还是 worker）未确认。
5. 没有实测热重载（会改本机插件状态，按纪律不擅自做）。
