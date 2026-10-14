#include "mco/game_start_flow.hpp"
#include <stdexcept>
#include <limits>

namespace {
void check(bool result) { if (!result) throw std::runtime_error("game start scenario differs"); }
std::vector<std::uint8_t> image(std::uint32_t channel = 123) {
    std::vector<std::uint8_t> result(0x600, 0xa5);
    for (unsigned i = 0; i < 4; ++i) {
        result[0x160 + i] = static_cast<std::uint8_t>(channel >> (8 * i));
        result[0x5cc + i] = static_cast<std::uint8_t>(7u >> (8 * i));
    }
    return result;
}
}
int main() {
    using Kind = mco::GameStartActionKind;
    for (auto result : {-1, -51, std::numeric_limits<std::int32_t>::min()}) {
        mco::GameStartFlow flow(image()); flow.enqueued(9); flow.completion_queried(result);
        check(flow.action().kind == Kind::complete && flow.action().result == result);
    }
    for (auto status : {std::optional<std::uint32_t>{}, {4}, {8}}) {
        mco::GameStartFlow flow(image());
        check(flow.action().argument == std::array<std::uint8_t,8>{7,0,0,0,123,0,0,0});
        flow.enqueued(0xffffffffu); flow.completion_queried(std::nullopt);
        flow.application_pumped(0); check(flow.action().operation_id == 0xffffffffu);
        flow.completion_queried(123); check(flow.action().kind == Kind::pump_application);
        auto changed = image(456); flow.application_pumped(0, changed);
        check(flow.action().channel_id == 456 && flow.action().owner_offset == 0x458);
        flow.room_status_queried(255); flow.application_pumped(0, flow.network_image());
        flow.room_status_queried(status);
        check(flow.action().result == (!status ? -7 : *status == 4 ? 0 : -20));
    }
    mco::GameStartFlow abort(image()); abort.enqueued(1); abort.completion_queried(0);
    abort.application_pumped(1); check(abort.action().result == -51);
    mco::GameStartFlow invalid(image());
    bool rejected = false;
    try { invalid.enqueued(0); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected && invalid.action().kind == Kind::enqueue_task_5);
}
