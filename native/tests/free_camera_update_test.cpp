#include "mco/free_camera_update.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,512> image{},latches{};
    std::array<std::byte,128> keys{};
    std::array<std::byte,68> subject{};
    std::array<std::byte,0x6000> arena{};
    std::array<std::byte,65536> grid{};
    mco::detail::write_word(arena,0x3000+0x680,8);
    const mco::SpatialQueryMemory memory{grid,arena,0x71000000};
    const mco::TrackSurfaceWorld world{memory,{0,0},{1,1},0x71003000,0x71001000,0,8};
    auto save=[&](unsigned offset,float value) {mco::detail::write_word(image,offset,std::bit_cast<std::uint32_t>(value));};
    auto real=[&](unsigned offset) {return std::bit_cast<float>(mco::detail::read_word(image,offset));};
    save(free_camera_image::saved_position,2);
    save(free_camera_image::saved_sensitivity,1);
    for(unsigned i:{0u,4u,8u}) save(free_camera_image::saved_matrix+i*4,1);
    mco::FreeCameraState state{image,keys,latches};
    const auto before=image;
    mco::free_camera_update(state,world,99,7);
    if(image!=before) throw std::runtime_error("unknown event mutated camera");
    mco::free_camera_update(state,world,0,7);
    if(real(free_camera_image::position)!=2 || mco::detail::read_word(image,free_camera_image::reset_time)!=7)
        throw std::runtime_error("camera reset changed");
    keys[0xcd&127]=std::byte{1};
    mco::free_camera_update(state,world,1,8);
    if(real(free_camera_image::position)!=2.5f) throw std::runtime_error("right translation changed");
    keys[0x13]=std::byte{1};
    mco::free_camera_update(state,world,1,9);
    if(real(free_camera_image::position)!=2.5f) throw std::runtime_error("first reset press missed");
    mco::free_camera_update(state,world,1,10);
    if(real(free_camera_image::position)!=3 || mco::detail::read_word(image,free_camera_image::reset_time)!=9)
        throw std::runtime_error("held reset repeated");
    keys[0x13]=std::byte{};keys[0xcd&127]=std::byte{};
    mco::free_camera_update(state,world,1,11);
    keys[0x13]=std::byte{1};
    mco::free_camera_update(state,world,1,12);
    if(real(free_camera_image::position)!=2 || mco::detail::read_word(image,free_camera_image::reset_time)!=12)
        throw std::runtime_error("reset release/repress changed");
}
