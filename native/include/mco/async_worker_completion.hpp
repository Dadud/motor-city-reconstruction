#pragma once

#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace mco {
inline constexpr std::size_t worker_record_size = 0x80c;
using WorkerRecord = std::array<std::uint8_t, worker_record_size>;

[[nodiscard]] WorkerRecord worker_record_from_bytes(std::span<const std::uint8_t> bytes);

struct CompletionQuery {
    bool found;
    std::optional<WorkerRecord> record;
};

// Single-owner record queue. No implicit locks, host pointers or task scheduling.
class WorkerCompletionQueue {
public:
    explicit WorkerCompletionQueue(std::vector<WorkerRecord> records = {});
    [[nodiscard]] const std::vector<WorkerRecord>& records() const noexcept;
    void append(const WorkerRecord& record);
    [[nodiscard]] CompletionQuery query(std::uint32_t operation_id, bool copy_output = true);
private:
    std::vector<WorkerRecord> records_;
};

struct CompletedOperation {
    std::uint32_t kind;
    std::uint32_t operation_id;
    std::int32_t result;
    std::array<std::uint8_t, 2048> argument;
    [[nodiscard]] static CompletedOperation from_record(const WorkerRecord& record);
};
} // namespace mco
