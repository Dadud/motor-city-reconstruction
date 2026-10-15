#include "mco/mechanical_loaders.hpp"
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
std::vector<std::byte> decode(const std::string& hex,std::size_t size) {
    if(hex.size()!=size*2) throw std::runtime_error("invalid mechanical fixture size");
    auto nibble=[](char c) -> unsigned {
        if(c>='0' && c<='9') return c-'0';
        if(c>='a' && c<='f') return c-'a'+10;
        throw std::runtime_error("invalid mechanical fixture hex");
    };
    std::vector<std::byte> bytes(size);
    for(std::size_t i=0;i<size;++i) bytes[i]=static_cast<std::byte>((nibble(hex[i*2])<<4)|nibble(hex[i*2+1]));
    return bytes;
}
std::string encode(std::span<const std::byte> bytes) {
    constexpr char digits[]="0123456789abcdef";
    std::string out(bytes.size()*2,'0');
    for(std::size_t i=0;i<bytes.size();++i) {
        const auto v=std::to_integer<unsigned>(bytes[i]);out[i*2]=digits[v>>4];out[i*2+1]=digits[v&15];
    }
    return out;
}
}
int main() {
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    std::string line;
    while(std::getline(std::cin,line)) {
        std::istringstream input(line);std::uint32_t kind;std::string config,component;
        if(!(input>>kind>>config>>component)) throw std::runtime_error("invalid mechanical fixture row");
        input>>std::ws;if(!input.eof()) throw std::runtime_error("trailing mechanical fixture fields");
        const auto result=mco::load_mechanical_component(kind,decode(config,0x820),decode(component,0x984));
        std::cout<<result.status<<' '<<encode(result.configuration)<<' '<<encode(result.component)<<'\n';
    }
}
