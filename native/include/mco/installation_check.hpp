#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace mco {
struct InstallationState {
    std::span<std::byte, 8320> paths;
    std::array<std::uint32_t, 4> flags{}; // level, CD-scan bypass, minimal, CD count
};
struct InstallationRow { std::uint32_t identity; std::uint32_t type; };
struct InstallationLocals {
    std::array<std::byte, 260> root{};
    std::array<std::byte, 788> candidate{};
    std::array<std::byte, 260> cdroot{};
    std::uint32_t level{};
};
struct InstallationCall {
    std::uint32_t id;
    std::span<const std::uint32_t> args;
    std::span<std::byte> destination;
    InstallationLocals& locals;
};
using InstallationInvoke = std::uint32_t (*)(InstallationState&, const InstallationCall&, void*);
struct InstallationPlatform { InstallationInvoke invoke{}; void* user{}; };

// Models returning helper/API boundaries. SEH, host registry, drives and files
// remain explicit; rows must terminate within the original 32-slot table.
std::uint32_t installation_check(InstallationState&, std::span<const InstallationRow>,
                                 const InstallationPlatform&);
}
