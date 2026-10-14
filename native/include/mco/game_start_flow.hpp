#pragma once
#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace mco {
enum class GameStartActionKind { enqueue_task_5, query_completion, pump_application, query_room_status, complete };
struct GameStartAction {
    GameStartActionKind kind;
    std::optional<std::uint32_t> owner_offset, operation_id, channel_id;
    std::optional<std::array<std::uint8_t, 8>> argument;
    std::optional<std::int32_t> result;
};
// Single-owner observations only. Worker scheduling, cache and sockets are external.
class GameStartFlow {
public:
    explicit GameStartFlow(std::span<const std::uint8_t> network_image);
    std::span<const std::uint8_t> network_image() const noexcept;
    GameStartAction action() const;
    void enqueued(std::uint32_t record_operation_id);
    void completion_queried(std::optional<std::int32_t> result);
    void application_pumped(std::int32_t result,
        std::optional<std::span<const std::uint8_t>> observed_image = std::nullopt);
    void room_status_queried(std::optional<std::uint32_t> status);
private:
    enum class Phase { enqueue, query, pump_completion, pump_status, status, complete };
    Phase phase_ = Phase::enqueue;
    std::vector<std::uint8_t> image_;
    std::array<std::uint8_t, 8> argument_{};
    std::optional<std::uint32_t> operation_id_;
    std::optional<std::int32_t> result_;
    void require(Phase expected) const;
    void finish(std::int32_t result);
};
} // namespace mco
