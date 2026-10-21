#include "mco/scheduler.hpp"
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
void add(std::vector<ScheduledCall>& list, std::int32_t priority,
        std::uint32_t callback, std::uint32_t payload = 0) {
    insert_callback(list, {priority, callback, payload});
}
void add_each(std::vector<ScheduledCall>& list, std::int32_t priority,
              std::uint32_t callback, const std::vector<std::uint32_t>& owners) {
    for (const auto owner : owners) add(list, priority, callback, owner);
}
std::int32_t capacity(std::int64_t value) {
    if (value < 0 || value > std::numeric_limits<std::int32_t>::max())
        throw std::invalid_argument("task-list capacity overflows signed int32");
    return static_cast<std::int32_t>(value);
}
void validate_owners(const std::vector<std::uint32_t>& owners) {
    if (std::find(owners.begin(), owners.end(), 0u) != owners.end())
        throw std::invalid_argument("task owner pointers must be non-null");
}
} // namespace

void insert_callback(std::vector<ScheduledCall>& entries, ScheduledCall entry) {
    const auto position = std::find_if(entries.begin(), entries.end(),
        [entry](const auto& current) { return entry.priority < current.priority; });
    entries.insert(position, entry);
}
GameTaskLists build_game_task_lists(const std::vector<std::uint32_t>& vehicles,
                                    const std::vector<std::uint32_t>& world_objects,
                                    const std::vector<std::uint32_t>& vehicle_flags,
                                    std::uint32_t dynamic_service_payload,
                                    std::int32_t capacity_source_count) {
    if (vehicles.size() != vehicle_flags.size())
        throw std::invalid_argument("one observed flag word is required per vehicle");
    if (capacity_source_count < 0)
        throw std::invalid_argument("capacity source count must be nonnegative");
    validate_owners(vehicles);
    validate_owners(world_objects);

    GameTaskLists result;
    const auto world_count = static_cast<std::int64_t>(world_objects.size());
    result.primary_capacity = capacity(world_count * 3 + 12 +
        static_cast<std::int64_t>(capacity_source_count) * 5);
    result.secondary_capacity = capacity(world_count + 8 +
        static_cast<std::int64_t>(capacity_source_count) * 4);

    // Original 0x567940 primary-list registration order. insert_callback
    // reproduces 0x565d20's stable ascending-priority insertion.
    add_each(result.primary, 6, 0x00520c20, vehicles);
    add_each(result.primary, 6, 0x00520c20, world_objects);
    add(result.primary, 6, 0x0042d730);
    add(result.primary, 8, 0x0043f550);
    add(result.primary, 10, 0x00487790, dynamic_service_payload);
    add_each(result.primary, 0x15, 0x00469010, vehicles);
    add_each(result.primary, 0x1e, 0x0053c140, vehicles);
    add_each(result.primary, 0x1e, 0x005779d0, world_objects);
    add(result.primary, 0x1e, 0x004265f0);
    add(result.primary, 0x1e, 0x00426730);
    add_each(result.primary, 0x28, 0x0045abe0, vehicles);
    add(result.primary, 0x28, 0x004265b0);
    add_each(result.primary, 0x28, 0x0045abe0, world_objects);
    add_each(result.primary, 0x32, 0x0043d6e0, vehicles);
    add(result.primary, 0x32, 0x00424ec0);
    add(result.primary, 0x32, 0x00426770);
    add(result.primary, 100, 0x0055f520);
    add(result.primary, 0x6e, 0x0055d300);
    add(result.primary, 0x78, 0x005678f0);

    // Original 0x567940 secondary-list registration order.
    add(result.secondary, 6, 0x0042d780);
    add(result.secondary, 6, 0x00459df0);
    for (std::size_t i = 0; i < vehicles.size(); ++i) {
        const auto flags = vehicle_flags[i];
        if (((flags & 1u) != 0 && (flags & 2u) != 0) || (flags & 4u) != 0)
            add(result.secondary, 0x19, 0x00585790, vehicles[i]);
    }
    add_each(result.secondary, 0x1e, 0x00520450, vehicles);
    add_each(result.secondary, 0x1e, 0x00520450, world_objects);
    add(result.secondary, 0x23, 0x0040adb0);
    add_each(result.secondary, 100, 0x0043f9d0, vehicles);
    add(result.secondary, 100, 0x0055f540);
    add(result.secondary, 0x6e, 0x005850b0);
    return result;
}
void execute_callbacks(std::vector<ScheduledCall>& entries,
                       const std::function<void(std::uint32_t, std::uint32_t)>& dispatch) {
    const auto count = entries.size();
    for (std::size_t index=0; index<count; ++index) {
        if(index>=entries.size()) throw std::invalid_argument("callback storage shortened during execution");
        const auto entry = entries[index];
        if(entry.callback) dispatch(entry.callback, entry.payload);
    }
}
int selected_iterations(bool enabled, std::int32_t mode, std::int32_t frame) {
    if(!enabled) return 1;
    if(mode==0) return frame%4==0 ? 1 : 0;
    if(mode==1) return frame%2==0 ? 1 : 0;
    return mode==3 ? 2 : 1;
}
int pending_iterations(std::uint32_t clock, std::uint32_t processed) {
    const auto delta=clock-processed;
    if((delta&0x80000000u)!=0) return 0;
    return delta>=16 ? 16 : static_cast<int>(delta);
}
std::uint32_t execute_batch(std::uint32_t counter, int iterations, bool inhibited,
                           const std::function<void()>& first,
                           const std::function<void()>& second,
                           const std::function<void()>& after) {
    if(iterations<0 || iterations>2) throw std::invalid_argument("selected iterations must be 0, 1 or 2");
    if(inhibited) return counter;
    for(int index=0;index<iterations;++index) {
        if((counter&1u)==0) first();
        second(); after(); ++counter;
    }
    return counter;
}
}
