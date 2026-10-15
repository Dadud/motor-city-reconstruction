#pragma once
#include "mco/owner_wheel_setup.hpp"
#include <cstdint>

namespace mco {
// Internal 0x51ed40/0x51f440 selectors; distinct from catalogue body selectors.
enum class BodyShape : unsigned { box, pyramid, wedge, cylinder, sphere };
using BodySamples = std::array<std::array<float,3>,22>;
BodySamples body_samples(BodyShape shape, std::array<float,3> half_extents);
BodySamples customize_body_samples(unsigned catalogue_selector, const BodySamples& samples);
// Preserves all observations above the original 0x418-byte base object.
StartupOwnerImage construct_body(std::span<const std::byte> owner,
    std::uint32_t identity, float mass, std::array<float,3> half_extents,
    BodyShape shape, std::uint32_t material);
// 0x43ab88..0x43acb1, after model assembly, before the main owner initializer.
StartupOwnerImage prepare_startup_body(std::span<const std::byte> owner,
    std::span<const std::byte> configuration,std::array<float,3> half_extents,
    std::uint32_t identity,bool assembly_finalized);
}
