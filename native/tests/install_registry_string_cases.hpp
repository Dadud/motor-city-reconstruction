#pragma once
#include "mco/install_registry_string.hpp"
#include "cell_io.hpp"
#include <vector>
#include <string>
namespace install_registry_string_cases {
struct Boundary{std::uint32_t seed,profile;std::span<std::byte,320> external;std::vector<std::uint32_t> logs;};
inline void put(std::span<std::byte> p,std::uint32_t v){for(unsigned i=0;i<4;++i)p[i]=std::byte((v>>(i*8))&255);}
inline std::uint32_t invoke(mco::RegistryInstallState& s,const mco::RegistryStringCall& c,void* user){auto& b=*static_cast<Boundary*>(user);
 b.logs.push_back(c.id);b.logs.push_back(static_cast<std::uint32_t>(c.args.size()));for(auto x:c.args)b.logs.push_back(x);for(auto x:c.buffer)b.logs.push_back(std::uint32_t(x));b.logs.push_back(c.id==2?1:0);if(c.id==2)b.logs.push_back(c.metadata[1]);for(auto x:s.image)b.logs.push_back(std::uint32_t(x));for(auto x:b.external)b.logs.push_back(std::uint32_t(x));
 const std::string texts[]={"","A","Hello",std::string("\x80Z",2),std::string(255,'X'),std::string(254,'Y'),std::string("A\0TAIL",6),std::string(16,'Q')};const auto& text=texts[(b.seed%64+(b.seed/64)%8+b.seed/512)%8];for(unsigned i=0;i<text.size();++i)c.buffer[i]=std::byte(text[i]);
 if(c.id==1){if(b.profile&32)put(s.image.subspan(4,4),0x10203040);return b.profile&16?1:0;}
 if(c.id==2){c.metadata[0]=b.profile&2?2:1;c.metadata[1]=b.profile&4?0:(b.profile&8?1:255);if(b.profile&32)put(s.image.subspan(4,4),0x20304050);return b.profile&1?5:0;}throw std::invalid_argument("registry string bridge id");
}
inline void compare(std::istream& in){using namespace cell_io;auto seed=read(in),profile=read(in),name=read(in),present=read(in),count=read(in);auto image=cell_io::image<0x210>(in);auto output=cell_io::image<320>(in);mco::RegistryInstallState s{image};Boundary b{seed,profile,output,{}};mco::RegistryStringPlatform p{invoke,&b};auto destination=present?std::span<std::byte>(output):std::span<std::byte>{};emit(mco::registry_read_string(s,p,name,destination,count));emit(image);emit(output);emit(static_cast<std::uint32_t>(b.logs.size()));for(auto x:b.logs)emit(x);}
}
