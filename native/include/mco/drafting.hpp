#pragma once
#include <array>
#include <cstdint>
#include <optional>
#include <vector>

namespace mco {
struct DraftVehicle {
    std::int64_t identifier;
    std::array<double,3> position;
    std::array<double,9> basis;
    std::array<double,3> half_extents;
    std::array<double,3> wake_origin{};
    std::array<std::array<double,3>,4> wake_normals{};
};
struct DraftingOutput {
    double factor;
    std::vector<DraftVehicle> vehicles;
    std::optional<std::int64_t> selected_vehicle;
    bool inside_wake;
};
// Preserve candidate order: the first qualifying candidate receives wake writes.
DraftingOutput calculate_drafting(std::int64_t identifier,std::vector<DraftVehicle> vehicles);
}
