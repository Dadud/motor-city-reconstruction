#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>

namespace mco {
inline constexpr std::size_t owned_part_slot_size = 1596;
using OwnedPartSlot = std::array<std::uint8_t, owned_part_slot_size>;

// Factors must be supplied explicitly; only an absent server record uses defaults.
struct PartValuationRates {
    double repair;
    double scrap;
    PartValuationRates(double repair_factor, double scrap_factor);
    static PartValuationRates from_reply(
        std::optional<std::span<const std::uint8_t>> record);
};

struct OwnedPartValuation {
    std::int32_t repair_cost;
    std::int32_t scrap_value;
    float wear_condition;
};

std::optional<OwnedPartValuation> calculate_owned_valuation(
    std::span<const std::uint8_t> slot, const PartValuationRates& rates);
OwnedPartSlot apply_owned_valuation(
    std::span<const std::uint8_t> slot, const PartValuationRates& rates);
} // namespace mco
