#include "mco/acceleration_table.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <stdexcept>
namespace {
void word(std::array<std::byte,0x820>& c,unsigned offset,std::uint32_t v){
    for(unsigned k=0;k<4;++k)c[offset+k]=static_cast<std::byte>((v>>(k*8))&255);}
void word(std::array<std::byte,0x4a8>& r,unsigned offset,std::uint32_t v){
    for(unsigned k=0;k<4;++k)r[offset+k]=static_cast<std::byte>((v>>(k*8))&255);}
void real(std::array<std::byte,0x4a8>& r,unsigned offset,float v){
    word(r,offset,std::bit_cast<std::uint32_t>(v));}
constexpr float thresholds[8]={10,25,45,65,85,120,130,140};
}
int main() {
    std::array<std::byte,0x820> c{};std::array<std::byte,0x4a8> r{};
    bool rejected=false;
    try{mco::acceleration_table({}, {});}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::runtime_error("incomplete records accepted");
    rejected=false;try{mco::startup_force(c,r,800,0,0.f);}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::runtime_error("unbounded maximum RPM accepted");
    word(c,0x70,6500);word(r,0x104,0x3f800000); // maximum RPM and denominator 1.0f
    rejected=false;try{mco::startup_force(c,r,0,0,0.f);}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::runtime_error("zero RPM accepted");
    rejected=false;try{mco::startup_force(c,r,12001,0,0.f);}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::runtime_error("excessive RPM accepted");
    rejected=false;try{mco::startup_force(c,r,800,8,0.f);}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::runtime_error("selector eight accepted");
    rejected=false;try{mco::acceleration_table(c,r);}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::runtime_error("zero mass accepted");
    word(c,0x20,0x447a0000); // mass 1000.0f
    rejected=false;try{mco::acceleration_table(c,r);}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::runtime_error("zero idle accepted");
    word(c,0x6c,800);
    rejected=false;try{mco::acceleration_table(c,r);}catch(const std::invalid_argument&){rejected=true;}
    if(!rejected)throw std::runtime_error("unbounded shift schedule accepted");
    for(unsigned i=0;i<8;++i)real(r,0xac+i*4,thresholds[i]);
    const auto result=mco::acceleration_table(c,r);
    for(unsigned i=0;i<0x4a8;++i){
        const auto byte=std::to_integer<unsigned char>(result[i]);
        if(i<0x128){
            if(byte!=std::to_integer<unsigned char>(r[i]))throw std::runtime_error("bytes below the outputs changed");
        }else if(byte!=0)throw std::runtime_error("nonzero acceleration without torque");
    }
}
