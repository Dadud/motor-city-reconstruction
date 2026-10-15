#include "mco/owner_wheel_setup.hpp"
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
std::vector<std::byte> decode(const std::string& hex,std::size_t size) {
    if(hex.size()!=size*2) throw std::runtime_error("invalid startup fixture size");
    auto nibble=[](char c)->unsigned {
        if(c>='0' && c<='9') return c-'0';if(c>='a' && c<='f') return c-'a'+10;
        throw std::runtime_error("invalid fixture hex");
    };
    std::vector<std::byte> out(size);
    for(std::size_t k=0;k<size;++k) out[k]=static_cast<std::byte>((nibble(hex[k*2])<<4)|nibble(hex[k*2+1]));return out;
}
std::string encode(std::span<const std::byte> bytes) {
    constexpr char digits[]="0123456789abcdef";std::string out(bytes.size()*2,'0');
    for(std::size_t k=0;k<bytes.size();++k) {const auto v=std::to_integer<unsigned>(bytes[k]);out[k*2]=digits[v>>4];out[k*2+1]=digits[v&15];}return out;
}
}
int main() {
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);std::string line;
    while(std::getline(std::cin,line)) {
        std::istringstream input(line);std::string owner,config;
        if(!(input>>owner>>config)) throw std::runtime_error("invalid startup fixture row");
        input>>std::ws;if(!input.eof()) throw std::runtime_error("trailing startup fixture fields");
        const auto image=decode(owner,0x2000),data=decode(config,0x820);
        std::cout<<encode(mco::initialize_owner_wheels(image,data,true))<<' '<<encode(mco::adjust_owner_stance(image))<<'\n';
    }
}
