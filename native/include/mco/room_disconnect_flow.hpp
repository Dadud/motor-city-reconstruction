#pragma once

#include "mco/room_disconnect.hpp"

namespace mco {
enum class RoomDisconnectActionKind : std::uint32_t {
    reset_container, yield_pending, enqueue, query_completion, pump_application, complete
};
struct RoomDisconnectAction {
    RoomDisconnectActionKind kind;
    std::optional<std::uint32_t> owner_offset;
    std::optional<std::array<std::uint8_t, 8>> argument;
    bool tracked = false;
    std::optional<std::uint32_t> operation_id;
    std::optional<std::int32_t> result;
};

// Single-owner driver of observed state/actions. No callbacks, scheduler,
// sockets, threads, timeout policy or fabricated completion are supplied.
class RoomDisconnectFlow {
public:
    explicit RoomDisconnectFlow(std::span<const std::uint8_t> room_image, bool wait_for_completion);
    std::span<const std::uint8_t> room_image() const noexcept;
    RoomDisconnectAction action() const;
    void container_reset(std::span<const std::uint8_t> observed_image);
    void pending_yielded(std::span<const std::uint8_t> observed_image);
    void enqueued(std::optional<std::uint32_t> record_operation_id = std::nullopt);
    void completion_queried(std::optional<std::int32_t> result);
    void application_pumped(std::int32_t result);

private:
    enum class Phase { reset_first, reset_second, yield_pending, enqueue, query, pump, complete };
    std::vector<std::uint8_t> image_;
    bool wait_;
    Phase phase_ = Phase::reset_first;
    std::optional<RoomDisconnectPreparation> preparation_;
    std::optional<std::uint32_t> operation_id_;
    std::optional<std::int32_t> result_;
    void require(Phase expected) const;
    void observe(std::span<const std::uint8_t> image);
    void prepare();
};
} // namespace mco
