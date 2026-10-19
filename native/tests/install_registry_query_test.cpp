#include "mco/install_registry_query.hpp"
#include <array>
#include <stdexcept>
static void put(std::span<std::byte> out,std::uint32_t v){for(unsigned i=0;i<4;++i)out[i]=std::byte((v>>(i*8))&255);}
static std::uint32_t word(std::span<const std::byte> p){std::uint32_t v=0;for(unsigned i=0;i<4;++i)v|=std::uint32_t(p[i])<<(8*i);return v;}
static std::uint32_t bridge(mco::RegistryInstallState&,const mco::RegistryQueryCall& c,void* user){auto mode=*static_cast<unsigned*>(user);if(c.id==3){if(mode==1){c.buffer[0]=std::byte{'x'};return 1;}return 0;}if(c.id==5)return 0;if(c.id==4){c.buffer[0]=std::byte{0xaa};c.buffer[1]=std::byte{0xbb};c.metadata[0]=4;c.metadata[1]=2;return mode==3?5:0;}throw std::invalid_argument("test boundary");}
int main(){std::array<std::byte,0x210> bytes{};mco::RegistryInstallState s{bytes};std::array<std::byte,4> output{};if(mco::registry_query_integer(s,{},1,output))return 1;
 put(std::span(bytes).subspan(4,4),1);bytes[8]=std::byte{'K'};bytes[0x10c]=std::byte{'P'};unsigned mode=1;mco::RegistryQueryPlatform p{bridge,&mode};put(output,0x11223344);
 if(!mco::registry_query_integer(s,p,0x71001000,output)||word(output)!=0x11223344)return 2;
 if(!mco::registry_read_integer(s,p,0x71001000,output)||word(output)!=0x71001000)return 3;
 mode=2;put(output,0x11223344);if(!mco::registry_query_integer(s,p,0x71001000,output)||word(output)!=0x1122bbaa)return 4;
 if(!mco::registry_read_integer(s,p,0x71001000,output)||word(output)!=0x7100bbaa)return 5;
 mode=3;put(output,0x11223344);if(mco::registry_read_integer(s,p,0x71001000,output)||word(output)!=0x11223344)return 6;
 bool rejected=false;try{mco::registry_query_integer(s,{},0x71001000,output);}catch(const std::invalid_argument&){rejected=true;}return rejected?0:7;
}
