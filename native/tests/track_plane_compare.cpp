#include "cell_io.hpp"
#include "mco/track_surface_sample.hpp"
#include <array>
#include <bit>
#include <cstdint>

int main() {
  return cell_io::run([](std::istream &input) {
    using namespace cell_io;
    const auto mode = read(input);
    const auto x = std::bit_cast<std::int32_t>(read(input));
    const auto z = std::bit_cast<std::int32_t>(read(input));
    const auto index = read(input);
    constexpr std::uint32_t base = 0x71000000, path = base + 0x1000, vertices = base + 0x2000;
    std::array<std::byte, 65536> grid{};
    std::array<std::byte, 0x3000> nodes{};
    const mco::SpatialQueryMemory memory{grid, nodes, base};
    const mco::TrackSurfaceWorld world{memory, {0,0}, {1,1}, base+0x2800, path, 0, 32};
    std::array<std::byte,68> query{};
    mco::detail::write_word(query,0,index);
    mco::detail::write_word(query,12,mode);
    std::array<float,3> seed{};
    for(auto &v:seed) v=std::bit_cast<float>(read(input));
    if(mode!=0) {
      for(unsigned i=0;i<4;++i) {
        mco::detail::write_word(query,16+i*4,vertices+i*12);
        for(unsigned j=0;j<3;++j) {
          const auto bits=read(input);
          mco::detail::write_word(nodes,vertices-base+i*12+j*4,bits);
        }
      }
      mco::detail::write_word(query,32,std::bit_cast<std::uint32_t>(x));
      mco::detail::write_word(query,40,std::bit_cast<std::uint32_t>(z));
    } else {
      for(unsigned j=0;j<3;++j)
        mco::detail::write_word(nodes,path-base+index*0x54+j*4,read(input));
    }
    const auto result=mco::track_plane_from_query(world,query,seed);
    emit(result.normal_written?1u:0u);
    for(auto v:result.reference) emit(std::bit_cast<std::uint32_t>(v));
    for(auto v:result.normal) emit(std::bit_cast<std::uint32_t>(v));
  });
}
