#include "mco/install_registry_string.hpp"
#include <array>
#include <stdexcept>
static std::uint32_t invoke(mco::RegistryInstallState&,const mco::RegistryStringCall& c,void* user){auto kind=*static_cast<unsigned*>(user);if(c.id==1){if(kind==0)return 1;if(kind==1){c.buffer[0]=std::byte{'A'};c.buffer[1]=std::byte{'B'};c.buffer[2]=std::byte{'C'};return 1;}return 0;}c.metadata[0]=kind==2?2:1;c.metadata[1]=kind==3?0:1;c.buffer[0]=std::byte{'Z'};return 0;}
int main(){std::array<std::byte,0x210> image{};std::array<std::byte,320> output;output.fill(std::byte{0xcc});mco::RegistryInstallState s{image};if(mco::registry_read_string(s,{},1,output,1))return 1;image[4]=std::byte{1};image[8]=std::byte{'K'};image[0x10c]=std::byte{'P'};unsigned kind=0;mco::RegistryStringPlatform p{invoke,&kind};
 if(!mco::registry_read_string(s,p,1,output,4)||output[0]!=std::byte{}||output[3]!=std::byte{}||output[4]!=std::byte{0xcc})return 2;
 output.fill(std::byte{0xcc});kind=1;if(!mco::registry_read_string(s,p,1,output,2)||output[0]!=std::byte{'A'}||output[1]!=std::byte{'B'}||output[2]!=std::byte{0xcc})return 3;
 kind=2;const auto before=output;if(mco::registry_read_string(s,p,1,output,4)||output!=before)return 4;
 kind=3;if(mco::registry_read_string(s,p,1,output,4)||output!=before)return 5;
 kind=4;if(!mco::registry_read_string(s,p,1,output,4)||output[0]!=std::byte{'Z'}||output[3]!=std::byte{})return 6;
 if(mco::registry_read_string(s,{},0,output,4)||mco::registry_read_string(s,{},1,{},4)||mco::registry_read_string(s,{},1,output,0))return 7;
 bool bound=false,bridge=false;try{mco::registry_read_string(s,p,1,output,257);}catch(const std::out_of_range&){bound=true;}try{mco::registry_read_string(s,{},1,output,1);}catch(const std::invalid_argument&){bridge=true;}return bound&&bridge?0:8;
}
