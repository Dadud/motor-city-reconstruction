#pragma once
#include "mco/install_registry_query.hpp"
#include "cell_io.hpp"
#include <vector>
namespace install_registry_query_cases {
struct Boundary {std::uint32_t seed,profile;std::span<std::byte,4> external;std::vector<std::uint32_t> logs;};
inline void put(std::span<std::byte> p,std::uint32_t value){for(unsigned i=0;i<4;++i)p[i]=std::byte((value>>(i*8))&255);}
inline std::uint32_t invoke(mco::RegistryInstallState& s,const mco::RegistryQueryCall& c,void* user){
 auto& b=*static_cast<Boundary*>(user);b.logs.push_back(c.id);b.logs.push_back(static_cast<std::uint32_t>(c.args.size()));for(auto x:c.args)b.logs.push_back(x);
 b.logs.push_back(static_cast<std::uint32_t>(c.buffer.size()));for(auto x:c.buffer)b.logs.push_back(std::uint32_t(x));
 b.logs.push_back(static_cast<std::uint32_t>(c.metadata.size()));for(auto x:c.metadata)b.logs.push_back(x);
 b.logs.push_back(static_cast<std::uint32_t>(c.text.size()));for(auto x:c.text)b.logs.push_back(std::uint32_t(x));
 for(auto x:s.image)b.logs.push_back(std::uint32_t(x));for(auto x:b.external)b.logs.push_back(std::uint32_t(x));
 switch(c.id){
 case 1:if(b.profile&32){put(s.image.subspan(4,4),0xdeadbeef);s.image[8]=std::byte{'Z'};s.image[0x10c]=std::byte{'Q'};}return 17;
 case 2:put(c.buffer,0x12345678);c.metadata[0]=2;if(b.profile&32){s.image[8]=std::byte{'R'};s.image[0x10c]=std::byte{'S'};}return b.profile&1?5:0;
 case 3:if(b.profile&16){if(b.seed%7){c.buffer[0]=std::byte{'3'};c.buffer[1]=std::byte{'7'};c.buffer[2]=std::byte{};}if(b.profile&32)put(s.image.subspan(4,4),0x10203040);return 1;}if(b.profile&32)put(s.image.subspan(4,4),0x10203040);return 0;
 case 4:{c.metadata[0]=b.profile&2?1:4;c.metadata[1]=b.profile&4?0:(b.profile&8?2:4);auto value=0xa5000000+b.seed;for(unsigned i=0;i<((b.profile&8)?2u:4u);++i)c.buffer[i]=std::byte((value>>(i*8))&255);if(b.profile&32)put(s.image.subspan(4,4),0x20304050);return b.profile&1?5:0;}
 case 5:if(b.seed%5){put(c.buffer,0x12340000+b.seed);return 1;}return 0;
 default:throw std::invalid_argument("registry query boundary id");
 }
}
inline void compare(std::istream& in){using namespace cell_io;auto mode=read(in),seed=read(in),profile=read(in),name=read(in);auto image=cell_io::image<0x210>(in);std::array<std::byte,4> output{std::byte{0x55},std::byte{0x66},std::byte{0x77},std::byte{0x88}};mco::RegistryInstallState state{image};Boundary b{seed,profile,output,{}};mco::RegistryQueryPlatform p{invoke,&b};std::uint32_t result=0;
 auto step=[&](std::uint32_t which){result=0;switch(which){case 0:mco::registry_query_close(state,p);break;case 1:result=mco::registry_query_create(state,p,0x80000002,0x71001000,0xf003f,0x71002000);break;case 2:result=mco::registry_query_integer(state,p,name,output);break;case 3:result=mco::registry_read_integer(state,p,name,output);break;default:throw std::invalid_argument("registry query mode");}
 emit(result);emit(image);emit(output);emit(static_cast<std::uint32_t>(b.logs.size()));for(auto x:b.logs)emit(x);};
 if(mode==4){for(auto which:{2u,3u,1u,2u,0u,3u})step(which);}else step(mode);
}
}
