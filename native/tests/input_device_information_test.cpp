#include "input_device_information_cases.hpp"
#include <stdexcept>
int main(){
    using mco::detail::read_word;
    auto require=[](bool ok,const char* message){if(!ok)throw std::runtime_error(message);};
    input_device_information_cases::Fixture f;f.config={2,257,2,3,1,0,0,7,1,260,0,33};f.initialize();auto d=f.device();
    require(mco::input_device_information(d,f.platform(),f.output)==0,"enumeration status changed");
    require(read_word(f.output,4)==3 && read_word(f.output,8)==3 && read_word(f.output,12)==7 && read_word(f.output,16)==1,"probe masks or capability mapping changed");
    require(f.logs.size()==8 && f.output[21]==std::byte{} && f.output[278]==std::byte{} && f.output[279]==std::byte{} && f.output[538]!=std::byte{} && f.output[539]==std::byte{},"bounded padded name copy changed");
    for(unsigned i=0;i<f.logs.size();++i)require(f.logs[i][1]==((7+i)&1),"information vtable not reloaded");
    require(f.logs[2][5]==316 && f.logs[3][5]==317,"object record size reset between probes");
    input_device_information_cases::Fixture flip;flip.config={2,0,0,2,0,0,0,0,0,0,0,2};flip.initialize();auto fd=flip.device();
    mco::input_device_information(fd,flip.platform(),flip.output);
    require(flip.logs[2][3]==12 && flip.logs[3][3]==49,"device type not reloaded between button probes");
    input_device_information_cases::Fixture limit;limit.config={2,0,0xffffffff,0xffffffff,0xffffffff,0,0,0,0,0,1,0};limit.initialize();auto ld=limit.device();
    require(mco::input_device_information(ld,limit.platform(),limit.output)==0 && limit.objects==44,"failed probes exceeded hard limits or escaped as return status");
    input_device_information_cases::Fixture mutation;mutation.config={2,0,0,32,0,0,0,0,0,0,1,4};mutation.initialize();auto md=mutation.device();
    mco::input_device_information(md,mutation.platform(),mutation.output);
    require(mutation.objects==13,"reported counts not reloaded after callback");
    input_device_information_cases::Fixture fail;fail.config={4,0,1,1,1,1,0,0,0,0,0,0};fail.initialize();auto ed=fail.device();
    require(mco::input_device_information(ed,fail.platform(),fail.output)==1 && fail.logs.size()==1 && read_word(fail.output,0)==0,"instance failure did not stop after clearing");
    fail.config[5]=0;fail.config[6]=0x80004005;fail.logs.clear();
    require(mco::input_device_information(ed,fail.platform(),fail.output)==0x80004005 && fail.logs.size()==2 && read_word(fail.output,0)==4,"capability failure lost copied instance data");
}
