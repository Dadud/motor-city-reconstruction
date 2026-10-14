#include "mco/async_worker_record.hpp"

#include <stdexcept>

namespace mco {
namespace {
void validate(std::span<const std::uint8_t> record) {
    if (record.size() < 12)
        throw std::invalid_argument("worker record requires complete 12-byte header");
}
std::uint32_t read(std::span<const std::uint8_t> record, std::size_t offset) {
    std::uint32_t bits = 0;
    for (std::size_t i = 0; i < 4; ++i)
        bits |= static_cast<std::uint32_t>(record[offset + i]) << (8 * i);
    return bits;
}
void write(std::vector<std::uint8_t>& record, std::size_t offset, std::uint32_t bits) {
    for (std::size_t i = 0; i < 4; ++i)
        record[offset + i] = static_cast<std::uint8_t>(bits >> (8 * i));
}
} // namespace

StampedOperation stamp_operation(std::optional<std::span<const std::uint8_t>> record,
                                 std::uint32_t counter, bool tracked, bool manager_present) {
    StampedOperation output{std::nullopt, counter, 0};
    if (!record) return output;
    output.record.emplace(record->begin(), record->end());
    // These original early returns precede record-header access.
    if (!manager_present) return output;
    validate(*record);
    if (tracked) {
        ++output.counter;
        if (output.counter == 0) output.counter = 1;
        output.operation_id = output.counter;
    }
    write(*output.record, 4, output.operation_id);
    return output;
}
WorkerResultRecord store_worker_result(std::span<const std::uint8_t> record,
                                      std::uint32_t result_bits) {
    validate(record);
    WorkerResultRecord output{{record.begin(), record.end()}, read(record, 4) != 0};
    write(output.record, 8, result_bits);
    return output;
}
} // namespace mco
