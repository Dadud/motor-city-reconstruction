#include "cell_io.hpp"
#include "mco/detail/byte_words.hpp"
#include "mco/driving_support.hpp"
#include "mco/track_surface_sample.hpp"
#include <array>
#include <bit>
#include <cstdint>

namespace {
void emit_projection(const mco::TrackSurfaceWorld &world,std::int32_t x,std::int32_t z){
  const mco::SupportQuery query{0,{double(x),7.,double(z)},{1.,2.,3.},0};
  const auto p=mco::project_track_surface(world,query,{.3f,.8f,-.2f});
  cell_io::emit(std::bit_cast<std::uint32_t>(p.record.sector));
  cell_io::emit(std::bit_cast<std::uint32_t>(p.record.group));
  cell_io::emit(p.record.status);cell_io::emit(p.record.surface_id.value_or(0));
  for(const auto id:p.record.vertex_ids)cell_io::emit(id.value_or(0));
  cell_io::emit(p.record.surface_code.value_or(0));
  for(const auto value:p.point)cell_io::emit(std::bit_cast<std::uint32_t>(static_cast<float>(value)));
  for(const auto value:p.reference_position)cell_io::emit(std::bit_cast<std::uint32_t>(static_cast<float>(value)));
}
void emit_support(const mco::TrackSurfaceWorld &world,std::int32_t x,std::int32_t z){
  mco::SupportPredictionState state;
  state.position={double(x),7.,double(z)};state.velocity={.1,0.,-.2};
  state.context=0;state.fallback_surface=9;state.support_count=3;
  for(std::size_t i=0;i<4;++i){
    auto &w=state.wheels[i];w.local_point={(i&1)? .25:-.25,0.,(i&2)? .25:-.25};
    w.world_point={double(x),7.,double(z)};w.clear_reference=.5;
  }
  const auto result=mco::predict_support_on_track(std::move(state),world,
      [](const mco::SupportQuery&){return std::array<float,3>{.3f,.8f,-.2f};});
  cell_io::emit(std::bit_cast<std::uint32_t>(result.state.support_count));
  for(const auto&w:result.state.wheels){
    cell_io::emit(w.contact?1u:0u);cell_io::emit(std::bit_cast<std::uint32_t>(static_cast<float>(w.support_delta)));
    cell_io::emit(w.surface_class);for(auto value:w.world_point)cell_io::emit(std::bit_cast<std::uint32_t>(static_cast<float>(value)));
    cell_io::emit(std::bit_cast<std::uint32_t>(w.record.sector));cell_io::emit(std::bit_cast<std::uint32_t>(w.record.group));
    cell_io::emit(w.record.status);cell_io::emit(w.record.surface_id.value_or(0));
    for(const auto id:w.record.vertex_ids)cell_io::emit(id.value_or(0));cell_io::emit(w.record.surface_code.value_or(0));
    for(const auto value:w.query_tail.value_or(std::array<std::uint8_t,24>{}))cell_io::emit(value);
  }
  for(const auto&q:result.queries){cell_io::emit(std::bit_cast<std::uint32_t>(q.context));
    for(auto value:q.point)cell_io::emit(std::bit_cast<std::uint32_t>(static_cast<float>(value)));
    for(auto value:q.previous_world)cell_io::emit(std::bit_cast<std::uint32_t>(static_cast<float>(value)));}
}
void compare(std::istream &input) {
  using namespace cell_io;
  const auto mode=read(input),cached=read(input),previous=read(input),neighbors=read(input),upward=read(input);
  const auto x=std::bit_cast<std::int32_t>(read(input)),z=std::bit_cast<std::int32_t>(read(input));
  const auto seed=read(input);
  if(mode==5){
    constexpr std::uint32_t path=0x4000,blocks=0x1000,geometry=0x5000;
    std::array<std::byte,0x8000> nodes{};std::array<std::byte,65536> grid{};
    auto word=[&](std::uint32_t address,std::uint32_t value){mco::detail::write_word(nodes,address,value);};
    auto real=[&](std::uint32_t address,float value){word(address,std::bit_cast<std::uint32_t>(value));};
    auto half=[&](std::uint32_t address,std::int16_t value){
      const auto bits=std::bit_cast<std::uint16_t>(value);nodes[address]=static_cast<std::byte>(bits&255);nodes[address+1]=static_cast<std::byte>(bits>>8);
    };
    mco::detail::write_word(grid,0,0xdeadbeef);mco::detail::write_word(grid,4,1);mco::detail::write_word(grid,8,0x200);
    half(0,100);half(2,0);half(4,0);half(6,0);half(8,0);half(10,1);
    const auto block=blocks;
    word(block+0x3c,geometry+0x80);word(block+0x14c,geometry);word(block+0x67c,0);word(block+0x680,8);
    for(unsigned j=0;j<8;++j)word(block+0x6a4+j*4,0xffffffffu);
    real(block+0x664,0);real(block+0x66c,0);real(block+0x670,16);real(block+0x678,16);
    const std::array<std::array<float,3>,4> vertices{{{0,0,0},{16,1,0},{16,3,16},{0,-2,16}}};
    for(unsigned i=0;i<4;++i)for(unsigned j=0;j<3;++j)real(geometry+i*12+j*4,vertices[i][j]);
    for(unsigned j=0;j<4;++j)half(geometry+0x80+j*2,static_cast<std::int16_t>(j));
    for(unsigned j=0;j<8;++j){real(path+j*0x54,static_cast<float>(j*2));real(path+j*0x54+4,2);real(path+j*0x54+8,static_cast<float>(j));}
    const mco::SpatialQueryMemory memory{grid,nodes,0};
    const mco::TrackSurfaceWorld world{memory,{0,0},{1,1},blocks,path,0,8};
    std::array<std::byte,68> query;for(unsigned i=0;i<68;++i)query[i]=static_cast<std::byte>((seed+i*37)&255);
    std::array<float,3> point{static_cast<float>(x),7.f,static_cast<float>(z)};
    const bool found=mco::sample_track_surface(world,query,point,0,{.3f,.8f,-.2f});
    emit(found?1u:0u);emit(query);for(auto value:point)emit(std::bit_cast<std::uint32_t>(value));
    emit_projection(world,x,z);emit_support(world,x,z);return;
  }
  constexpr std::uint32_t base=0x71000000,paths=base+0x1000,blocks=base+0x3000,geometry=base+0x5000;
  std::array<std::byte,0x6000> arena;arena.fill(std::byte{0xa5});
  std::array<std::byte,65536> grid{};
  auto word=[&](std::uint32_t address,std::uint32_t value){mco::detail::write_word(arena,address-base,value);};
  auto real=[&](std::uint32_t address,float value){word(address,std::bit_cast<std::uint32_t>(value));};
  auto half=[&](std::uint32_t address,std::int16_t value){
    const auto bits=std::bit_cast<std::uint16_t>(value);
    arena[address-base]=static_cast<std::byte>(bits&255);arena[address-base+1]=static_cast<std::byte>(bits>>8);
  };
  std::array<std::uint32_t,3> ids{0,1,2};unsigned count=3;
  if(mode==1)count=0;else if(mode==3)ids={2,1,0};else if(mode==4){ids[0]=1;count=1;}
  for(unsigned i=0;i<count;++i)word(base+0x100+i*4,ids[i]);
  if(mode){mco::detail::write_word(grid,0,0xdeadbeef);mco::detail::write_word(grid,4,count);mco::detail::write_word(grid,8,base+0x100);}
  std::array<std::byte,68> query{};
  for(unsigned i=0;i<68;++i)query[i]=static_cast<std::byte>((seed+i*37)&255);
  mco::detail::write_word(query,4,previous);
  mco::detail::write_word(query,12,cached?geometry+0xc0:0);
  for(unsigned j=0;j<4;++j)mco::detail::write_word(query,16+j*4,geometry+j*12);
  for(unsigned b=0;b<3;++b){
    const auto block=blocks+b*0x6c4,geo=geometry+b*0x200;
    word(block+0x3c,geo+0x80);word(block+0x14c,geo);word(block+0x67c,geo+0xc0);word(block+0x680,8);
    for(unsigned j=0;j<8;++j)word(block+0x6a4+j*4,neighbors&&j==7?previous:0xffffffffu);
    real(block+0x664,static_cast<float>(b*24));real(block+0x66c,0);real(block+0x670,static_cast<float>(b*24+16));real(block+0x678,16);
    const std::array<std::array<float,3>,4> vertices{{{0,0,0},{16,1,0},{16,3,16},{0,-2,16}}};
    for(unsigned i=0;i<4;++i)for(unsigned j=0;j<3;++j)real(geo+i*12+j*4,vertices[i][j]);
    for(unsigned j=0;j<4;++j)half(geo+0x80+j*2,static_cast<std::int16_t>(j));
    const std::array<std::int16_t,10> descriptor{0,0,0,0,static_cast<std::int16_t>(100+b),
      static_cast<std::int16_t>((upward&(1u<<b))?32767:-32768),static_cast<std::int16_t>(-200-static_cast<int>(b)),
      static_cast<std::int16_t>(300+b),static_cast<std::int16_t>(-400-static_cast<int>(b)),static_cast<std::int16_t>(500+b)};
    for(unsigned j=0;j<descriptor.size();++j)half(geo+0xc0+j*2,descriptor[j]);
    for(unsigned j=0;j<8;++j){real(paths+(b*8+j)*0x54,static_cast<float>(b*24+j*2));real(paths+(b*8+j)*0x54+8,static_cast<float>(j));}
  }
  const mco::SpatialQueryMemory memory{grid,arena,base};
  const mco::TrackSurfaceWorld world{memory,{0,0},{1,1},blocks,paths,2,24};
  std::array<float,3> point{static_cast<float>(x),7.f,static_cast<float>(z)};
  const bool found=mco::sample_track_surface(world,query,point,0,{0,1,0});
  emit(found?1u:0u);emit(query);
  for(const auto value:point)emit(std::bit_cast<std::uint32_t>(value));
  emit_projection(world,x,z);
  emit_support(world,x,z);
}
}

int main(){return cell_io::run(compare);}
