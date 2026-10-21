#include "mco/world_object_array.hpp"
#include <limits>
#include <stdexcept>

namespace mco {
void update_active_world_objects(
    std::uint32_t base_address, const std::vector<bool>& active_flags,
    const std::function<void(std::uint32_t)>& update_object) {
    if (base_address == 0) throw std::invalid_argument("world-object base must be non-null");
    if (!update_object) throw std::invalid_argument("the 0x520250 object callback is required");
    for (std::size_t index=0; index<active_flags.size(); ++index) {
        const auto address=static_cast<std::uint64_t>(base_address)+index*world_object_stride;
        if (address>std::numeric_limits<std::uint32_t>::max())
            throw std::invalid_argument("world-object row address overflows uint32");
        if (active_flags[index]) update_object(static_cast<std::uint32_t>(address));
    }
}
}
