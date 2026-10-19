#include "mco/install_registry_runtime.hpp"
#include <array>
#include <stdexcept>
#include <string_view>
namespace mco {
void registry_install_prepare_path(RegistryInstallState& s,const RegistryInstallPlatform& p){
 auto bytes=s.image.subspan(0x10c);bytes[0]=std::byte{};
 if(!p.invoke)throw std::invalid_argument("install module filename boundary required");
 const std::array<std::uint32_t,3> args{0,0x10c,0x103};
 if(!p.invoke(s,7,args,bytes.first(0x103),p.user)){bytes[0]=std::byte{};return;}
 std::size_t length=0;while(length<0x103 && bytes[length]!=std::byte{})++length;
 if(length==0x103)throw std::invalid_argument("install module filename must be terminated within 259 bytes");
 for(std::size_t i=0;i<length;++i){const auto value=std::uint32_t(bytes[i]);if(value>='a'&&value<='z')bytes[i]=std::byte(value-32);}
 auto marker=[&]{for(std::size_t i=0;i+4<=length;++i)if(bytes[i]==std::byte{'\\'}&&bytes[i+1]==std::byte{'N'}&&bytes[i+2]==std::byte{'P'}&&bytes[i+3]==std::byte{'S'})return true;return false;};
 auto trim=[&]{for(auto i=length;i>0;--i)if(bytes[i-1]==std::byte{'\\'}){length=i-1;bytes[length]=std::byte{};return;}};
 if(marker())trim();
 trim();
 constexpr std::string_view suffix="\\mcotest.ini";
 if(length+suffix.size()+1>bytes.size())throw std::out_of_range("install module path append exceeds owner image");
 for(std::size_t i=0;i<suffix.size();++i)bytes[length+i]=std::byte(suffix[i]);
 bytes[length+suffix.size()]=std::byte{};
}
}
