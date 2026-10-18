#pragma once
#include <array>
#include <cstdint>
#include <span>
#include "mco/cleanup_registry_state.hpp"
namespace mco {
struct StartupThreadRuntime {
 // 0xb2bbc4..0xb2bbdc followed by 0xb35fd0; identities are original words.
 std::array<std::uint32_t,8> words{};
 std::uint32_t& handle(){return words[0];}
 std::uint32_t& thread_id(){return words[1];}
 std::uint32_t& initialized(){return words[2];}
 std::uint32_t& cleanup_registered(){return words[3];}
 std::uint32_t& allocation(){return words[4];}
 std::uint32_t& capacity(){return words[5];}
 std::uint32_t& lock(){return words[6];}
 std::uint32_t& page_size(){return words[7];}
};
// 0x6bd640 lock-pool acquisition and true Windows resource ownership remain boundaries.
// Calls: 1 lock acquisition, 2 page size query, 3 VirtualAlloc, 4 memory clear,
// 5 GetCurrentThreadId, 6 GetCurrentProcess, 7 GetCurrentThread, 8 DuplicateHandle.
using StartupThreadInvoke=std::uint32_t (*)(StartupThreadRuntime&,std::uint32_t,std::span<const std::uint32_t>,void*);
struct StartupThreadPlatform {StartupThreadInvoke invoke{};void* user{};};
std::uint32_t startup_thread_allocate(StartupThreadRuntime&,const StartupThreadPlatform&,std::uint32_t& bytes);
std::uint32_t startup_thread_capacity(StartupThreadRuntime&,const StartupThreadPlatform&,std::uint32_t count);
void startup_thread_initialize(StartupThreadRuntime&,CleanupRegistry&,const StartupThreadPlatform&,std::uint32_t count);
}
