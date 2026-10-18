#include "mco/model_preparation.hpp"
#include <bit>
#include <stdexcept>
namespace {
void word(std::vector<std::uint8_t>& b,unsigned p,std::uint32_t v) {
    for(unsigned i=0;i<4;++i) b[p+i]=static_cast<std::uint8_t>(v>>(8*i));
}
void scalar(std::vector<std::uint8_t>& b,unsigned p,float v) {word(b,p,std::bit_cast<std::uint32_t>(v));}
void require(bool condition) {
    if(!condition) throw std::runtime_error("model preparation check failed");
}
}
int main() {
    std::vector<std::uint8_t> b(0x2050);
    word(b,0x11c,1);word(b,0x520,2);
    scalar(b,0x2038,1.f);scalar(b,0x2044,-3.f);
    auto bounds=mco::model_part_half_extents(b,0);
    require(bounds && (*bounds)[0]==2.f);
    require(!mco::model_part_half_extents(b,-1));
    require(!mco::model_part_half_extents(b,1));
    // Three aliased streams execute sequentially, applying the scale thrice.
    mco::model_scale_part_streams(b,0,{2.f,1.f,1.f});
    require(mco::model_part_half_extents(b,0)->at(0)==16.f);
    auto before=b;
    require(!mco::model_align_secondary(b,b,std::nullopt));require(b==before);
    require(!mco::model_align_secondary(b,b,0));require(b==before);
    b[0xe28]='_';b[0xe29]='W';
    auto ref=b;scalar(ref,0x120,3.25f);
    require(mco::model_align_secondary(b,ref,0));
    require(b[0x2038]==before[0x2038]);
    word(b,0x520,1000001);
    bool rejected=false;
    try {mco::model_part_half_extents(b,0);} catch(const std::invalid_argument&) {rejected=true;}
    require(rejected);
}
