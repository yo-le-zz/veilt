#include <unordered_map>
#include <string>
#include <vector>
#include <cstring>
#include <mutex>
#include <chrono>
#include <algorithm>

#if defined(_WIN32) || defined(_WIN64)
#  define RAM_API __declspec(dllexport)
#else
#  define RAM_API __attribute__((visibility("default")))
#endif

extern "C" {

std::unordered_map<std::string, std::vector<char>> RAM_STORAGE;
std::unordered_map<std::string, int> ACCESS_COUNT;
std::unordered_map<std::string, std::chrono::steady_clock::time_point> LAST_ACCESS;
std::mutex ram_mutex;
bool PANIC_MODE = false;

// =========================================================
// WRITE MEMORY
// =========================================================
RAM_API void store(const char* id, const char* data, int size) {
    std::lock_guard<std::mutex> lock(ram_mutex);

    if (PANIC_MODE) {
        return; // Silent rejection in panic mode
    }

    std::string key(id);
    std::vector<char> buffer(data, data + size);
    RAM_STORAGE[key] = buffer;
    
    // Reset access counters on new data
    ACCESS_COUNT[key] = 0;
    LAST_ACCESS[key] = std::chrono::steady_clock::now();
}

// =========================================================
// READ MEMORY
// =========================================================
RAM_API const char* get(const char* id) {
    std::lock_guard<std::mutex> lock(ram_mutex);

    if (PANIC_MODE) {
        return "VEIL::FAKE_DATA_BLOCK";
    }

    std::string key(id);
    auto it = RAM_STORAGE.find(key);
    if (it == RAM_STORAGE.end()) return nullptr;

    // Update access monitoring
    ACCESS_COUNT[key]++;
    LAST_ACCESS[key] = std::chrono::steady_clock::now();
    
    // Check for suspicious access patterns
    auto now = std::chrono::steady_clock::now();
    auto time_diff = std::chrono::duration_cast<std::chrono::milliseconds>(now - LAST_ACCESS[key]).count();
    
    if (ACCESS_COUNT[key] > 10 || time_diff < 100) {
        PANIC_MODE = true;
        return "VEIL::FAKE_DATA_BLOCK";
    }

    return it->second.data();
}

// =========================================================
// DELETE MEMORY (SECURE WIPE)
// =========================================================
RAM_API void erase_entry(const char* id) {
    std::lock_guard<std::mutex> lock(ram_mutex);

    std::string key(id);
    auto it = RAM_STORAGE.find(key);
    if (it != RAM_STORAGE.end()) {

        // overwrite avant suppression
        std::fill(it->second.begin(), it->second.end(), 0x00);
        std::fill(it->second.begin(), it->second.end(), 0xFF);

        RAM_STORAGE.erase(it);
        
        // Clean up access tracking
        ACCESS_COUNT.erase(key);
        LAST_ACCESS.erase(key);
    }
}

// =========================================================
// CLEAR ALL (panic wipe)
// =========================================================
RAM_API void clear_all() {
    std::lock_guard<std::mutex> lock(ram_mutex);

    for (auto& pair : RAM_STORAGE) {
        std::fill(pair.second.begin(), pair.second.end(), 0x00);
    }

    RAM_STORAGE.clear();
    ACCESS_COUNT.clear();
    LAST_ACCESS.clear();
    PANIC_MODE = false;
}

// =========================================================
// FAKE DUMP RESPONSE (ANTI-FORENSIC)
// =========================================================
RAM_API const char* fake_dump() {
    return "VEIL::ACCESS_DENIED::ANTI_DUMP_TRIGGERED";
}

// =========================================================
// MEMORY STATUS
// =========================================================
RAM_API int size() {
    return RAM_STORAGE.size();
}

// =========================================================
// PANIC MODE STATUS
// =========================================================
RAM_API int is_panic_mode() {
    return PANIC_MODE ? 1 : 0;
}

}