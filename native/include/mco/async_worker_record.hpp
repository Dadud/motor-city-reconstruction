#pragma once

#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace mco {
struct StampedOperation {
    std::optional<std::vector<std::uint8_t>> record;
    std::uint32_t counter;
    std::uint32_t operation_id;
};
struct WorkerResultRecord {
    std::vector<std::uint8_t> record;
    bool completion_required;
};

// Generic local worker header, not a network packet. These helpers do not
// enqueue records, start threads or classify the result as success/failure.
StampedOperation stamp_operation(std::optional<std::span<const std::uint8_t>> record,
                                 std::uint32_t counter, bool tracked,
                                 bool manager_present = true);
WorkerResultRecord store_worker_result(std::span<const std::uint8_t> record,
                                      std::uint32_t result_bits);
} // namespace mco
