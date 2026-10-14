#include "mco/room_disconnect_flow.hpp"
#include <utility>

namespace mco {
namespace {
void validate(std::span<const std::uint8_t> image) {
    if (image.size() < room_disconnect_min_size || image.size() > 65536)
        throw std::invalid_argument("expected bounded complete room image");
}
std::uint32_t read(std::span<const std::uint8_t> image, std::size_t offset, std::size_t size) {
    std::uint32_t value = 0;
    for (std::size_t i = 0; i < size; ++i) value |= static_cast<std::uint32_t>(image[offset + i]) << (8 * i);
    return value;
}
} // namespace

RoomDisconnectFlow::RoomDisconnectFlow(std::span<const std::uint8_t> room_image, bool wait_for_completion)
    : wait_(wait_for_completion) {
    validate(room_image);
    image_.assign(room_image.begin(), room_image.end());
}
std::span<const std::uint8_t> RoomDisconnectFlow::room_image() const noexcept { return image_; }
RoomDisconnectAction RoomDisconnectFlow::action() const {
    RoomDisconnectAction result{};
    switch (phase_) {
    case Phase::reset_first:
    case Phase::reset_second:
        result.kind = RoomDisconnectActionKind::reset_container;
        result.owner_offset = phase_ == Phase::reset_first ? 0x2e0 : 0x1fc;
        break;
    case Phase::yield_pending: result.kind = RoomDisconnectActionKind::yield_pending; break;
    case Phase::enqueue:
        result.kind = RoomDisconnectActionKind::enqueue;
        result.owner_offset = 12;
        result.argument = preparation_->argument;
        result.tracked = preparation_->tracked;
        break;
    case Phase::query:
        result.kind = RoomDisconnectActionKind::query_completion;
        result.owner_offset = 12;
        result.operation_id = operation_id_;
        break;
    case Phase::pump: result.kind = RoomDisconnectActionKind::pump_application; break;
    case Phase::complete:
        result.kind = RoomDisconnectActionKind::complete;
        result.result = result_;
        break;
    }
    return result;
}
void RoomDisconnectFlow::require(Phase expected) const {
    if (phase_ != expected) throw std::invalid_argument("observation does not match requested disconnect action");
}
void RoomDisconnectFlow::observe(std::span<const std::uint8_t> image) {
    validate(image);
    if (image.size() != image_.size()) throw std::invalid_argument("observed room image size changed");
    // Copy first, permitting observations that alias the current read-only span.
    std::vector<std::uint8_t> copy(image.begin(), image.end());
    image_ = std::move(copy);
}
void RoomDisconnectFlow::prepare() {
    preparation_ = prepare_room_disconnect(image_, wait_);
    image_ = preparation_->room_image;
    if (!preparation_->argument) { result_ = 0; phase_ = Phase::complete; }
    else phase_ = Phase::enqueue;
}
void RoomDisconnectFlow::container_reset(std::span<const std::uint8_t> observed_image) {
    if (phase_ != Phase::reset_first && phase_ != Phase::reset_second)
        throw std::invalid_argument("observation does not match requested disconnect action");
    observe(observed_image);
    if (phase_ == Phase::reset_first) phase_ = Phase::reset_second;
    else if (read(image_, 0xec, 2) != 0 && read(image_, 0x3a8, 4) != 0) phase_ = Phase::yield_pending;
    else prepare();
}
void RoomDisconnectFlow::pending_yielded(std::span<const std::uint8_t> observed_image) {
    require(Phase::yield_pending);
    observe(observed_image);
    if (read(image_, 0x3a8, 4) == 0) prepare();
}
void RoomDisconnectFlow::enqueued(std::optional<std::uint32_t> record_operation_id) {
    require(Phase::enqueue);
    if (preparation_->tracked) {
        if (!record_operation_id || *record_operation_id == 0)
            throw std::invalid_argument("tracked disconnect requires nonzero record operation ID");
        operation_id_ = record_operation_id;
        phase_ = Phase::query;
    } else { result_ = 0; phase_ = Phase::complete; }
}
void RoomDisconnectFlow::completion_queried(std::optional<std::int32_t> result) {
    require(Phase::query);
    if (!result) phase_ = Phase::pump;
    else { result_ = result; phase_ = Phase::complete; }
}
void RoomDisconnectFlow::application_pumped(std::int32_t result) {
    require(Phase::pump);
    if (result != 0) { result_ = -51; phase_ = Phase::complete; }
    else phase_ = Phase::query;
}
} // namespace mco
