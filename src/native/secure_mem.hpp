// =========================================================
// VEIL - secure_mem.hpp
// Cross-platform low-level memory protection primitives.
//
// Goals:
//   - Pin secret-holding pages in physical RAM (prevents the OS from
//     swapping them to disk, where they could survive long after the
//     process exits and be recovered forensically).
//   - Guarantee secrets are overwritten (not just "freed") the instant
//     they are no longer needed.
//   - Make accidental process core dumps / crash dumps not contain
//     secret material.
//
// Platforms: Windows (MSVC/MinGW), Linux (incl. ARM / Raspberry Pi),
// and a safe no-op fallback for anything else.
// =========================================================
#pragma once

#include <cstddef>
#include <cstdint>
#include <new>
#include <vector>

#if defined(_WIN32)
    #define WIN32_LEAN_AND_MEAN
    #include <windows.h>
#else
    #include <sys/mman.h>
    #include <unistd.h>
    #if defined(__linux__)
        #include <sys/prctl.h>
        #include <sys/resource.h>
    #endif
#endif

namespace veil {

// ---------------------------------------------------------
// secure_zero: overwrite memory in a way the compiler cannot
// optimize away (unlike a plain memset, which dead-store
// elimination is legally allowed to remove if the buffer is
// about to be freed).
// ---------------------------------------------------------
inline void secure_zero(void* ptr, std::size_t len) {
    if (!ptr || len == 0) return;
#if defined(_WIN32)
    SecureZeroMemory(ptr, len);
#else
    volatile unsigned char* p = reinterpret_cast<volatile unsigned char*>(ptr);
    while (len--) {
        *p++ = 0;
    }
#endif
}

// ---------------------------------------------------------
// lock_memory / unlock_memory: pin pages so the OS will not
// page them out to swap/disk. Best-effort: unprivileged
// processes have a small quota (RLIMIT_MEMLOCK on Linux,
// the working-set minimum on Windows) - failure is reported
// but must never crash the caller. Run elevated (admin/root)
// to raise these limits via raise_memlock_limit().
// ---------------------------------------------------------
inline bool lock_memory(void* ptr, std::size_t len) {
    if (!ptr || len == 0) return false;
#if defined(_WIN32)
    return VirtualLock(ptr, len) != 0;
#else
    return mlock(ptr, len) == 0;
#endif
}

inline void unlock_memory(void* ptr, std::size_t len) {
    if (!ptr || len == 0) return;
#if defined(_WIN32)
    VirtualUnlock(ptr, len);
#else
    munlock(ptr, len);
#endif
}

// ---------------------------------------------------------
// harden_process: best-effort process-wide anti-forensic
// hardening, applied once when the native engine starts.
//   Linux   : disable core dumps (PR_SET_DUMPABLE + RLIMIT_CORE=0)
//             so `gdb --pid` / crash handlers cannot read our heap.
//   Windows : normal user processes do not produce automatic
//             crash dumps, so there is nothing extra required here
//             by default (WER dumps are opt-in and handled at the
//             OS/policy level, outside this process's control).
// ---------------------------------------------------------
inline bool harden_process() {
#if defined(__linux__)
    bool ok = true;
    if (prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) != 0) {
        ok = false;
    }
    struct rlimit rl;
    rl.rlim_cur = 0;
    rl.rlim_max = 0;
    if (setrlimit(RLIMIT_CORE, &rl) != 0) {
        ok = false;
    }
    return ok;
#else
    return true;
#endif
}

// ---------------------------------------------------------
// raise_memlock_limit: only succeeds when running with
// sufficient privilege (root / CAP_IPC_LOCK on Linux). This
// is what the Vault(admin=True) / --admin CLI flag unlocks:
// instead of being capped at a few dozen KB of lockable
// memory, secrets of any reasonable size stay pinned in RAM.
// ---------------------------------------------------------
inline bool raise_memlock_limit() {
#if defined(__linux__)
    struct rlimit rl;
    rl.rlim_cur = RLIM_INFINITY;
    rl.rlim_max = RLIM_INFINITY;
    return setrlimit(RLIMIT_MEMLOCK, &rl) == 0;
#else
    // Windows equivalent (SeLockMemoryPrivilege / working-set quota) is
    // adjusted from the Python side (veil.elevate.harden_token_privileges)
    // since it requires the Win32 security/token APIs, not just the CRT.
    return false;
#endif
}

// ---------------------------------------------------------
// SecureAllocator: a drop-in std-compatible allocator that
// mlocks/VirtualLocks every allocation it makes and securely
// zeroes + unlocks the memory the instant it is deallocated.
// Use it for any std::vector/std::basic_string that may hold
// plaintext or ciphertext secrets.
// ---------------------------------------------------------
template <class T>
struct SecureAllocator {
    using value_type = T;

    SecureAllocator() noexcept = default;
    template <class U>
    SecureAllocator(const SecureAllocator<U>&) noexcept {}

    T* allocate(std::size_t n) {
        if (n > static_cast<std::size_t>(-1) / sizeof(T)) {
            throw std::bad_alloc();
        }
        void* p = ::operator new(n * sizeof(T));
        lock_memory(p, n * sizeof(T));  // best-effort, failure is non-fatal
        return static_cast<T*>(p);
    }

    void deallocate(T* p, std::size_t n) noexcept {
        if (!p) return;
        secure_zero(p, n * sizeof(T));
        unlock_memory(p, n * sizeof(T));
        ::operator delete(p);
    }

    template <class U>
    bool operator==(const SecureAllocator<U>&) const noexcept { return true; }
    template <class U>
    bool operator!=(const SecureAllocator<U>&) const noexcept { return false; }
};

using SecureBuffer = std::vector<unsigned char, SecureAllocator<unsigned char>>;

} // namespace veil
