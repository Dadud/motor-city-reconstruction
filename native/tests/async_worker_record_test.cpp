#include "mco/async_worker_record.hpp"

#include <array>
#include <stdexcept>

namespace {
void check(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
void put(std::vector<std::uint8_t>& bytes, std::size_t offset, std::uint32_t value) {
    for (std::size_t i = 0; i < 4; ++i) bytes[offset + i] = static_cast<std::uint8_t>(value >> (8 * i));
}
std::uint32_t read(std::span<const std::uint8_t> bytes, std::size_t offset) {
    std::uint32_t value = 0;
    for (std::size_t i = 0; i < 4; ++i) value |= static_cast<std::uint32_t>(bytes[offset + i]) << (8 * i);
    return value;
}
template<class F> void reject(F function) {
    bool rejected = false;
    try { function(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "incomplete worker header accepted");
}
} // namespace

int main() {
    std::vector<std::uint8_t> raw(268);
    put(raw, 0, 7); put(raw, 4, 0xaaaaaaaau); put(raw, 8, 0xbbbbbbbbu);
    for (std::size_t i = 12; i < raw.size(); ++i) raw[i] = static_cast<std::uint8_t>(i - 12);
    const std::array<std::uint32_t, 4> counters{0,1,0xfffffffeu,0xffffffffu};
    const std::array<std::uint32_t, 4> expected{1,2,0xffffffffu,1};
    const auto original = raw;
    for (std::size_t i = 0; i < counters.size(); ++i) {
        const auto result = mco::stamp_operation(std::span<const std::uint8_t>{raw}, counters[i], true);
        check(result.counter == expected[i] && result.operation_id == expected[i] && result.record.has_value(),
              "tracked counter wrapping mismatch");
        check(read(*result.record, 4) == expected[i], "operation ID not stored little-endian");
        for (std::size_t offset = 0; offset < raw.size(); ++offset)
            if (offset < 4 || offset >= 8) check((*result.record)[offset] == raw[offset], "unrelated operation byte changed");
    }
    const auto untracked = mco::stamp_operation(std::span<const std::uint8_t>{raw}, 0xffffffffu, false);
    check(untracked.counter == 0xffffffffu && untracked.operation_id == 0 && read(*untracked.record, 4) == 0,
          "untracked counter or ID mismatch");
    const auto no_manager = mco::stamp_operation(std::span<const std::uint8_t>{raw}, 9, true, false);
    check(no_manager.counter == 9 && no_manager.operation_id == 0 && *no_manager.record == raw,
          "missing manager changed record");
    for (auto manager : {false, true}) {
        const auto null = mco::stamp_operation(std::nullopt, 9, true, manager);
        check(null.counter == 9 && null.operation_id == 0 && !null.record, "null record early return mismatch");
    }
    for (auto id : {0u,1u,0xffffffffu}) {
        auto record = raw; put(record, 4, id);
        const auto result = mco::store_worker_result(record, 0xfffffffau);
        check(result.completion_required == (id != 0) && read(result.record, 8) == 0xfffffffau,
              "result bits or completion gating mismatch");
        for (std::size_t offset = 0; offset < record.size(); ++offset)
            if (offset < 8 || offset >= 12) check(result.record[offset] == record[offset], "unrelated result byte changed");
    }
    check(raw == original, "input record modified");
    for (auto size : {0u, 11u}) {
        const auto short_record = std::span<const std::uint8_t>{raw}.first(size);
        reject([&] { mco::stamp_operation(short_record, 0, true); });
        reject([&] { mco::store_worker_result(short_record, 0); });
        const auto skipped = mco::stamp_operation(short_record, 9, true, false);
        check(skipped.record->size() == size && skipped.counter == 9 && skipped.operation_id == 0,
              "missing manager did not return before header access");
    }
}
