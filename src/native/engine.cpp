// =========================================================
// VEIL - engine.cpp
// Native secure in-memory storage engine.
//
// This replaces the original ram.dll / ctypes design with a single
// cross-platform pybind11 extension (compiles for Windows, Linux x86_64
// and Linux ARM64 / Raspberry Pi via the normal `pip install` build).
//
// Three bugs from the original implementation are fixed here, on purpose
// left documented in place so the fix is auditable:
//
//   BUG #1 - PANIC MODE timing logic was reading LAST_ACCESS *after*
//            already overwriting it with `now`, so the computed
//            "elapsed time since last access" was always ~0ms, which
//            made panic mode trigger on virtually every second read.
//            FIX: capture the previous timestamp BEFORE updating it.
//
//   BUG #2 - get() returned a raw `const char*` pointing directly into
//            the storage vector, AFTER releasing the mutex. Another
//            thread calling erase_entry()/clear_all() between the
//            unlock and ctypes reading that pointer on the Python side
//            produces a dangling-pointer read (undefined behaviour /
//            potential crash or info leak).
//            FIX: the returned py::bytes object is constructed *while
//            the mutex is still held*, so the copy is atomic with
//            respect to any concurrent mutation.
//
//   BUG #3 - the original ctypes interface used `const char*` /
//            `c_char_p` (NUL-terminated C strings) for ciphertext.
//            Any binary ciphertext containing an embedded 0x00 byte
//            (which AES-GCM output will routinely contain) was
//            silently truncated. FIX: length-prefixed py::bytes/
//            std::string is used everywhere - no implicit truncation.
// =========================================================
#include <pybind11/pybind11.h>
#include <algorithm>
#include <chrono>
#include <mutex>
#include <string>
#include <unordered_map>

#include "secure_mem.hpp"

namespace py = pybind11;

namespace veilt {

using Clock = std::chrono::steady_clock;

struct Entry {
    SecureBuffer data;
    long long access_count = 0;
    Clock::time_point last_access;
};

class SecureStore {
public:
    explicit SecureStore(int max_access_per_window = 30, int min_interval_ms = 5)
        : max_access_(max_access_per_window), min_interval_ms_(min_interval_ms) {
        harden_process();
    }

    // -----------------------------------------------------
    // store(): writes/overwrites an entry. Silently rejected
    // while panic mode is active (mirrors the original
    // "fail closed" behaviour).
    // -----------------------------------------------------
    void store(const std::string& id, const std::string& data) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (panic_mode_) {
            return;
        }
        Entry entry;
        entry.data.assign(data.begin(), data.end());
        entry.access_count = 0;
        entry.last_access = Clock::now();
        store_[id] = std::move(entry);
    }

    // -----------------------------------------------------
    // get(): returns the stored bytes, or None if absent.
    // While in panic mode, returns a decoy block instead of
    // raising - an attacker scripting against this API sees
    // a "successful" call with garbage data, not an error
    // that would tell them they've been detected.
    // -----------------------------------------------------
    py::object get(const std::string& id) {
        std::lock_guard<std::mutex> lock(mutex_);

        if (panic_mode_) {
            return py::bytes(FAKE_BLOCK);
        }

        auto it = store_.find(id);
        if (it == store_.end()) {
            return py::none();
        }

        Entry& entry = it->second;

        // --- BUG #1 FIX: snapshot the previous access time BEFORE
        // overwriting it with `now`. ---
        const Clock::time_point prev_access = entry.last_access;
        const auto now = Clock::now();
        const auto elapsed_ms =
            std::chrono::duration_cast<std::chrono::milliseconds>(now - prev_access).count();

        entry.access_count += 1;
        entry.last_access = now;

        // Skip the rapid-access heuristic on the very first read of a
        // freshly stored entry: there is no meaningful "previous" access
        // to compare against yet, so it can never be "too fast".
        const bool too_fast = (entry.access_count > 1) && (elapsed_ms < min_interval_ms_);
        const bool too_many = entry.access_count > max_access_;

        if (too_fast || too_many) {
            panic_mode_ = true;
            return py::bytes(FAKE_BLOCK);
        }

        // --- BUG #2 FIX: py::bytes is constructed here, still inside
        // the locked scope, so the copy is atomic with any concurrent
        // erase_entry()/clear_all() call from another thread. ---
        return py::bytes(reinterpret_cast<const char*>(entry.data.data()), entry.data.size());
    }

    bool erase_entry(const std::string& id) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = store_.find(id);
        if (it == store_.end()) {
            return false;
        }
        secure_wipe(it->second.data);
        store_.erase(it);
        return true;
    }

    void clear_all() {
        std::lock_guard<std::mutex> lock(mutex_);
        for (auto& kv : store_) {
            secure_wipe(kv.second.data);
        }
        store_.clear();
        panic_mode_ = false;
    }

    py::bytes fake_dump() const {
        return py::bytes(FAKE_BLOCK);
    }

    int size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return static_cast<int>(store_.size());
    }

    bool is_panic_mode() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return panic_mode_;
    }

    // Explicit, intentional re-arm after an operator has reviewed the
    // audit log and is confident the trigger was a false positive
    // (e.g. a legitimate tight retry loop). Never automatic.
    void reset_panic() {
        std::lock_guard<std::mutex> lock(mutex_);
        panic_mode_ = false;
    }

    void force_panic() {
        std::lock_guard<std::mutex> lock(mutex_);
        panic_mode_ = true;
    }

    bool raise_memory_lock_limit() {
        return veilt::raise_memlock_limit();
    }

private:
    static constexpr const char* FAKE_BLOCK = "VEIL::FAKE_DATA_BLOCK";

    static void secure_wipe(SecureBuffer& buf) {
        // Defense-in-depth overwrite ahead of the SecureAllocator's own
        // zero-on-free, in case the buffer is ever moved to a
        // non-SecureAllocator container in the future.
        std::fill(buf.begin(), buf.end(), static_cast<unsigned char>(0xFF));
        std::fill(buf.begin(), buf.end(), static_cast<unsigned char>(0x00));
        buf.clear();
        buf.shrink_to_fit();
    }

    mutable std::mutex mutex_;
    std::unordered_map<std::string, Entry> store_;
    bool panic_mode_ = false;
    int max_access_;
    int min_interval_ms_;
};

} // namespace veilt

PYBIND11_MODULE(_veilt_native, m) {
    m.doc() = "VEIL native secure-memory engine (Windows / Linux / ARM)";

    py::class_<veilt::SecureStore>(m, "SecureStore")
        .def(py::init<int, int>(),
             py::arg("max_access_per_window") = 30,
             py::arg("min_interval_ms") = 5)
        .def("store", &veilt::SecureStore::store, py::arg("id"), py::arg("data"))
        .def("get", &veilt::SecureStore::get, py::arg("id"))
        .def("erase_entry", &veilt::SecureStore::erase_entry, py::arg("id"))
        .def("clear_all", &veilt::SecureStore::clear_all)
        .def("fake_dump", &veilt::SecureStore::fake_dump)
        .def("size", &veilt::SecureStore::size)
        .def("is_panic_mode", &veilt::SecureStore::is_panic_mode)
        .def("reset_panic", &veilt::SecureStore::reset_panic)
        .def("force_panic", &veilt::SecureStore::force_panic)
        .def("raise_memory_lock_limit", &veilt::SecureStore::raise_memory_lock_limit);
}
