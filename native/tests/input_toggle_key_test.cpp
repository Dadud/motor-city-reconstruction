#include "input_toggle_key_cases.hpp"
using namespace mco;
using input_toggle_key_cases::Calls;
void require(bool b){if(!b)throw std::runtime_error("toggle-key invariant");}
int main(){
    InputToggleKeyPlatform empty{};
    for(auto selector:{3u,0x100u,0xffffffffu})input_toggle_key(selector,0,empty);
    for(auto selector:{0u,1u,2u}){
        Calls f;f.state=0xffff;f.script=3;input_toggle_key(selector,0,f.platform);
        const auto key=selector==0?0x14u:selector==1?0x90u:0x91u;
        const auto scan=selector==0?0x3au:selector==1?0x45u:0x46u;
        require(f.logs.size()==3 && f.logs[0][2]==key);
        require(f.logs[1]==std::array<std::uint32_t,6>{1,1,key,scan,selector==1?1u:0u,0});
        require(f.logs[2]==std::array<std::uint32_t,6>{1,1,key,scan,selector==1?3u:2u,0});
        Calls g;g.state=0x8000;input_toggle_key(selector,0,g.platform);require(g.logs.size()==1);
        Calls h;h.state=1;input_toggle_key(selector,2,h.platform);require(h.logs.size()==3);
    }
    Calls startup;startup.state=1;input_startup_numlock(startup.platform);
    require(startup.logs.size()==3 && startup.logs[1][2]==0x90);
}
