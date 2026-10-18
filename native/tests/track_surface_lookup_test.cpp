#include "mco/track_surface_lookup.hpp"
#include <stdexcept>
int main() {
    constexpr std::uint32_t base=0x71000000,blocks=base+0x400,geo=base+0xb00;
    std::array<std::byte,65536> grid{};
    std::array<std::byte,4096> arena{};
    std::array<std::byte,68> record;
    record.fill(std::byte{0xcc});
    auto word=[&](unsigned offset,std::uint32_t value) {mco::detail::write_word(arena,offset,value);};
    word(0x400+0x680,8);
    const std::array<std::array<float,3>,4> vertices{{{0,0,0},{16,0,0},{16,0,16},{0,0,16}}};
    for(unsigned i=0;i<4;++i) for(unsigned j=0;j<3;++j)
        word(0xb00+i*12+j*4,std::bit_cast<std::uint32_t>(vertices[i][j]));
    mco::detail::write_word(record,12,0x1234);
    for(unsigned i=0;i<4;++i) mco::detail::write_word(record,16+i*4,geo+i*12);
    const mco::SpatialQueryMemory memory{grid,arena,base};
    const mco::TrackSurfaceWorld world{memory,{0,0},{1,1},blocks,base,0,8};
    std::array<float,3> position{8,7,8};
    if(mco::track_surface_lookup(world,position,record)!=1 ||
       mco::detail::read_word(record,0)!=0xcccccccc ||
       mco::detail::read_word(record,36)!=std::bit_cast<std::uint32_t>(7.f))
        throw std::runtime_error("cached hit changed unrelated state");
    position={20,7,20};
    if(mco::track_surface_lookup(world,position,record)!=0 ||
       mco::detail::read_word(record,0)!=0 || mco::detail::read_word(record,4)!=0 ||
       mco::detail::read_word(record,8)!=2 || mco::detail::read_word(record,12)!=0 ||
       mco::detail::read_word(record,16)!=0 || mco::detail::read_word(record,44)!=0xcccccccc)
        throw std::runtime_error("fallback reset or coefficient retention changed");
    auto invalid=world;invalid.path_count=0;
    try {mco::track_surface_lookup(invalid,position,record);}
    catch(const std::invalid_argument&) {return 0;}
    throw std::runtime_error("invalid path world accepted");
}
