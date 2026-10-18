#include "mco/input_queue_resize.hpp"
#include <bit>
namespace mco {
void input_queue_resize(InputKeyQueue& state,std::uint32_t requested) {
    auto size=std::bit_cast<std::int32_t>(requested);
    if(size>32) size=32;
    if(size<1) size=1;
    state.store(input_queue_image::capacity,static_cast<std::uint32_t>(size));
    state.store(input_queue_image::read_cursor,0);
    state.store(input_queue_image::write_cursor,0);
}
}
