#include "mco/cleanup_registry.hpp"
#include <stdexcept>
namespace mco {
void cleanup_registry_register(CleanupRegistry& state,std::uint32_t identity) {
    for (auto value:state.slots) if (value==identity) return;
    for (auto& value:state.slots) if (value==0) {value=identity;return;}
}
void cleanup_registry_run(CleanupRegistry& state,const CleanupRegistryPlatform& platform) {
    for (std::size_t remaining=state.slots.size();remaining!=0;--remaining) {
        auto& slot=state.slots[remaining-1];
        const auto identity=slot;
        if (identity!=0) {
            if (!platform.invoke) throw std::invalid_argument("cleanup callback bridge required");
            platform.invoke(state,identity,platform.user);
        }
        // Clear after return, including mutations to the current slot.
        slot=0;
    }
}
}
