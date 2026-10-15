#pragma once
#include <array>
#include <cstdint>

namespace mco {
// Original 0x53e620 returns an unstored intermediate; do not narrow to float.
double startup_surface_factor(std::uint32_t selector, float speed);
// Original 0x550ed0: finalized inputs, not an integrated road-load simulation.
std::array<float, 135> startup_resistance_table(float mass, float coefficient,
                                              float area, std::uint32_t selector);
}
