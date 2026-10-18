#pragma once
#include "mco/input_key_queue.hpp"
namespace mco {
// Named observations of discontiguous original globals, not an original struct.
enum class StartupGlobal:unsigned {diagnostic_callback,diagnostic_file,diagnostic_line,graphics_ready,auxiliary_ready,configuration,driver_name,driver_loaded,external_driver,width,height,depth,mode,flags,policy_callback,count};
inline constexpr unsigned startup_global_count=static_cast<unsigned>(StartupGlobal::count);
struct StartupState {
    InputKeyQueue& queue;
    std::span<std::uint32_t,startup_global_count> globals;
    std::uint32_t& at(StartupGlobal field){return globals[static_cast<unsigned>(field)];}
};
using StartupInvoke=std::uint32_t (*)(StartupState&,std::uint32_t identity,std::span<const std::uint32_t> arguments,void* user);
using StartupDriverNonempty=bool (*)(std::uint32_t identity,void* user);
struct StartupPlatform {StartupInvoke invoke{};StartupDriverNonempty driver_nonempty{};void* user{};};
void startup_window_policy(StartupState&,std::uint32_t flag,std::uint32_t callback);
}
