#pragma once
#include "cell_io.hpp"
#include "mco/free_camera_update.hpp"
namespace free_camera_cases {
inline void compare(std::istream& input) {
    const auto event=cell_io::read(input),stamp=cell_io::read(input);
    auto image=cell_io::image<512>(input);
    const auto keys=cell_io::image<128>(input);
    auto latches=cell_io::image<512>(input);
    auto subject=cell_io::image<68>(input);
    std::array<std::byte,0x6000> arena{};
    std::array<std::byte,65536> grid{};
    mco::detail::write_word(arena,0x3000+0x680,8);
    const mco::SpatialQueryMemory memory{grid,arena,0x71000000};
    const mco::TrackSurfaceWorld world{memory,{0,0},{1,1},0x71003000,0x71001000,0,8};
    mco::FreeCameraState state{image,keys,latches,
        [](std::uint32_t identity,void* user) -> std::span<const std::byte,68> {
            if(identity!=0x7100b000) throw std::invalid_argument("unmapped camera subject");
            return *static_cast<std::array<std::byte,68>*>(user);
        },&subject};
    mco::free_camera_update(state,world,event,stamp);
    cell_io::emit(image);cell_io::emit(keys);cell_io::emit(latches);cell_io::emit(subject);
}
}
