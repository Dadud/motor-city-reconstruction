#pragma once
#include <array>
#include <cstdint>
namespace mco {
// Image of 0x8c4730..0x8c49af. Identities remain original 32-bit values.
struct DiagnosticRuntime { std::array<std::uint32_t,160> words{}; std::uint32_t initialized{}; };
struct DiagnosticPlatform {
 // PRINT_CHANNEL / PRINT_DEVICE environment lookup and configuration parser remain explicit boundaries.
 std::uint32_t (*environment)(DiagnosticRuntime&,bool channel,void*){};
 void (*configure)(DiagnosticRuntime&,bool channel,std::uint32_t identity,void*){};
 void* user{};
};
void diagnostic_initialize(DiagnosticRuntime&,const DiagnosticPlatform&);
void diagnostic_channel_bits(DiagnosticRuntime&,std::uint32_t selector,std::uint32_t enabled);
void diagnostic_device_bits(DiagnosticRuntime&,std::uint32_t selector,std::uint32_t enabled);
void diagnostic_channel_configure(DiagnosticRuntime&,const DiagnosticPlatform&,std::uint32_t,std::uint32_t);
void diagnostic_device_configure(DiagnosticRuntime&,const DiagnosticPlatform&,std::uint32_t,std::uint32_t);
}
