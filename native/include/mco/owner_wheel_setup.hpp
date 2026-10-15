#pragma once
#include <array>
#include <cstddef>
#include <span>
namespace mco {
using StartupOwnerImage=std::array<std::byte,0x2000>;
// Internal recovery images. Prior geometry and assembly provenance are required.
StartupOwnerImage adjust_owner_stance(std::span<const std::byte> owner);
StartupOwnerImage initialize_owner_wheels(std::span<const std::byte> owner,
    std::span<const std::byte> configuration,bool assembly_finalized);
}
