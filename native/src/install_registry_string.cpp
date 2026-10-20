#include "mco/install_registry_string.hpp"
#include <array>
#include <stdexcept>
namespace mco {
namespace {
std::uint32_t handle(const RegistryInstallState&s){std::uint32_t v=0;for(unsigned i=0;i<4;++i)v|=std::uint32_t(s.image[4+i])<<(8*i);return v;}
void copy(std::span<std::byte> out,std::span<const std::byte,256> source,std::uint32_t count){bool ended=false;for(std::uint32_t i=0;i<count;++i){if(source[i]==std::byte{})ended=true;out[i]=ended?std::byte{}:source[i];}}
}
bool registry_read_string(RegistryInstallState&s,const RegistryStringPlatform&p,std::uint32_t name,std::span<std::byte> output,std::uint32_t count){
 if(!handle(s)||!name||output.empty()||!count)return false;
 if(count>256||count>output.size())throw std::out_of_range("registry string output/source bound");
 if(!p.invoke)throw std::invalid_argument("registry string platform required");
 if(s.image[8]!=std::byte{}&&s.image[0x10c]!=std::byte{}){
  std::array<std::byte,256> text{};const std::array<std::uint32_t,5> args{8,name,0x8e3ac4,255,0x10c};
  if(p.invoke(s,{1,args,text,{}},p.user)){copy(output,text,count);return true;}
 }
 std::array<std::byte,256> text{};
 // Original type local is uninitialized: its pre-write value is not a claim.
 std::array<std::uint32_t,2> metadata{0,255};const std::array<std::uint32_t,3> args{handle(s),name,0};
 const auto status=p.invoke(s,{2,args,text,metadata},p.user);
 if(status==0&&metadata[0]==1&&metadata[1]!=0){copy(output,text,count);return true;}
 return false;
}
}
