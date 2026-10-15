#include "mco/owner_wheel_setup.hpp"
#include <bit>
#include <cstdint>
#include <stdexcept>
int main() {
    mco::StartupOwnerImage owner{};std::array<std::byte,0x820> config{};
    bool rejected=false;
    try {mco::initialize_owner_wheels(owner,config,false);} catch(const std::invalid_argument&) {rejected=true;}
    if(!rejected) throw std::runtime_error("incomplete assembly accepted");
    auto put=[](auto& image,unsigned offset,float v) {
        const auto bits=std::bit_cast<std::uint32_t>(v);
        for(unsigned k=0;k<4;++k) image[offset+k]=static_cast<std::byte>((bits>>(k*8))&255);
    };
    put(owner,0x18ec,.35f);put(owner,0x18f0,.35f);put(config,0x144,205.f);
    put(config,0x124,205.f);put(config,0x228,205.f);
    const auto result=mco::initialize_owner_wheels(owner,config,true);
    if(result[0x6c1]!=std::byte{0} || result[0x8d9]!=std::byte{1} || result[0x9e5]!=std::byte{1})
        throw std::runtime_error("original zero-steering fallback changed");
    if(owner[0x8d9]!=std::byte{0}) throw std::runtime_error("input owner mutated");
}
