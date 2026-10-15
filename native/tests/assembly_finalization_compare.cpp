#include "mco/assembly_finalization.hpp"
#include <array>
#include <iostream>
#include <stdexcept>
#include <string>
int main() {
    constexpr char digits[]="0123456789abcdef";
    auto nibble=[](char c) -> unsigned {
        if(c>='0' && c<='9') return c-'0';
        if(c>='a' && c<='f') return c-'a'+10;
        throw std::runtime_error("invalid configuration hex");
    };
    std::string line;
    while(std::getline(std::cin,line)) {
        if(line.size()!=0x1040) throw std::runtime_error("configuration hex length");
        std::array<std::byte,0x820> image;
        for(std::size_t i=0;i<image.size();++i) image[i]=static_cast<std::byte>((nibble(line[i*2])<<4)|nibble(line[i*2+1]));
        const auto out=mco::finalize_loaded_configuration(image,true);
        for(auto b:out) {const auto v=std::to_integer<unsigned>(b);std::cout<<digits[v>>4]<<digits[v&15];}
        std::cout<<'\n';
    }
}
