> English version. 中文原版：[seatbelt-profile.md](seatbelt-profile.md)

# Appendix: the code that generates the macOS seatbelt sandbox profile (JS side, verbatim fragments)

> Location: `raw/chunks2/0205__chunk-5vadtxaa.js` @730440 (function `PV()`; the same file also has `_a()`/`RV()`/`kV()`, which assemble the file-read/file-write rules)

> Note: the profile is assembled by JS into an array of strings and then handed to `sandbox-exec` to launch the child process; below are the verbatim fragments extracted from the code (in order of appearance, with adjacent duplicates removed).

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
