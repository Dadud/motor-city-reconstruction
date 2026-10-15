#include "mco/body_constructor.hpp"
#include <algorithm>
#include <bit>
#include <stdexcept>
namespace {
void check(bool value) {if(!value) throw std::runtime_error("body constructor regression");}
float number(const mco::StartupOwnerImage& image,unsigned offset) {
    std::uint32_t word=0;for(unsigned k=0;k<4;++k) word|=std::to_integer<std::uint32_t>(image[offset+k])<<(k*8);
    return std::bit_cast<float>(word);
}
}
int main() {
    mco::StartupOwnerImage owner;owner.fill(std::byte{0xa5});
    auto result=mco::construct_body(owner,17,0,{1,.5,2},mco::BodyShape::box,6);
    check(number(result,0x50)==1000);check(number(result,0x74)==8);
    check(std::equal(result.begin()+0x418,result.end(),owner.begin()+0x418));
    check(std::equal(result.begin()+0xe0,result.begin()+0x1e8,result.begin()+0x1e8));
    check(number(result,0x308)==.37f);check(result[4]==std::byte{1});
    const auto cylinder=mco::body_samples(mco::BodyShape::cylinder,{1,.5,2});
    check(cylinder[0][0]==-.707f);check(cylinder[0][1]==-.5f);
    check(cylinder[8][2]==2); // Face positions precede corner rounding.
    const auto pyramid=mco::body_samples(mco::BodyShape::pyramid,{1,.5,2});
    check(pyramid[4][0]==0 && pyramid[4][1]==.5f && pyramid[4][2]==0);
    bool rejected=false;
    try {mco::construct_body(owner,0,-1,{1,1,1},mco::BodyShape::box,0);} catch(const std::invalid_argument&) {rejected=true;}
    check(rejected);
}
