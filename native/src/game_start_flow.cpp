#include "mco/game_start_flow.hpp"
#include <algorithm>
#include <stdexcept>

namespace mco {
namespace {
void validate(std::span<const std::uint8_t> image) {
    if (image.size() < 0x5d0 || image.size() > 65536)
        throw std::invalid_argument("expected bounded network-owner image");
}
std::uint32_t read(std::span<const std::uint8_t> image, std::size_t offset) {
    std::uint32_t value = 0;
    for (unsigned i = 0; i < 4; ++i) value |= static_cast<std::uint32_t>(image[offset + i]) << (8 * i);
    return value;
}
}
GameStartFlow::GameStartFlow(std::span<const std::uint8_t> image) {
    validate(image);
    image_.assign(image.begin(), image.end());
    std::copy_n(image.begin() + 0x5cc, 4, argument_.begin());
    std::copy_n(image.begin() + 0x160, 4, argument_.begin() + 4);
}
std::span<const std::uint8_t> GameStartFlow::network_image() const noexcept { return image_; }
void GameStartFlow::require(Phase phase) const {
    if (phase_ != phase) throw std::invalid_argument("unexpected game-start observation");
}
void GameStartFlow::finish(std::int32_t result) { result_ = result; phase_ = Phase::complete; }
GameStartAction GameStartFlow::action() const {
    GameStartAction result{};
    switch (phase_) {
    case Phase::enqueue:
        result.kind = GameStartActionKind::enqueue_task_5; result.owner_offset = 12;
        result.argument = argument_; break;
    case Phase::query:
        result.kind = GameStartActionKind::query_completion; result.owner_offset = 12;
        result.operation_id = operation_id_; break;
    case Phase::pump_completion:
    case Phase::pump_status: result.kind = GameStartActionKind::pump_application; break;
    case Phase::status:
        result.kind = GameStartActionKind::query_room_status; result.owner_offset = 0x458;
        result.channel_id = read(image_, 0x160); break;
    case Phase::complete: result.kind = GameStartActionKind::complete; result.result = result_; break;
    }
    return result;
}
void GameStartFlow::enqueued(std::uint32_t id) {
    require(Phase::enqueue);
    if (id == 0) throw std::invalid_argument("tracked start requires nonzero record operation ID");
    operation_id_ = id; phase_ = Phase::query;
}
void GameStartFlow::completion_queried(std::optional<std::int32_t> result) {
    require(Phase::query);
    if (!result) phase_ = Phase::pump_completion;
    else if (*result < 0) finish(*result);
    else phase_ = Phase::pump_status;
}
void GameStartFlow::application_pumped(std::int32_t result,
    std::optional<std::span<const std::uint8_t>> observed) {
    if (phase_ != Phase::pump_completion && phase_ != Phase::pump_status)
        throw std::invalid_argument("unexpected application pump observation");
    if (observed) {
        validate(*observed);
        if (observed->size() != image_.size()) throw std::invalid_argument("observed owner size changed");
        // Copy first so an observation may alias the owned image safely.
        std::vector<std::uint8_t> copy(observed->begin(), observed->end());
        image_.swap(copy);
    }
    if (result != 0) finish(-51);
    else phase_ = phase_ == Phase::pump_completion ? Phase::query : Phase::status;
}
void GameStartFlow::room_status_queried(std::optional<std::uint32_t> status) {
    require(Phase::status);
    if (!status) finish(-7);
    else {
        if (*status > 255) throw std::invalid_argument("room status must fit uint8");
        if (*status == 4 || *status == 8) finish(*status == 4 ? 0 : -20);
        else phase_ = Phase::pump_status;
    }
}
} // namespace mco
