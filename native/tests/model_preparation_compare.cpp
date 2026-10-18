#include "mco/model_preparation.hpp"
#include <bit>
#include <iostream>
#include <stdexcept>
#include <string>
namespace {
std::vector<std::uint8_t> parse(const std::string& s) {
    if(s=="-") return {};
    if(s.size()%2 || s.size()>32*1024*1024) throw std::invalid_argument("bounded hex image required");
    std::vector<std::uint8_t> b;
    for(std::size_t i=0;i<s.size();i+=2) b.push_back(static_cast<std::uint8_t>(std::stoul(s.substr(i,2),nullptr,16)));
    return b;
}
void hex(std::span<const std::uint8_t> b) {
    constexpr char chars[]="0123456789abcdef";
    for(auto v:b) std::cout<<chars[v>>4]<<chars[v&15];
    if(b.empty()) std::cout<<'-';
}
}
int main() {
    char op;int part;std::uint32_t x,y,z;std::string a,b;
    while(std::cin>>op>>part>>x>>y>>z>>a>>b) {
        auto image=parse(a),ref=parse(b);int status=0;std::vector<std::uint8_t> output;
        if(op=='h') {
            auto v=mco::model_part_half_extents(image,part);status=int(v.has_value());
            if(v) for(auto f:*v) {
                auto bits=std::bit_cast<std::uint32_t>(f);
                for(unsigned j=0;j<4;++j) output.push_back(static_cast<std::uint8_t>(bits>>(8*j)));
            }
        } else if(op=='s') {
            mco::model_scale_part_streams(image,part,{std::bit_cast<float>(x),std::bit_cast<float>(y),std::bit_cast<float>(z)});
            output=std::move(image);
        } else if(op=='a') {
            status=mco::model_align_secondary(part==-1 ? std::span<std::uint8_t>{} : image,
                part==-2 ? std::span<const std::uint8_t>{} : ref,
                part==-3 ? std::optional<int>{} : std::optional<int>{part});
            output=std::move(image);
        } else throw std::invalid_argument("unknown operation");
        std::cout<<status<<' ';hex(output);std::cout<<'\n';
    }
}
