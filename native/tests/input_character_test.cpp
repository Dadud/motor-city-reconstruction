#include "mco/input_character.hpp"
#include "input_queue_cases.hpp"
#include <stdexcept>
int main() {
    queue_cases::Fixture f;
    f.keys.fill(std::byte{0x55});
    auto state=f.state();
    state.store(input_queue_image::target_window,7);state.store(input_queue_image::capacity,2);
    state.store(input_queue_image::raw_mode,1);state.store(input_queue_image::remap,0x12345678);
    state.store(input_queue_image::last_code,0xdeadbeef);
    const auto keys=f.keys;
    if(mco::input_character(state,1,7,0xdead,0x1234abcd,3u|(42u<<16)|(1u<<24))!=1 ||
       f.logs.size()!=4 || state.load(input_queue_image::write_cursor)!=0 ||
       state.load(input_queue_image::read_cursor)!=1 || f.keys!=keys ||
       state.load(input_queue_image::last_code)!=0xdeadbeef)
        throw std::runtime_error("character queue changed raw/remap/repeat semantics");
    for(unsigned i=0;i<2;++i) {
        const auto event=state.event(i);
        if(event[0]!=std::byte{1} || event[1]!=std::byte{42} ||
           event[2]!=std::byte{0xcd} || event[3]!=std::byte{0xab})
            throw std::runtime_error("packed character event changed");
    }
    state.store(input_queue_image::capacity,0xffffffff);
    const auto before=f.globals;const auto logs=f.logs.size();
    if(mco::input_character(state,0,7,0x102,1,1)!=1 || f.globals!=before || f.logs.size()!=logs)
        throw std::runtime_error("disabled character handler touched queue");
}
