#include "input_device_state_cases.hpp"
#include <stdexcept>
int main(){
    auto require=[](bool ok,const char* message){if(!ok)throw std::runtime_error(message);};
    input_device_state_cases::Fixture f;f.config={6,1,0,15,0,0,0,0,1,0,0,7};
    f.initialize();auto s=f.state();f.access=&s;
    auto result=mco::input_device_state(s,6);
    require(result.data()==f.keyboard.data() && result.size()==260,"failed acquisition discarded keyboard image");
    require(f.keyboard[0]==std::byte{0x78} && f.keyboard[3]==std::byte{0x12},"keyboard prefix cleared");
    for(unsigned i=4;i<260;++i)require(f.keyboard[i]==std::byte{},"failed payload not cleared");
    require(s.enabled==0 && s.device==0x71001100,"callback global mutations lost");
    const auto calls=f.methods.logs.size();
    require(mco::input_device_state(s,6).empty() && f.methods.logs.size()==calls,"disabled accessor called device");
    mco::input_device_state(s,99);
    require(f.logs.back()[1]==99 && f.logs.back()[3]==0x84a0f0 && f.logs.back()[4]==0x1c1,"invalid kind diagnostic order changed");
    input_device_state_cases::Fixture info;info.config={2,1,3,0,0,0,0,0,0,0,1,0};info.initialize();auto is=info.state();info.access=&is;
    require(mco::input_device_state(is,2).empty() && info.information[1]==std::byte{20},"failed information result or side effects lost");
    info.config[10]=0;
    require(mco::input_device_state(is,2).data()==info.information.data(),"successful information pointer lost");
}
