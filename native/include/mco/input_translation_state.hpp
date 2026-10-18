#pragma once
#include "mco/layouts.hpp"
#include <span>
#include <cstdint>
#include <stdexcept>
namespace mco {
struct InputTranslationState;
using InputDeviceState=std::span<const std::byte> (*)(InputTranslationState&,std::uint32_t kind,void* user);
// Must not return: the original selected child calls ExitProcess(0).
using InputExitRequest=void (*)(InputTranslationState&,std::uint32_t code,void* user);
struct InputTranslationState {
    std::uint32_t caps,escape_exits;
    // Five original planes start 91 bytes apart; extra mapped tail supports byte scans.
    std::span<const std::byte,scan_translation_tables::size> tables;
    InputDeviceState get_state{};
    InputExitRequest exit_request{};
    void* user{};
};
}
