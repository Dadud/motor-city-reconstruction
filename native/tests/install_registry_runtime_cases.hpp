#pragma once
#include "mco/install_registry_runtime.hpp"
#include "cell_io.hpp"
#include <vector>
namespace install_registry_runtime_cases {
struct Boundary{std::uint32_t seed,profile;std::vector<std::uint32_t> logs;};
inline std::uint32_t word(std::span<const std::byte> p){std::uint32_t v=0;for(unsigned i=0;i<4;++i)v|=std::uint32_t(p[i])<<(i*8);return v;}
inline void put(std::span<std::byte> p,std::uint32_t v){for(unsigned i=0;i<4;++i)p[i]=std::byte((v>>(i*8))&255);}
inline std::uint32_t invoke(mco::RegistryInstallState& s,std::uint32_t id,std::span<const std::uint32_t> args,std::span<std::byte> out,void* user){
 auto& b=*static_cast<Boundary*>(user);b.logs.push_back(id);b.logs.push_back(static_cast<std::uint32_t>(args.size()));for(auto x:args)b.logs.push_back(x);for(auto x:s.image)b.logs.push_back(std::uint32_t(x));b.logs.push_back(s.language);
 switch(id){
 case 1:{const char text[]="SYNTHETIC-PATH";for(unsigned i=0;i<sizeof(text);++i)s.image[0x10c+i]=std::byte(text[i]);if(b.profile&4)put(s.image.subspan(4,4),0xdead1234);return 0;}
 case 2:if(b.profile&8){put(s.image.subspan(4,4),0xcafef00d);s.image[8]=std::byte{'Z'};s.image[0x10c]=std::byte{'Q'};}return 123;
 case 3:case 5:put(out,id==3&&(b.profile&2)?0:0x12345678);if(b.profile&16){s.image[8]=std::byte{'R'};s.image[0x10c]=std::byte{'S'};}return id==3&&(b.profile&1)?5:0;
 case 4:{const unsigned sizes[]={0,3,258,300};const auto size=sizes[b.seed%4];for(unsigned i=0;i<out.size();++i)out[i]=i<size?std::byte(65+(b.seed+i)%26):std::byte{};if(b.profile&32)put(s.image.subspan(4,4),0x87654321);return 0x71002008;}
 case 6:if(!(b.profile&1)){auto value=0x12340000+b.seed;for(unsigned i=0;i<((b.profile&2)?2u:4u);++i)out[8+i]=std::byte((value>>(i*8))&255);}if(b.profile&16){put(out.subspan(0,4),7);put(out.subspan(4,4),2);}return b.profile&1?234:0;
 default:throw std::invalid_argument("install registry boundary id");
 }
}
inline void compare(std::istream& in){using namespace cell_io;auto mode=read(in),seed=read(in);Boundary b{seed,read(in),{}};auto image=cell_io::image<0x210>(in);mco::RegistryInstallState s{image,read(in)};mco::RegistryInstallPlatform p{invoke,&b};std::uint32_t result=0;
 switch(mode){case 0:mco::registry_install_construct(s,p,0x80000002,0x71001000,0xf003f);result=0x71002000;break;case 1:result=mco::registry_install_reopen(s,p,0x80000002,0x71001000,0xf003f);break;case 2:result=mco::registry_install_is_open(s);break;case 3:mco::registry_install_language(s,p);break;default:throw std::invalid_argument("install registry mode");}
 emit(result);emit(image);emit(s.language);emit(static_cast<std::uint32_t>(b.logs.size()));for(auto x:b.logs)emit(x);
}
}
