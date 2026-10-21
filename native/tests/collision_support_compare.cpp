#include "mco/collision_support.hpp"
#include "mco/detail/byte_words.hpp"
#include <bit>
#include <iomanip>
#include <iostream>
#include <limits>

namespace {
constexpr std::uint32_t base=0x71000000, paths=base+0x1000,
                        blocks=base+0x3000, geometry=base+0x5000,
                        owner_address=0x71008000;
void put_word(std::array<std::byte,0x6000>& arena,std::uint32_t address,
              std::uint32_t value) {
    mco::detail::write_word(arena,address-base,value);
}
void put_float(std::array<std::byte,0x6000>& arena,std::uint32_t address,float value) {
    put_word(arena,address,std::bit_cast<std::uint32_t>(value));
}
void put_half(std::array<std::byte,0x6000>& arena,std::uint32_t address,
              std::int16_t value) {
    const auto bits=std::bit_cast<std::uint16_t>(value);
    arena[address-base]=static_cast<std::byte>(bits&0xff);
    arena[address-base+1]=static_cast<std::byte>(bits>>8);
}
mco::TrackSurfaceWorld make_world(std::array<std::byte,65536>& grid,
                                  std::array<std::byte,0x6000>& arena,
                                  unsigned previous,unsigned neighbors) {
    mco::detail::write_word(grid,0,0xdeadbeef);
    mco::detail::write_word(grid,4,3);
    mco::detail::write_word(grid,8,base+0x100);
    for(unsigned i=0;i<3;++i) put_word(arena,base+0x100+i*4,i);
    const std::array<std::array<float,3>,4> vertices{{{0,0,0},{16,0,0},
                                                       {16,0,16},{0,0,16}}};
    for(unsigned b=0;b<3;++b) {
        const auto block=blocks+b*0x6c4,geo=geometry+b*0x200;
        put_word(arena,block+0x3c,geo+0x80);
        put_word(arena,block+0x14c,geo);
        put_word(arena,block+0x67c,geo+0xc0);
        put_word(arena,block+0x680,8);
        for(unsigned j=0;j<8;++j)
            put_word(arena,block+0x6a4+j*4,neighbors&&j==7?previous:0xffffffffu);
        put_float(arena,block+0x664,static_cast<float>(b*24));
        put_float(arena,block+0x66c,0.f);
        put_float(arena,block+0x670,static_cast<float>(b*24+16));
        put_float(arena,block+0x678,16.f);
        for(unsigned i=0;i<4;++i) for(unsigned j=0;j<3;++j)
            put_float(arena,geo+i*12+j*4,vertices[i][j]);
        for(unsigned j=0;j<4;++j) put_half(arena,geo+0x80+j*2,j);
        const std::array<std::int16_t,6> coefficients{
            static_cast<std::int16_t>(100+b),32767,
            static_cast<std::int16_t>(-200-static_cast<int>(b)),
            static_cast<std::int16_t>(300+b),static_cast<std::int16_t>(-400-static_cast<int>(b)),
            static_cast<std::int16_t>(500+b)};
        for(unsigned j=0;j<6;++j) put_half(arena,geo+0xc8+j*2,coefficients[j]);
        for(unsigned j=0;j<8;++j) {
            put_float(arena,paths+(b*8+j)*0x54,static_cast<float>(b*24+j*2));
            put_float(arena,paths+(b*8+j)*0x54+8,static_cast<float>(j));
        }
    }
    const mco::SpatialQueryMemory memory{grid,arena,base};
    return {memory,{0,0},{1,1},blocks,paths,2,24};
}
}

int main() {
    std::cout<<std::setprecision(std::numeric_limits<float>::max_digits10);
    while(true) {
        std::array<float,3> position{};float velocity_y{};unsigned previous{},neighbors{};
        if(!(std::cin>>position[0])) return std::cin.eof()?0:2;
        if(!(std::cin>>position[1]>>position[2]>>velocity_y>>previous>>neighbors)) return 2;
        std::array<float,66> local{};
        for(auto& value:local) if(!(std::cin>>value)) return 2;
        std::array<std::byte,68> seed{};
        for(auto& value:seed) {unsigned byte{};if(!(std::cin>>byte)||byte>255)return 2;value=static_cast<std::byte>(byte);}
        std::array<std::byte,65536> grid{};
        std::array<std::byte,0x6000> arena{};
        auto world=make_world(grid,arena,previous,neighbors);
        const std::array<float,9> identity{1,0,0,0,1,0,0,0,1};
        const auto geometry_result=mco::correct_support_geometry(
            world,position,identity,local,seed,velocity_y);
        mco::CollisionImpactBody body{};
        body.address=owner_address;body.position=position;body.linear_velocity={0,velocity_y,0};
        body.mass=1.f;body.inertia.inverse_mass=1.f;
        body.inertia.inverse_inertia={1,1,1};
        body.inertia.world_to_body={1,0,0,0,1,0,0,0,1};
        body.inertia.body_to_world={1,0,0,0,1,0,0,0,1};
        std::array<std::array<float,2>,32> coefficients{};
        for(auto& row:coefficients) row={.45f,.2f};
        const auto result=mco::resolve_support_contacts(world,body,geometry_result,
                                                        coefficients,1.f,0);
        std::cout<<result.support_count;
        for(float v:result.body.position)std::cout<<' '<<v;
        for(float v:result.body.linear_velocity)std::cout<<' '<<v;
        for(float v:result.body.angular_turn_velocity)std::cout<<' '<<v;
        for(std::size_t i=0;i<22;++i) for(std::size_t axis=0;axis<3;++axis)
            std::cout<<' '<<geometry_result.position[axis]+geometry_result.relative_points[i*3+axis];
        for(std::size_t i=0x3c4;i<0x400;++i)
            std::cout<<' '<<static_cast<unsigned>(result.body.contact_record[i]);
        std::cout<<'\n';
    }
}
