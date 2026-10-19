#include "mco/install_registry_runtime.hpp"
#include <array>
#include <stdexcept>
#include <string>
struct Fixture{std::string text;std::uint32_t result;bool terminate=true;};
static std::uint32_t module(mco::RegistryInstallState&,std::uint32_t id,std::span<const std::uint32_t> args,std::span<std::byte> out,void* user){
 if(id!=7||args.size()!=3||args[0]!=0||args[1]!=0x10c||args[2]!=259)throw std::invalid_argument("module boundary shape");
 auto& f=*static_cast<Fixture*>(user);for(unsigned i=0;i<f.text.size();++i)out[i]=std::byte(f.text[i]);if(f.terminate)out[f.text.size()]=std::byte{};return f.result;
}
int main(){std::array<std::byte,0x210> bytes{};mco::RegistryInstallState s{bytes};Fixture f{"C:\\Games\\nps\\mcity.exe",22};mco::RegistryInstallPlatform p{module,&f};mco::registry_install_prepare_path(s,p);
 const std::string expected="C:\\GAMES\\mcotest.ini";for(unsigned i=0;i<expected.size();++i)if(bytes[0x10c+i]!=std::byte(expected[i]))return 1;if(bytes[0x10c+expected.size()]!=std::byte{})return 2;
 f={"WRITTEN",0};mco::registry_install_prepare_path(s,p);if(bytes[0x10c]!=std::byte{}||bytes[0x10d]!=std::byte{'R'})return 3;
 f={std::string(259,'x'),259,false};bool unterminated=false;try{mco::registry_install_prepare_path(s,p);}catch(const std::invalid_argument&){unterminated=true;}if(!unterminated)return 4;
 f={std::string(258,'x'),258};bool overflow=false;try{mco::registry_install_prepare_path(s,p);}catch(const std::out_of_range&){overflow=true;}return overflow?0:5;
}
