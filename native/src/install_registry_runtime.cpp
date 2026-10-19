#include "mco/install_registry_runtime.hpp"
#include <array>
#include <initializer_list>
#include <stdexcept>
namespace mco {
namespace {
std::uint32_t word(std::span<const std::byte> p){std::uint32_t v=0;for(unsigned i=0;i<4;++i)v|=std::uint32_t(p[i])<<(i*8);return v;}
void put(std::span<std::byte> p,std::uint32_t v){for(unsigned i=0;i<4;++i)p[i]=std::byte((v>>(i*8))&255);}
std::uint32_t call(RegistryInstallState& s,const RegistryInstallPlatform& p,std::uint32_t id,std::initializer_list<std::uint32_t> args,std::span<std::byte> out={}){
 if(!p.invoke)throw std::invalid_argument("install registry platform boundary required");
 return p.invoke(s,id,{args.begin(),args.size()},out,p.user);
}
void close_old(RegistryInstallState& s,const RegistryInstallPlatform& p){
 if(word(s.image.subspan(4,4))){call(s,p,2,{word(s.image.subspan(4,4))});put(s.image.subspan(4,4),0);s.image[8]=std::byte{};s.image[0x10c]=std::byte{};}
}
}
bool registry_install_reopen(RegistryInstallState& s,const RegistryInstallPlatform& p,std::uint32_t root,std::uint32_t path,std::uint32_t access){
 close_old(s,p);const auto status=call(s,p,3,{root,path,0,access},s.image.subspan(4,4));
 if(status){put(s.image.subspan(4,4),0);return false;}
 call(s,p,4,{8,path,0x103},s.image.subspan(8,0x103));return true;
}
void registry_install_construct(RegistryInstallState& s,const RegistryInstallPlatform& p,std::uint32_t root,std::uint32_t path,std::uint32_t access){
 put(s.image.subspan(0,4),0x83ec68);put(s.image.subspan(4,4),0);s.image[8]=std::byte{};s.image[0x10c]=std::byte{};
 registry_install_prepare_path(s,p);registry_install_reopen(s,p,root,path,access);
}
bool registry_install_is_open(const RegistryInstallState& s){return word(s.image.subspan(4,4))!=0;}
void registry_install_language(RegistryInstallState& s,const RegistryInstallPlatform& p){
 std::array<std::byte,4> handle{};
 if(call(s,p,5,{0x80000002,0x896154,0,0xf003f},handle)!=0)throw std::invalid_argument("language recovery supports successful registry open only");
 const auto id=word(handle);std::array<std::byte,12> locals{};put(std::span(locals).subspan(0,4),4);put(std::span(locals).subspan(4,4),4);
 call(s,p,6,{id,0x8961c4,0,4,4,0},locals);call(s,p,2,{id});s.language=word(std::span(locals).subspan(8,4));
}
}
