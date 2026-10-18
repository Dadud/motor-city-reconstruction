#include "mco/track_surface_lookup.hpp"
#include <stdexcept>
#include "mco/spatial_grid_lookup.hpp"
#include "mco/nearest_path_point.hpp"
#include "mco/path_side.hpp"
#include <vector>

namespace mco {

// Decompiled pseudocode of 0x42e760, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t track_surface_lookup(const TrackSurfaceWorld &world, std::span<const float,3> position, std::span<std::byte,68> record) {
    auto load=[&](unsigned offset) {return detail::read_word(record,offset);};
    auto store=[&](unsigned offset,std::uint32_t value) {detail::write_word(record,offset,value);};
    auto save_position=[&] {
        for(unsigned i=0;i<3;++i) store(32+i*4,std::bit_cast<std::uint32_t>(position[i]));
    };
    const auto previous_block=load(4);
    auto contains=[&](const std::array<std::uint32_t,4>& vertices) {
        for(unsigned i=0;i<4;++i) {
            const auto a=vertices[i],b=vertices[(i+1)%4];
            const double ax=world.real(a),az=world.real(a+8);
            const double bx=world.real(b),bz=world.real(b+8);
            if(!((ax-bx)*(static_cast<double>(position[2])-bz)<=
                 (az-bz)*(static_cast<double>(position[0])-bx))) return false;
        }
        return true;
    };
    if(load(12)!=0 && contains({load(16),load(20),load(24),load(28)})) {
        save_position();return 1;
    }
    const auto leaf=spatial_grid_lookup(world.memory,position,world.origin,world.scale);
    std::vector<std::array<float,3>> points;
    auto path_points=[&]() -> std::span<const std::array<float,3>> {
        if(points.empty()) {
            if(world.path_count<=0 || world.path_count>1000000)
                throw std::invalid_argument("unsupported track path count");
            points.resize(static_cast<std::size_t>(world.path_count));
            for(unsigned i=0;i<points.size();++i) for(unsigned j=0;j<3;++j)
                points[i][j]=world.real(world.paths_address+i*0x54+j*4);
        }
        return points;
    };
    auto nearest=[&](std::uint32_t block) {
        return nearest_path_point(path_points(),position,block,
            std::bit_cast<std::int32_t>(world.word(world.blocks_address+block*0x6c4+0x680)));
    };
    bool found=false;
    if(leaf!=0 && world.word(leaf)==0xdeadbeef) {
        const auto count=std::bit_cast<std::int32_t>(world.word(leaf+4));
        const auto identifiers=world.word(leaf+8);
        for(std::int32_t i=0;i<count;++i) {
            const auto id=identifiers+static_cast<std::uint32_t>(i)*4;
            const auto block=static_cast<std::uint32_t>(world.half(id));
            const auto base=world.blocks_address+block*0x6c4;
            const auto descriptor=world.word(base+0x67c)+world.half(id+2)*20;
            const auto vertices_base=world.word(base+0x14c);
            const auto quad=world.word(base+0x3c)+world.half(descriptor+6)*30;
            std::array<std::uint32_t,4> vertices;
            for(unsigned j=0;j<4;++j) vertices[j]=vertices_base+world.half(quad+j*2)*12;
            if(!contains(vertices) || world.signed_half(descriptor+10)<=0) continue;
            store(4,block);store(0,nearest(block));store(12,descriptor);save_position();
            store(8,0);
            for(unsigned j=0;j<6;++j) {
                const float coefficient=static_cast<float>(static_cast<double>(world.signed_half(descriptor+8+j*2))*2*(1.0/65536.0));
                store(44+j*4,std::bit_cast<std::uint32_t>(coefficient));
            }
            for(unsigned j=0;j<4;++j) store(16+j*4,vertices[j]);
            if(block==previous_block) return 1;
            for(unsigned j=0;j<8;++j) if(world.word(base+0x6a4+j*4)==previous_block) return 1;
            found=true;
        }
        if(found) return 1;
    }
    // No containing upward quad: choose the nearest block center, then its path.
    auto distance=[&](std::uint32_t block) {
        const auto base=world.blocks_address+block*0x6c4;
        const double x=static_cast<double>(position[0])-
            (static_cast<double>(world.real(base+0x670))+world.real(base+0x664))*0.5;
        const double z=static_cast<double>(position[2])-
            (static_cast<double>(world.real(base+0x678))+world.real(base+0x66c))*0.5;
        return z*z+x*x;
    };
    std::uint32_t block=0;
    float minimum=static_cast<float>(distance(0));
    for(std::int32_t i=1;i<=world.last_block;++i) {
        const double candidate=distance(static_cast<std::uint32_t>(i));
        if(candidate<minimum) {block=static_cast<std::uint32_t>(i);minimum=static_cast<float>(candidate);}
    }
    const auto index=nearest(block);
    store(4,index>>3);store(12,0);
    for(unsigned j=0;j<4;++j) store(16+j*4,0);
    store(8,0);save_position();store(0,index);
    store(8,path_side(path_points(),position,index));
    return 0;
}

}  // namespace mco
