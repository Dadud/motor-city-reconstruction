#include "mco/install_registry_query.hpp"
#include <array>
#include <initializer_list>
#include <stdexcept>
namespace mco {
namespace {
std::uint32_t word(std::span<const std::byte> p){std::uint32_t v=0;for(unsigned i=0;i<4;++i)v|=std::uint32_t(p[i])<<(8*i);return v;}
void put(std::span<std::byte> p,std::uint32_t v){for(unsigned i=0;i<4;++i)p[i]=std::byte((v>>(8*i))&255);}
std::uint32_t call(RegistryInstallState&s,const RegistryQueryPlatform&p,std::uint32_t id,std::initializer_list<std::uint32_t> args,std::span<std::byte> buffer={},std::span<std::uint32_t> metadata={},std::span<const std::byte> text={}){
 if(!p.invoke)throw std::invalid_argument("registry query platform required");
 return p.invoke(s,{id,{args.begin(),args.size()},buffer,metadata,text},p.user);
}
void close_old(RegistryInstallState&s,const RegistryQueryPlatform&p){
 const auto handle=word(s.image.subspan(4,4));
 if(handle){call(s,p,1,{handle});put(s.image.subspan(4,4),0);s.image[8]=std::byte{};s.image[0x10c]=std::byte{};}
}
}
void registry_query_close(RegistryInstallState&s,const RegistryQueryPlatform&p){put(s.image.first<4>(),0x83ec68);close_old(s,p);}
bool registry_query_create(RegistryInstallState&s,const RegistryQueryPlatform&p,std::uint32_t root,std::uint32_t path,std::uint32_t access,std::uint32_t owner_identity){
 close_old(s,p);std::array<std::uint32_t,1> disposition{owner_identity};
 return call(s,p,2,{root,path,0,0x88b7a8,0,access,0},s.image.subspan(4,4),disposition)==0;
}
bool registry_query_integer(RegistryInstallState&s,const RegistryQueryPlatform&p,std::uint32_t name,std::span<std::byte,4> output){
 if(!word(s.image.subspan(4,4))||!name)return false;
 if(s.image[8]!=std::byte{}&&s.image[0x10c]!=std::byte{}){
  std::array<std::byte,256> text{};
  const auto size=call(s,p,3,{8,name,0x8e3ac4,255,0x10c},text);
  if(size&&text[0]!=std::byte{}){call(s,p,5,{0x894960},output,{},text);return true;}
 }
 std::array<std::uint32_t,2> metadata{4,4};
 const auto result=call(s,p,4,{word(s.image.subspan(4,4)),name,0},output,metadata);
 return result==0&&metadata[0]==4&&metadata[1]!=0;
}
bool registry_read_integer(RegistryInstallState&s,const RegistryQueryPlatform&p,std::uint32_t name,std::span<std::byte,4> output){
 std::array<std::byte,4> local{};put(local,name);
 if(!registry_query_integer(s,p,name,local))return false;
 for(unsigned i=0;i<4;++i)output[i]=local[i];
 return true;
}
}
