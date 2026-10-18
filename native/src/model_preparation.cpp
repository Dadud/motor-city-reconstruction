#include "mco/model_preparation.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <stdexcept>
#include <string_view>
namespace mco {
namespace {
std::uint32_t word(std::span<const std::uint8_t> b,std::size_t p) {
    if(p>b.size() || b.size()-p<4) throw std::invalid_argument("truncated FCE field");
    return std::uint32_t(b[p]) | std::uint32_t(b[p+1])<<8 |
           std::uint32_t(b[p+2])<<16 | std::uint32_t(b[p+3])<<24;
}
unsigned count(std::span<const std::uint8_t> b) {
    if(b.size()<0x2038 || word(b,0x11c)>64 || word(b,0x58)>16)
        throw std::invalid_argument("bounded FCE header required");
    return word(b,0x11c);
}
Vec3 point(std::span<const std::uint8_t> b,std::size_t p) {
    Vec3 result{};
    for(unsigned i=0;i<3;++i) {
        result[i]=std::bit_cast<float>(word(b,p+i*4));
        if(!std::isfinite(result[i])) throw std::invalid_argument("finite FCE vector required");
    }
    return result;
}
void store(std::span<std::uint8_t> b,std::size_t p,const Vec3& values) {
    for(unsigned i=0;i<3;++i) {
        auto v=std::bit_cast<std::uint32_t>(values[i]);
        for(unsigned j=0;j<4;++j) b[p+i*4+j]=static_cast<std::uint8_t>(v>>(8*j));
    }
}
struct Table {std::size_t start;unsigned size;};
std::optional<Table> table(std::span<const std::uint8_t> b,int part,unsigned stream) {
    auto parts=count(b);
    if(part<0 || static_cast<unsigned>(part)>=parts) return {};
    auto size=word(b,0x520+part*4);
    auto start=std::size_t(0x2038)+word(b,stream)+std::size_t(word(b,0x420+part*4))*12;
    if(size>1000000 || start>b.size() || size>(b.size()-start)/12)
        throw std::invalid_argument("bounded FCE geometry stream required");
    return Table{start,size};
}
}
std::optional<Vec3> model_part_half_extents(std::span<const std::uint8_t> b,int part) {
    auto t=table(b,part,0x14);
    if(!t || !t->size) return {};
    auto low=point(b,t->start),high=low;
    for(unsigned i=1;i<t->size;++i) {
        auto v=point(b,t->start+i*12);
        for(unsigned a=0;a<3;++a) {low[a]=std::min(low[a],v[a]);high[a]=std::max(high[a],v[a]);}
    }
    Vec3 result{};
    for(unsigned a=0;a<3;++a) result[a]=static_cast<float>(std::abs(double(high[a])-low[a])*.5);
    return result;
}
void model_scale_part_streams(std::span<std::uint8_t> b,int part,const Vec3& scales) {
    for(auto s:scales) if(!std::isfinite(s)) throw std::invalid_argument("finite scales required");
    std::array<std::optional<Table>,3> tables{table(b,part,0x14),table(b,part,0x34),table(b,part,0x2c)};
    for(auto t:tables) if(t) for(unsigned i=0;i<t->size;++i) {
        auto v=point(b,t->start+i*12);
        for(unsigned a=0;a<3;++a) v[a]=static_cast<float>(double(v[a])*scales[a]);
        store(b,t->start+i*12,v);
    }
}
bool model_align_secondary(std::span<std::uint8_t> b,std::span<const std::uint8_t> ref,
                           std::optional<int> part) {
    if(b.empty() || ref.empty() || !part) return false;
    auto parts=count(b);
    if(*part<0 || static_cast<unsigned>(*part)>=count(ref)) throw std::invalid_argument("valid reference part required");
    auto target=point(ref,0x120+*part*12);
    for(unsigned i=0;i<parts;++i) {
        auto p=reinterpret_cast<const char*>(b.data()+0xe28+i*64);
        auto end=std::find(p,p+64,'\0');
        if(end==p+64) throw std::invalid_argument("terminated FCE name required");
        if(std::string_view(p,static_cast<std::size_t>(end-p)).find("_W")==std::string_view::npos) continue;
        auto src=point(b,0x120+i*12); Vec3 delta{};
        for(unsigned a=0;a<3;++a) delta[a]=static_cast<float>(double(target[a])-src[a]);
        delta[1]=static_cast<float>(double(delta[1])+double(.05f));
        for(auto t:std::array<Table,2>{Table{0x120,parts},Table{0x5c,word(b,0x58)}})
            for(unsigned j=0;j<t.size;++j) {
                auto v=point(b,t.start+j*12);
                for(unsigned a=0;a<3;++a) v[a]=static_cast<float>(double(v[a])+delta[a]);
                store(b,t.start+j*12,v);
            }
        return true;
    }
    return false;
}
}
