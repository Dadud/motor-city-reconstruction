#include "mco/body_constructor.hpp"
#include <bit>
#include <cstdint>
#include <stdexcept>
void check(bool value) {if(!value) throw std::runtime_error("startup body regression");}
int main() {
    mco::StartupOwnerImage owner{};std::array<std::byte,0x820> config{};
    auto put=[](auto& image,unsigned offset,std::uint32_t value) {
        for(unsigned k=0;k<4;++k) image[offset+k]=static_cast<std::byte>((value>>(k*8))&255);
    };
    put(config,0x20,std::bit_cast<std::uint32_t>(1000.f));
    put(config,0x38,std::bit_cast<std::uint32_t>(1.1f));
    put(owner,0x18ec,std::bit_cast<std::uint32_t>(.3f));put(owner,0x18f0,std::bit_cast<std::uint32_t>(.3f));
    put(owner,0x18c4,std::bit_cast<std::uint32_t>(2.f));put(owner,0x18b8,std::bit_cast<std::uint32_t>(.75f));
    const auto result=mco::prepare_startup_body(owner,config,{1,1,2},17,true);
    check(result[6]==std::byte{1});
    check(result[0x66]==std::byte{0xa0} && result[0x67]==std::byte{0x3f}); // COM z = 1.25f.
    const auto samples=mco::body_samples(mco::BodyShape::box,{1,1,2});
    check(mco::customize_body_samples(0,samples)==samples);
    check(mco::customize_body_samples(1,samples)[4][1]==.5f);
    bool rejected=false;try {mco::prepare_startup_body(owner,config,{1,1,2},0,false);} catch(const std::invalid_argument&) {rejected=true;}
    check(rejected);
}
