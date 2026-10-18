#include "mco/input_key_down.hpp"
#include "input_queue_cases.hpp"
#include <stdexcept>
int main() {
    queue_cases::Fixture f;
    auto s=f.state();
    s.store(input_queue_image::capacity,2);
    s.store(input_queue_image::target_window,7);
    s.store(input_queue_image::raw_mode,1);
    const auto bits=3u | (42u<<16) | (1u<<24);
    if(mco::input_key_down(s,f.remap,1,7,0x100,0x70,bits)!=1 ||
       s.keys[42]!=std::byte{1} || f.logs.size()!=4 ||
       s.load(input_queue_image::write_cursor)!=0 ||
       s.load(input_queue_image::read_cursor)!=1)
        throw std::runtime_error("repeat clamp or overwrite-oldest changed");
    for(auto slot : {0u,1u}) {
        auto event=s.event(slot);
        if(event[0]!=std::byte{1} || event[1]!=std::byte{42} ||
           event[2]!=std::byte{0} || event[3]!=std::byte{0})
            throw std::runtime_error("raw queue event changed");
    }
    s.store(input_queue_image::raw_mode,0);
    const auto logs=f.logs.size();
    if(mco::input_key_down(s,f.remap,1,7,0x100,0x41,1u|(9u<<16))!=0 ||
       s.keys[9]!=std::byte{1} || f.logs.size()!=logs)
        throw std::runtime_error("untranslated key must update raw state without queuing");
    const auto before=f.globals;
    mco::input_key_down(s,f.remap,0,7,0x100,0x70,bits);
    if(f.globals!=before || f.logs.size()!=logs)
        throw std::runtime_error("disabled input mutated state");
}
