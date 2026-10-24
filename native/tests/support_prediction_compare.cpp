#include "mco/support_prediction.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
template <class T> T get(const std::vector<std::uint8_t> &b, std::size_t p) {
  T x{}; std::memcpy(&x, b.data() + p, sizeof x); return x;
}
template <class T> void put(std::vector<std::uint8_t> &b, std::size_t p, T x) {
  std::memcpy(b.data() + p, &x, sizeof x);
}
std::uint32_t address(std::optional<std::uint32_t> id) {
  return id ? 0x71008000u + *id * 8u : 0;
}
void write_record(std::vector<std::uint8_t> &b, std::size_t p, const mco::SupportRecord &r) {
  put(b,p,r.sector); put(b,p+4,r.group); put(b,p+8,r.status); put(b,p+12,address(r.surface_id));
  for (std::size_t i=0;i<4;++i) put(b,p+16+i*4,address(r.vertex_ids[i]));
}
}
int main() {
  std::string hex; unsigned mask; int rewrite;
  while (std::cin >> hex >> mask >> rewrite) {
    try {
      if (hex.size()!=0x4000 || mask>15 || (rewrite!=0 && rewrite!=1)) return 2;
      std::vector<std::uint8_t> image(0x2000);
      for(std::size_t i=0;i<image.size();++i) image[i]=static_cast<std::uint8_t>(std::stoul(hex.substr(i*2,2),nullptr,16));
      mco::SupportPredictionState s;
      for(int i=0;i<3;++i){s.position[i]=get<float>(image,8+i*4);s.velocity[i]=get<float>(image,0x14+i*4);}
      for(int i=0;i<9;++i)s.to_world[i]=get<float>(image,0xc10+i*4);
      s.context=get<std::int32_t>(image,0x370);s.fallback_surface=get<std::uint32_t>(image,0x404);s.support_count=get<std::int32_t>(image,0xc08);
      for(std::size_t i=0;i<4;++i){auto base=0x5fc+i*0x10c;auto &w=s.wheels[i];
        for(int j=0;j<3;++j){w.world_point[j]=get<float>(image,base+0x34+j*4);w.local_point[j]=get<float>(image,base+0x100+j*4);}
        w.clear_reference=get<float>(image,base+0xb8);w.support_delta=get<float>(image,base+0xe8);w.surface_class=get<std::uint32_t>(image,base+0x58);w.contact=image[base+0xec]!=0;
        auto rp=base+0x14;w.record.sector=get<std::int32_t>(image,rp);w.record.group=get<std::int32_t>(image,rp+4);w.record.status=get<std::uint32_t>(image,rp+8);
        auto sid=get<std::uint32_t>(image,rp+12);if(sid)w.record.surface_id=(sid-0x71008000u)/8u;
        for(int j=0;j<4;++j){auto id=get<std::uint32_t>(image,rp+16+j*4);if(id)w.record.vertex_ids[j]=(id-0x71008000u)/8u;}
        if(w.record.surface_id)w.record.surface_code=0x5a;
      }
      std::vector<mco::SupportQuery> queries;
      auto out=mco::predict_support(std::move(s),[&](const mco::SupportQuery&q){queries.push_back(q);const auto slot=q.slot;const bool found=(mask&(1u<<slot))!=0;
        mco::SupportProjection p;p.point=q.point;p.reference_position=q.point;
        if(rewrite)p.reference_position[1]=static_cast<float>(p.reference_position[1]+.125);
        if(found)p.point[1]=static_cast<float>(-.3+slot*.1);
        p.record.sector=q.context;p.record.group=q.context>>3;p.record.status=3+slot;
        if(found){p.record.surface_id=100+slot;p.record.vertex_ids={10+slot*4,11+slot*4,12+slot*4,13+slot*4};p.record.surface_code=std::array<std::uint8_t,4>{0,0xff,0xa6,20}[slot];}
        return p;});
      for(std::size_t i=0;i<4;++i){auto base=0x5fc+i*0x10c;const auto&w=out.state.wheels[i];write_record(image,base+0x14,w.record);
        for(int j=0;j<3;++j)put(image,base+0x34+j*4,static_cast<float>(w.world_point[j]));put(image,base+0xb8,static_cast<float>(w.clear_reference));put(image,base+0xe8,static_cast<float>(w.support_delta));put(image,base+0x58,w.surface_class);image[base+0xec]=w.contact?1:0;
      }
      put(image,0xc08,out.state.support_count);
      for(auto b:image)std::cout<<std::hex<<std::setw(2)<<std::setfill('0')<<unsigned(b);std::cout<<std::dec<<std::setprecision(17);
      for(const auto&q:queries){std::cout<<' '<<q.context;for(auto x:q.point)std::cout<<' '<<x;for(auto x:q.previous_world)std::cout<<' '<<x;}
      std::cout<<'\n';
    } catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 3;}
  }
}
