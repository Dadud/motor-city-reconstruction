#include "mco/startup_balance.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <stdexcept>
int main() {
    std::array<std::byte,0x820> config{};
    auto put=[&](unsigned offset,float value) {auto word=std::bit_cast<std::uint32_t>(value);for(unsigned k=0;k<4;++k) config[offset+k]=static_cast<std::byte>((word>>(k*8))&255);};
    put(0x20,1000);put(0x28,200);put(0x38,.5334f);put(0xfc,15000);put(0x104,18000);
    const auto result=mco::startup_load_coefficient(config);
    if(!(result>0 && result<1)) throw std::runtime_error("startup load regression");
    bool rejected=false;try {mco::startup_balance_coefficient(config);} catch(const std::invalid_argument&) {rejected=true;}
    if(!rejected) throw std::runtime_error("zero geometry accepted");
    rejected=false;try {mco::startup_load_coefficient({});} catch(const std::invalid_argument&) {rejected=true;}
    if(!rejected) throw std::runtime_error("incomplete config accepted");
}
