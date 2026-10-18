#include "mco/registry_reset.hpp"
#include <span>
#include <stdexcept>
int main() {
    std::array<std::byte, 0x1804> registry{};
    registry.fill(static_cast<std::byte>(0xaa));
    mco::registry_reset(registry);
    for (unsigned record = 0; record < 256; ++record) {
        const size_t base = record*24;
        if (registry[base] != std::byte{0} || registry[base+1] != std::byte{0}
                || registry[base+2] != std::byte{0}
                || registry[base+3] != std::byte{0})
            throw std::runtime_error("record head dword must clear");
        if (registry[base+4] != std::byte{0xff}
                || registry[base+5] != std::byte{0xff}
                || registry[base+6] != std::byte{0xff}
                || registry[base+7] != std::byte{0xff})
            throw std::runtime_error("record sentinel must be 0xffffffff");
        if (registry[base+8] != std::byte{0} || registry[base+9] != std::byte{0}
                || registry[base+10] != std::byte{0}
                || registry[base+11] != std::byte{0})
            throw std::runtime_error("record third dword must clear");
        for (unsigned k = 12; k < 24; ++k)
            if (registry[base+k] != static_cast<std::byte>(0xaa))
                throw std::runtime_error("record tail must stay untouched");
    }
    for (unsigned k = 0x17f4; k < 0x1804; ++k)
        if (registry[k] != static_cast<std::byte>(0xaa))
            throw std::runtime_error("bytes past the last record must stay");
    return 0;
}
