#pragma once
#include "mco/startup_initialize.hpp"
#include "mco/input_toggle_key.hpp"
#include <stdexcept>
namespace mco {
// Compose the recovered Num Lock entry with the existing startup input binding.
struct StartupToggleBinding {
    InputToggleKeyPlatform& toggle;
    std::uint32_t& incoming_temporary;
    StartupPlatform previous;
    static std::uint32_t invoke(StartupState& state, std::uint32_t id,
            std::span<const std::uint32_t> args, void* user) {
        auto& self = *static_cast<StartupToggleBinding*>(user);
        if (id == 0x6bfc80) {
            if (!args.empty()) throw std::invalid_argument("startup Num Lock arguments");
            input_startup_numlock(self.toggle);
            // In the original x86 call chain, PUSH ECX allocates the toggle
            // local; its scan byte becomes 0x45 before POP ECX. Device init
            // receives this defined residue, not the original mouse word.
            // This models a bounded original register contract, not host ECX.
            self.incoming_temporary=(self.incoming_temporary&0xffffff00u)|0x45u;
            return 0;
        }
        if (!self.previous.invoke) throw std::invalid_argument("startup subsystem bridge required");
        return self.previous.invoke(state, id, args, self.previous.user);
    }
    static bool nonempty(std::uint32_t id, void* user) {
        auto& self = *static_cast<StartupToggleBinding*>(user);
        if (!self.previous.driver_nonempty) throw std::invalid_argument("startup driver-name view required");
        return self.previous.driver_nonempty(id, self.previous.user);
    }
    StartupPlatform platform() { return {invoke, nonempty, this}; }
};
}
