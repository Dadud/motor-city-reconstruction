#include "mco/scheduler.hpp"
#include <algorithm>
#include <stdexcept>

namespace mco {
void insert_callback(std::vector<ScheduledCall>& entries, ScheduledCall entry) {
    const auto position = std::find_if(entries.begin(), entries.end(),
        [entry](const auto& current) { return entry.priority < current.priority; });
    entries.insert(position, entry);
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
