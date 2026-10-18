#pragma once
#include "mco/startup_toggle_binding.hpp"
#include "mco/input_device_lifetime.hpp"
#include "cell_io.hpp"
#include <array>
#include <vector>
namespace startup_toggle_cases {
struct Fixture {
    mco::InputDeviceLifetimeState& device;
    std::uint32_t state{}, script{};
    std::vector<std::array<std::uint32_t,8>> logs;
    mco::InputToggleKeyPlatform platform{query, first, this};
    void log(std::uint32_t kind,std::uint32_t target,std::uint32_t key,
             std::uint32_t scan=0,std::uint32_t flags=0,std::uint32_t extra=0) {
        logs.push_back({kind,target,key,scan,flags,extra,device.initialized,
                       device.queue.load(input_queue_image::policy_enabled)});
    }
    static std::uint32_t query(std::uint32_t key,void* user) {
        auto& f=*static_cast<Fixture*>(user);f.log(0,0,key);
        if(f.script&1)f.platform.event=second;
        return f.state;
    }
    static void first(std::uint32_t key,std::uint32_t scan,std::uint32_t flags,
                      std::uint32_t extra,void* user) { event(0,key,scan,flags,extra,user); }
    static void second(std::uint32_t key,std::uint32_t scan,std::uint32_t flags,
                       std::uint32_t extra,void* user) { event(1,key,scan,flags,extra,user); }
    static void event(unsigned target,std::uint32_t key,std::uint32_t scan,
                      std::uint32_t flags,std::uint32_t extra,void* user) {
        auto& f=*static_cast<Fixture*>(user);f.log(1,target,key,scan,flags,extra);
        if(f.script&2)f.platform.event=target?first:second;
        if((flags&2) && !(f.script&4))f.state^=1;
    }
    void emit()const {
        cell_io::emit(state);cell_io::emit(std::uint32_t(platform.event==second));
        cell_io::emit(static_cast<std::uint32_t>(logs.size()));
        for(const auto& row:logs)cell_io::emit(row);
    }
};
}
