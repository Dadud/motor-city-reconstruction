#pragma once
#include "cell_io.hpp"
#include "mco/input_key_queue.hpp"
#include <vector>

namespace queue_cases {
struct Fixture {
    std::uint32_t mask{}, value{};
    std::array<std::byte, ::input_queue_image::size> globals{};
    std::array<std::byte, 256> keys{};
    std::array<std::byte, 128> remap{};
    std::vector<std::vector<std::uint32_t>> logs;

    static Fixture read(std::istream& input) {
        Fixture f;
        f.mask=cell_io::read(input); f.value=cell_io::read(input);
        f.globals=cell_io::image<::input_queue_image::size>(input);
        f.keys=cell_io::image<256>(input); f.remap=cell_io::image<128>(input);
        return f;
    }
    static void synchronize(mco::InputKeyQueue& state, bool entering,
                            std::uint32_t identity, void* user) {
        auto& f=*static_cast<Fixture*>(user);
        std::vector<std::uint32_t> log{entering ? 1u : 0u,identity};
        for(auto byte:state.globals) log.push_back(std::to_integer<std::uint32_t>(byte));
        for(auto byte:state.keys) log.push_back(std::to_integer<std::uint32_t>(byte));
        f.logs.push_back(std::move(log));
        using namespace ::input_queue_image;
        if(entering) {
            if(f.mask&1) {state.store(write_cursor,f.value);state.store(read_cursor,(f.value+1u)&3u);}
            if(f.mask&2) state.store(capacity,2);
            if(f.mask&4) state.store(last_code,f.value^0x55aau);
            if(f.mask&8) state.store(synchronizer,f.value^0x11223344u);
        } else {
            if(f.mask&16) {state.store(write_cursor,f.value);state.store(last_code,f.value+128u);}
            if(f.mask&32) {state.store(raw_mode,state.load(raw_mode)^1u);state.keys[f.value&127u]=std::byte{0};}
        }
    }
    mco::InputKeyQueue state() {return {globals,keys,synchronize,this};}
    void emit() const {
        cell_io::emit(globals);cell_io::emit(keys);cell_io::emit(remap);
        cell_io::emit(static_cast<std::uint32_t>(logs.size()));
        for(const auto& log:logs) for(auto word:log) cell_io::emit(word);
    }
};
}
