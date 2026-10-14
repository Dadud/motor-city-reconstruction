#pragma once
#include <cstdint>
#include <functional>
#include <vector>

namespace mco {
struct ScheduledCall {
    std::int32_t priority{};
    std::uint32_t callback{}, payload{};
};
void insert_callback(std::vector<ScheduledCall>& entries, ScheduledCall entry);
void execute_callbacks(std::vector<ScheduledCall>& entries,
                       const std::function<void(std::uint32_t, std::uint32_t)>& dispatch);
int selected_iterations(bool adjustment_enabled, std::int32_t adjustment_mode,
                        std::int32_t frame_counter);
int pending_iterations(std::uint32_t clock_counter, std::uint32_t processed_counter);
std::uint32_t execute_batch(std::uint32_t counter, int iterations, bool inhibited,
                           const std::function<void()>& first,
                           const std::function<void()>& second,
                           const std::function<void()>& after);
}
