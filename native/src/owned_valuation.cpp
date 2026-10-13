#include "mco/owned_valuation.hpp"

#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
static_assert(sizeof(double) == 8 && std::numeric_limits<double>::is_iec559);

template<class T> T read_le(std::span<const std::uint8_t> bytes, std::size_t offset) {
    T value = 0;
    for (std::size_t i = 0; i < sizeof(T); ++i)
        value |= static_cast<T>(bytes[offset + i]) << (8 * i);
    return value;
}
std::int32_t read_i32(std::span<const std::uint8_t> bytes, std::size_t offset) {
    return std::bit_cast<std::int32_t>(read_le<std::uint32_t>(bytes, offset));
}
float f32(double value) {
    if (std::isfinite(value) && std::abs(value) > std::numeric_limits<float>::max())
        throw std::overflow_error("float32 valuation local overflow");
    return static_cast<float>(value);
}
// __ftol produces an int64; callers consume signed EAX. Invalid conversions
// produce x87's indefinite int64, whose low 32 bits are zero.
std::int32_t ftol_low32(double value) {
    constexpr double limit = 9223372036854775808.0;
    if (!std::isfinite(value) || value < -limit || value >= limit) return 0;
    auto wide = static_cast<std::int64_t>(std::trunc(value));
    auto low = static_cast<std::uint32_t>(static_cast<std::uint64_t>(wide));
    return std::bit_cast<std::int32_t>(low);
}
void validate(std::span<const std::uint8_t> slot, const PartValuationRates& rates) {
    if (slot.size() != owned_part_slot_size)
        throw std::invalid_argument("expected 1596-byte owned-part slot");
    if (!std::isfinite(rates.repair) || !std::isfinite(rates.scrap))
        throw std::invalid_argument("valuation factors must be finite");
}
void write_i32(OwnedPartSlot& slot, std::size_t offset, std::int32_t value) {
    auto bits = std::bit_cast<std::uint32_t>(value);
    for (std::size_t i = 0; i < 4; ++i)
        slot[offset + i] = static_cast<std::uint8_t>(bits >> (8 * i));
}
} // namespace

PartValuationRates::PartValuationRates(double repair_factor, double scrap_factor)
    : repair(repair_factor), scrap(scrap_factor) {
    if (!std::isfinite(repair) || !std::isfinite(scrap))
        throw std::invalid_argument("valuation factors must be finite");
}
PartValuationRates PartValuationRates::from_reply(
    std::optional<std::span<const std::uint8_t>> record) {
    if (!record) return {0.1, 0.75};
    if (record->size() != 118 || read_le<std::uint16_t>(*record, 0) != 0x186)
        throw std::invalid_argument("expected server data reply 0x186");
    return {std::bit_cast<double>(read_le<std::uint64_t>(*record, 0x1e)),
            std::bit_cast<double>(read_le<std::uint64_t>(*record, 0x26))};
}

std::optional<OwnedPartValuation> calculate_owned_valuation(
    std::span<const std::uint8_t> slot, const PartValuationRates& rates) {
    validate(slot, rates);
    if (!read_le<std::uint32_t>(slot, 0x5f8) || !read_le<std::uint32_t>(slot, 0x1e3))
        return std::nullopt;
    const auto price = read_i32(slot, 0x1eb);
    const auto maximum = read_i32(slot, 0x1ef);
    const auto damage = read_i32(slot, 0x610);
    const auto wear = read_i32(slot, 0x614);
    const float condition = maximum == 0 ? 1.0f : f32(1.0 - static_cast<double>(wear) / maximum);
    constexpr double percent = static_cast<double>(std::bit_cast<float>(std::uint32_t{0x3c23d70a}));
    const auto repair = damage == 0 ? 0 : std::max(1, ftol_low32(
        (rates.repair * price) * (damage * percent) + 0.5));
    const auto base = ftol_low32((rates.scrap * price) * condition + 0.5);
    const double remainder = static_cast<double>(base) - f32(repair);
    auto scrap = remainder >= 0 ? ftol_low32(remainder) : 0;
    const auto identifier = read_le<std::uint32_t>(slot, 0);
    if (identifier >= 20001 && identifier <= 20999) {
        const float body = std::bit_cast<float>(read_le<std::uint32_t>(slot, 0x454));
        if (!std::isfinite(body)) throw std::invalid_argument("body physics Val11 must be finite");
        scrap = ftol_low32(rates.scrap * body + scrap);
    }
    return OwnedPartValuation{repair, scrap, condition};
}

OwnedPartSlot apply_owned_valuation(
    std::span<const std::uint8_t> slot, const PartValuationRates& rates) {
    const auto valuation = calculate_owned_valuation(slot, rates);
    OwnedPartSlot output;
    std::copy(slot.begin(), slot.end(), output.begin());
    if (valuation) {
        write_i32(output, 0x62c, valuation->repair_cost);
        write_i32(output, 0x630, valuation->scrap_value);
    }
    return output;
}
} // namespace mco
