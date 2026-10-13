# 附：macOS seatbelt 沙箱 profile 的生成代码（JS 侧，逐字片段）

> 位置：`raw/chunks2/0205__chunk-5vadtxaa.js` @730440（函数 `PV()`，同文件另有 `_a()`/`RV()`/`kV()` 负责拼 file-read/file-write 规则）

> 说明：profile 由 JS 组装成字符串数组，再交给 `sandbox-exec` 启动子进程；下面是从代码里抽出的逐字片段（按出现顺序，已去重相邻重复）。

```scheme
(version 1)
; Essential permissions - based on Chrome sandbox policy
; Process permissions
(allow process-exec)
(allow process-fork)
(allow process-info* (target same-sandbox))
(allow signal (target same-sandbox))
(allow mach-priv-task-port (target same-sandbox))
; User preferences
(allow user-preference-read)
; Mach IPC - specific services only (no wildcard)
(allow mach-lookup
(allow appleevent-send)
; Launch Services open requests need the lsopen operation plus, on
; macOS 14/15, coreservicesd and the quarantine resolver - without
; these open fails with -10822 kLSServerCommunicationErr or -54
(allow lsopen)
; User-specified XPC/Mach services
; POSIX IPC - shared memory
(allow ipc-posix-shm)
; POSIX IPC - semaphores for Python multiprocessing
(allow ipc-posix-sem)
; IOKit - specific operations only
(allow iokit-open
; IOKit properties
(allow iokit-get-properties)
; Specific safe system-sockets, doesn't allow network access
(allow system-socket (require-all (socket-domain AF_SYSTEM) (socket-protocol 2)))
; sysctl - specific sysctls only
(allow sysctl-read
; V8 thread calculations
(allow sysctl-write
; Distributed notifications
(allow distributed-notification-post)
; Specific mach-lookup permissions for security operations
; File I/O on device files
(allow file-ioctl file-read-data file-write-data
```
