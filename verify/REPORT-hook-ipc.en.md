> English version. 中文原版：[REPORT-hook-ipc.md](REPORT-hook-ipc.md)

# Hook IPC: how the hooks-worker actually runs

> Filling in the "the hooks-worker itself was not found" gap from `06-quirks.en.md`. The object is still Claude Code v2.1.287.
> In one sentence: **it is not a socket but a `Worker` thread plus two `SharedArrayBuffer`s coordinated without locks**.
> Related: `06-quirks.en.md` (the 33 hook events and matcher semantics), `REPORT-plugin-api.en.md` (the plugin API surface).

## Conclusions at a glance

1. hooks run in a **separate thread**: `new Worker(HOOKS_WORKER_URL, {name:"hooks", workerData:{stamp, marks}})` (`raw/chunks2/0374__chunk-mphp7acd.js` around @1268211).
2. Host and worker coordinate quickly through **two blocks of shared memory**: `stamp` (a single slot holding the id of the currently active hook) and `marks` (an array of markers), all read without locks via `Atomics.load`.
3. In production the worker script path is `/$bunfs/root/src/plugins/functionHooks/hooks-worker/hooks-worker.js`; in development it falls back to the source-relative path `../../../hooks-worker/hooks-worker.ts` (on Windows the `B:/~BUN/root/` prefix gets extra handling).
4. The lifecycle is managed by a **heartbeat + in-flight counts**: `heartbeat` / `awaitingPong`, plus six kinds of in-flight counter — `inFlight / pendingCalls / pendingLoads / pendingBuilds / pendingPresses / pendingResolves`; only when all of them are zero and the heartbeat matches is the worker judged idle (`ePt()`).
5. **Hot reload** is supported: `reloadModule(path)` + `notifyLoaded(names)` — a plugin module can be swapped out mid-session.
6. Calls have a **timeout backstop**: `LAe()` sets a timer and then rejects that call with a uniform error (`DAe()` removes it from the pending table and rejects).

## 1. Thread and shared memory

```js
var Ovt = (e, n) => ({ name: "hooks", workerData: { stamp: e, marks: n } });

function geo() {
  const stamp = new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT * vts);
  const marks = new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT * Ets);
  return { worker: new Worker(Nvt(), Ovt(stamp, marks)), stamp: new Int32Array(stamp), marks: new Int32Array(marks) };
}
```

- `Nvt()` resolves the worker script URL: `HOOKS_WORKER_URL` (the `hooks-worker.js` inside bunfs) takes priority, and on Windows the `B:/~BUN/root/` prefix is turned into `file://`; if it cannot be resolved it falls back to the module-relative path `../../../hooks-worker/hooks-worker.ts`. **Both the production and the development path exist in the code at the same time**.
- Two functions read the shared state:

```js
var ZAt = (e) => e.names.get(Atomics.load(e.stamp, c7e));         // currently active hook
function hse(e) {                                                  // marker priority scan
  const { stamp: n, names: r } = e;
  return [...Array.from({ length: n.length - Tjt }, (s, g) => Atomics.load(n, Tjt + g)),
          Atomics.load(n, K7n)]
         .filter((s) => s !== 0).map((s) => r.get(s)).find((s) => s !== undefined);
}
```

`stamp` is a noticeboard for "which hook is running right now", and `marks` is a set of markers that either side can set (`0` = not set); **they use atomic reads rather than message passing** — that way, when the host needs to know on a hot path whether some hook is intercepting right now, it does not need a message round-trip.

## 2. Lifecycle and in-flight counts

```js
function ePt(e) {
  if (!(e.inFlight.size === 1 && e.pendingCalls.size === 0 && e.pendingLoads.size === 0 &&
        e.pendingBuilds.size === 0 && e.pendingPresses.size === 0 && e.pendingResolves.size === 0)) return;
  const [r] = e.inFlight, [s, g] = r ?? [], h = e.awaitingPong?.n;
  if (!(s !== void 0 && g !== void 0 && h !== void 0)) return;
  ...
}
```

The host side maintains a state table:

```js
var Hvt = () => ({ names: new Map, dispatches: new Map, pendingLoads: new Map, dispatchCounter: 0,
                   died: void 0, opControllers: new Map, work: new Map, servedCalls: new Map, callCounter: 0 });
```

- `heartbeat` / `awaitingPong`: a periodic ping, then wait for the pong; `K0()` is responsible for clearing the heartbeat timer.
- `opControllers`: one AbortController per "environment/operation", aborted in batches by prefix (`JAt()` deletes the controller and aborts, `gse()` ends the corresponding operation stream).
- Timeout: `LAe(e, n, r)` sets a timer and rejects uniformly when it fires; `DAe(e)` removes the entry from the pending table and rejects (`Ceo()` handles the unref).
- `$ne(e, n, r)` maintains `{ops, epoch}` per name: when `ybe(r)` is true it counts 0, otherwise 1 (**inferred**: distinguishing the occupancy of blocking hooks from that of asynchronous ones).

## 3. Hot reload

```js
function $vt() {
  const e = Ys(), n = Ys(), r = Ys();
  return { setSpawner: e.set, spawnWorker: () => (e.get() ?? geo)(),
           setReloader: n.set,
           reloadModule: (s) => n.get()?.(s) ?? Promise.reject(Error("hooks host not loaded yet; nothing to reload")),
           setLoadedNotifier: r.set, notifyLoaded: (s) => r.get()?.(s) };
}
```

`reloadModule(path)` lets the host **swap out a plugin module and load it again**, and `notifyLoaded(names)` broadcasts "the list of loaded hooks" (`Fne()` calls it). This explains why plugin developers can change a plugin mid-session: the worker is resident, and modules are replaceable.

## 4. Relationship to the earlier reports

| Report | What it covers |
|---|---|
| `06-quirks.en.md` | **The event surface**: the 33 hook events, matcher semantics, input/output contracts and limits |
| This report | **The execution machinery**: the worker thread, shared memory, the heartbeat, in-flight counts, hot reload, timeouts |
| `REPORT-plugin-api.en.md` | **The plugin surface**: what types a plugin can import, which implementations it can hook into, the UI and test infrastructure |

Only the three layers stacked together are complete: event → dispatched to the worker → the worker runs plugin code.

## 5. Not yet done / not verified

1. **The protocol details on the other side of the worker were not read out**: the body of `hooks-worker.js` (the file inside bunfs) was not extracted separately; this report describes the behaviour of the **host side** (the main thread).
2. Constant values such as `vts` / `Ets` (the lengths of the two shared memory blocks), `c7e` / `Tjt` / `K7n` (slot indices) and `KKe` (the timeout base) were **not read out one by one**.
3. The semantics of the `inFlight.size === 1` constraint in `n0o`…`ePt()` (**inferred**: only one hook may be "active" at a time) was not verified at runtime.
4. Which side sets `marks` (the host or the worker) has not been confirmed.
5. Hot reload was not tested for real (it would change this machine's plugin state, and by discipline that is not done unilaterally).
