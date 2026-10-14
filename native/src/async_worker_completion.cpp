#include "mco/async_worker_completion.hpp"

#include <algorithm>
#include <bit>
#include <stdexcept>
#include <utility>

namespace mco {
namespace {
std::uint32_t read32(const WorkerRecord& record, std::size_t offset) {
    std::uint32_t bits = 0;
    for (std::size_t i = 0; i < 4; ++i)
        bits |= static_cast<std::uint32_t>(record[offset + i]) << (8 * i);
    return bits;
}
}

WorkerRecord worker_record_from_bytes(std::span<const std::uint8_t> bytes) {
    if (bytes.size() != worker_record_size)
        throw std::invalid_argument("completion requires exact worker record size");
    WorkerRecord result;
    std::copy(bytes.begin(), bytes.end(), result.begin());
    return result;
}

WorkerCompletionQueue::WorkerCompletionQueue(std::vector<WorkerRecord> records)
    : records_(std::move(records)) {}

const std::vector<WorkerRecord>& WorkerCompletionQueue::records() const noexcept { return records_; }
void WorkerCompletionQueue::append(const WorkerRecord& record) { records_.push_back(record); }

CompletionQuery WorkerCompletionQueue::query(std::uint32_t operation_id, bool copy_output) {
    if (operation_id == 0)
        throw std::invalid_argument("completion query requires a nonzero operation ID");
    const auto found = std::find_if(records_.begin(), records_.end(), [operation_id](const WorkerRecord& record) {
        return read32(record, 4) == operation_id;
    });
    if (found == records_.end()) return {false, std::nullopt};
    CompletionQuery result{true, std::nullopt};
    if (copy_output) result.record = *found;
    records_.erase(found);
    return result;
}

CompletedOperation CompletedOperation::from_record(const WorkerRecord& record) {
    CompletedOperation result{read32(record, 0), read32(record, 4),
                              std::bit_cast<std::int32_t>(read32(record, 8)), {}};
    std::copy(record.begin() + 12, record.end(), result.argument.begin());
    return result;
}
} // namespace mco
