#pragma once
#include "cell_io.hpp"
#include "mco/track_surface_lookup.hpp"
namespace track_surface_cases {
inline void compare(std::istream& input) {
    const auto mode=cell_io::read(input),cached=cell_io::read(input),previous=cell_io::read(input);
    const auto neighbors=cell_io::read(input),upward=cell_io::read(input);
    const auto x=std::bit_cast<std::int32_t>(cell_io::read(input));
    const auto z=cell_io::read(input),seed=cell_io::read(input);
    constexpr std::uint32_t base=0x71000000,paths=base+0x1000,blocks=base+0x3000,geometry=base+0x5000;
    std::array<std::byte,0x6000> arena{};
    std::array<std::byte,65536> grid{};
    std::array<std::byte,68> record;
    auto word=[&](std::uint32_t address,std::uint32_t value) {mco::detail::write_word(arena,address-base,value);};
    auto real=[&](std::uint32_t address,float value) {word(address,std::bit_cast<std::uint32_t>(value));};
    auto half=[&](std::uint32_t address,std::int32_t value) {
        arena[address-base]=static_cast<std::byte>(value&255);
        arena[address-base+1]=static_cast<std::byte>((static_cast<std::uint32_t>(value)>>8)&255);
    };
    unsigned count=mode==1 ? 0 : mode==4 ? 1 : 3;
    for(unsigned i=0;i<count;++i) word(base+0x100+i*4,mode==3 ? 2-i : mode==4 ? 1 : i);
    if(mode) {
        mco::detail::write_word(grid,0,0xdeadbeef);mco::detail::write_word(grid,4,count);
        mco::detail::write_word(grid,8,base+0x100);
    }
    const std::array<std::array<float,3>,4> vertices{{{0,0,0},{16,0,0},{16,0,16},{0,0,16}}};
    for(unsigned b=0;b<3;++b) {
        const auto block=blocks+b*0x6c4,geo=geometry+b*0x200;
        word(block+0x3c,geo+0x80);word(block+0x14c,geo);word(block+0x67c,geo+0xc0);
        word(block+0x680,8);
        for(unsigned j=0;j<8;++j) word(block+0x6a4+j*4,neighbors && j==7 ? previous : 0xffffffffu);
        real(block+0x664,static_cast<float>(b*24));real(block+0x66c,0);
        real(block+0x670,static_cast<float>(b*24+16));real(block+0x678,16);
        for(unsigned i=0;i<4;++i) for(unsigned j=0;j<3;++j) real(geo+i*12+j*4,vertices[i][j]);
        for(unsigned j=0;j<4;++j) half(geo+0x80+j*2,static_cast<std::int32_t>(j));
        const std::array<std::int32_t,6> coefficients{100+static_cast<std::int32_t>(b),
            upward&(1u<<b) ? 32767 : -32768,-200-static_cast<std::int32_t>(b),
            300+static_cast<std::int32_t>(b),-400-static_cast<std::int32_t>(b),500+static_cast<std::int32_t>(b)};
        for(unsigned j=0;j<6;++j) half(geo+0xc8+j*2,coefficients[j]);
        for(unsigned j=0;j<8;++j) {
            real(paths+(b*8+j)*0x54,static_cast<float>(b*24+j*2));
            real(paths+(b*8+j)*0x54+8,static_cast<float>(j));
        }
    }
    for(unsigned i=0;i<68;++i) record[i]=static_cast<std::byte>((seed+i*37)&255);
    mco::detail::write_word(record,4,previous);
    mco::detail::write_word(record,12,cached ? geometry+0xc0 : 0);
    for(unsigned j=0;j<4;++j) mco::detail::write_word(record,16+j*4,geometry+j*12);
    const mco::SpatialQueryMemory memory{grid,arena,base};
    const mco::TrackSurfaceWorld world{memory,{0,0},{1,1},blocks,paths,2,24};
    const std::array<float,3> position{static_cast<float>(x),7,static_cast<float>(z)};
    cell_io::emit(mco::track_surface_lookup(world,position,record));cell_io::emit(record);
}
}
