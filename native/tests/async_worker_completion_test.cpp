#include "mco/async_worker_completion.hpp"

#include <iostream>
#include <limits>
#include <stdexcept>
#include <utility>

namespace {
mco::WorkerRecord record(std::uint32_t id, std::uint8_t marker, std::uint32_t bits = 0) {
    mco::WorkerRecord result;
    result.fill(marker);
    for (auto [offset, value] : {std::pair<std::size_t, std::uint32_t>{0, 7}, {4, id}, {8, bits}})
        for (std::size_t i = 0; i < 4; ++i)
            result[offset + i] = static_cast<std::uint8_t>(value >> (8 * i));
    return result;
}
}

int main() {
    int failures = 0;
    const auto check = [&](bool condition) { if (!condition) ++failures; };
    const std::vector<mco::WorkerRecord> original{record(1, 1), record(2, 2), record(1, 3), record(3, 4)};
    mco::WorkerCompletionQueue queue(original);
    const auto first = queue.query(1);
    check(first.found && first.record == original[0]);
    check(queue.records() == std::vector<mco::WorkerRecord>(original.begin() + 1, original.end()));
    const auto duplicate = queue.query(1, false);
    check(duplicate.found && !duplicate.record);
    check(queue.records() == std::vector<mco::WorkerRecord>{original[1], original[3]});
    const auto before = queue.records();
    const auto absent = queue.query(0xffffffff);
    check(!absent.found && !absent.record && queue.records() == before);
    try { (void)queue.query(0); ++failures; } catch (const std::invalid_argument&) {}
    check(queue.records() == before);
    mco::WorkerCompletionQueue empty;
    check(!empty.query(1).found);
    for (auto [bits, expected] : {std::pair<std::uint32_t, std::int32_t>{0, 0}, {1, 1},
         {0x7fffffff, 2147483647}, {0x80000000, std::numeric_limits<std::int32_t>::min()}, {0xffffffff, -1}}) {
        empty.append(record(0xffffffff, 9, bits));
        const auto complete = empty.query(0xffffffff);
        check(complete.found && complete.record.has_value());
        const auto decoded = mco::CompletedOperation::from_record(*complete.record);
        check(decoded.kind == 7 && decoded.operation_id == 0xffffffff && decoded.result == expected);
        for (auto value : decoded.argument) check(value == 9);
        check(empty.records().empty());
    }
    check(mco::worker_record_from_bytes(original[0]) == original[0]);
    for (auto size : {std::size_t{0}, mco::worker_record_size - 1, mco::worker_record_size + 1}) {
        try { (void)mco::worker_record_from_bytes(std::vector<std::uint8_t>(size)); ++failures; }
        catch (const std::invalid_argument&) {}
    }
    if (failures) std::cerr << failures << " completion checks failed\n";
    return failures ? 1 : 0;
}
