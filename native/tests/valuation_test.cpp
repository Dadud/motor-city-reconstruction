#include "mco/owned_valuation.hpp"

#include <bit>
#include <limits>
#include <stdexcept>
#include <string>

namespace {
void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
template<class T, class Container> void put(Container& bytes, std::size_t offset, T bits) {
    for (std::size_t i = 0; i < sizeof(T); ++i)
        bytes[offset + i] = static_cast<std::uint8_t>(bits >> (8 * i));
}
mco::OwnedPartSlot slot(std::uint32_t id = 160001, std::int32_t price = 500,
                       std::int32_t maximum = 1000, std::int32_t damage = 20,
                       std::int32_t wear = 250, float body = 0) {
    mco::OwnedPartSlot result{};
    put(result, 0, id);
    put(result, 0x1e3, std::uint32_t{123});
    put(result, 0x1eb, std::bit_cast<std::uint32_t>(price));
    put(result, 0x1ef, std::bit_cast<std::uint32_t>(maximum));
    put(result, 0x454, std::bit_cast<std::uint32_t>(body));
    put(result, 0x5f8, std::uint32_t{42});
    put(result, 0x610, std::bit_cast<std::uint32_t>(damage));
    put(result, 0x614, std::bit_cast<std::uint32_t>(wear));
    put(result, 0x62c, std::uint32_t{999});
    put(result, 0x630, std::uint32_t{888});
    return result;
}
template<class F> void invalid(F function) {
    bool rejected = false;
    try { function(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid data was accepted");
}
} // namespace

int main() {
    const mco::PartValuationRates rates{0.1, 0.75};
    const auto source = slot();
    const auto normal = mco::calculate_owned_valuation(source, rates).value();
    check(normal.repair_cost == 10 && normal.scrap_value == 271 && normal.wear_condition == 0.75f,
          "baseline valuation mismatch");
    const auto output = mco::apply_owned_valuation(source, rates);
    for (std::size_t i = 0; i < source.size(); ++i)
        if (i < 0x62c || i >= 0x634) check(output[i] == source[i], "unrelated slot byte changed");
    check(output[0x62c] == 10 && output[0x630] == 15 && output[0x631] == 1,
          "stored valuation mismatch");
    check(mco::calculate_owned_valuation(slot(160001, 25, 1000, 100, 0), rates)->repair_cost == 2,
          "float32 percentage rounding lost");
    const auto zero = mco::calculate_owned_valuation(slot(160001, 500, 0, 0, 500), rates).value();
    check(zero.repair_cost == 0 && zero.scrap_value == 375 && zero.wear_condition == 1,
          "zero wear limit branch mismatch");
    const auto worn = mco::calculate_owned_valuation(slot(160001, 1, 1000, 1, 2000), rates).value();
    check(worn.repair_cost == 1 && worn.scrap_value == 0, "repair minimum or scrap floor mismatch");
    for (auto id : {20000u, 20001u, 20999u, 21000u}) {
        const auto result = mco::calculate_owned_valuation(slot(id, 500, 1000, 20, 250, 123.25f), rates);
        check(result->scrap_value == ((id == 20001 || id == 20999) ? 363 : 271),
              "body bonus type boundary mismatch");
    }
    // The body bonus is added after the floor and is not clamped again.
    check(mco::calculate_owned_valuation(slot(20001, 500, 1000, 0, 0, -1000), rates)->scrap_value == -375,
          "negative body bonus was incorrectly clamped");
    // x87 __ftol returns int64, and signed low EAX is used by this caller.
    check(mco::calculate_owned_valuation(slot(160001, 1, 0, 100, 0), {4294967298.0, 0})->repair_cost == 1,
          "signed low32 conversion mismatch");
    constexpr double percent = static_cast<double>(std::bit_cast<float>(std::uint32_t{0x3c23d70a}));
    check(mco::calculate_owned_valuation(slot(160001, 1, 0, 1, 0), {4294967298.0 / percent, 0})->repair_cost == 2,
          "positive low32 wrap mismatch");
    check(mco::calculate_owned_valuation(slot(160001, 1, 0, 100, 0), {1e300, 1e300})->scrap_value == 0,
          "indefinite conversion mismatch");
    auto empty = source;
    put(empty, 0x5f8, std::uint32_t{0});
    check(!mco::calculate_owned_valuation(empty, rates), "empty identity valued");
    check(mco::apply_owned_valuation(empty, rates) == empty, "empty identity modified");
    put(empty, 0x5f8, std::uint32_t{42});
    put(empty, 0x1e3, std::uint32_t{0});
    check(!mco::calculate_owned_valuation(empty, rates), "missing brand valued");
    const auto fallback = mco::PartValuationRates::from_reply(std::nullopt);
    check(fallback.repair == 0.1 && fallback.scrap == 0.75, "absent reply defaults mismatch");
    std::array<std::uint8_t, 118> reply{};
    put(reply, 0, std::uint16_t{0x186});
    put(reply, 0x1e, std::bit_cast<std::uint64_t>(0.2));
    put(reply, 0x26, std::bit_cast<std::uint64_t>(0.65));
    auto decoded = mco::PartValuationRates::from_reply(std::span<const std::uint8_t>{reply});
    check(decoded.repair == 0.2 && decoded.scrap == 0.65, "LE server factor decoding mismatch");
    put(reply, 0x1e, std::uint64_t{0});
    put(reply, 0x26, std::uint64_t{0});
    decoded = mco::PartValuationRates::from_reply(std::span<const std::uint8_t>{reply});
    check(decoded.repair == 0 && decoded.scrap == 0, "zero server factors replaced with defaults");
    put(reply, 0, std::uint16_t{0x187});
    invalid([&] { mco::PartValuationRates::from_reply(std::span<const std::uint8_t>{reply}); });
    invalid([&] { mco::calculate_owned_valuation(std::span<const std::uint8_t>{source}.first(1595), rates); });
    invalid([] { mco::PartValuationRates{std::numeric_limits<double>::quiet_NaN(), 0.75}; });
    invalid([&] { mco::calculate_owned_valuation(
        slot(20001, 500, 1000, 20, 250, std::numeric_limits<float>::infinity()), rates); });
}
