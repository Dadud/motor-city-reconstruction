#include "input_mouse_state_set_cases.hpp"
using namespace mco;
using input_mouse_state_set_cases::Fixture;
void require(bool b){if(!b)throw std::runtime_error("mouse state invariant");}
int main(){
    std::array<std::uint32_t,15> words{};std::uint32_t width=640,height=480;
    InputMouseLifetimeState lifetime{words,width,height};
    std::uint32_t mode=4,state8=0,state9=0,callback=0x7000b000,file=0,line=0;
    InputMouseStateSet s{lifetime,mode,state8,state9,callback,file,line};
    Fixture simple;
    require(input_mouse_state_set(s,simple.platform(),3,0xffffffff));
    require(words[4]==0xffffffff && simple.logs.size()==1 && simple.logs[0][0]==0x6f07f0);
    require(simple.logs[0][4]==0xffffffff && simple.logs[0][5]==0);
    simple.logs.clear();mode=0;
    require(input_mouse_state_set(s,simple.platform(),4,0x80000000) && simple.logs.empty());
    require(words[5]==0x80000000);
    require(input_mouse_state_set(s,simple.platform(),5,0x12345678) && words[6]==0x12345678);
    require(input_mouse_state_set(s,simple.platform(),8,17) && state8==17);
    require(input_mouse_state_set(s,simple.platform(),9,19) && state9==19);
    simple.config[1]=16;
    require(!input_mouse_state_set(s,simple.platform(),0xffffffff,5));
    require(simple.logs.back()[25]==0x84a004 && simple.logs.back()[26]==0x185 && file==0xcafe);
    simple.logs.clear();mode=0;
    require(input_mouse_state_set(s,simple.platform(),7,5) && mode==5);
    require(simple.logs.size()==1 && simple.logs[0][26]==0x155);
    simple.logs.clear();require(input_mouse_state_set(s,simple.platform(),7,5) && simple.logs.empty());
    words[11]=0x71001400;words[12]=0x71001000;mode=0;
    Fixture retry;retry.config={1,3,0};
    require(input_mouse_state_set(s,retry.platform(),7,5) && mode==5);
    require(retry.logs.size()==6);
    require(retry.logs[1][0]==0x34 && retry.logs[1][1]==0x70009034 && retry.logs[1][2]==0x71001100);
    require(retry.logs[1][4]==0xabcdef00 && retry.logs[1][5]==5);
    require(retry.logs[2][0]==0x20 && retry.logs[5][0]==0x1c);
    words[12]=0x71001000;mode=0;Fixture failure;failure.config={2,0,0};
    require(!input_mouse_state_set(s,failure.platform(),7,0xffffffff) && mode==0xffffffff);
    require(failure.logs.size()==6 && failure.logs[1][5]==6 && failure.logs.back()[0]==0x1c);
    words[12]=0x71001000;mode=0;Fixture blocked;blocked.config={3,0,0};
    require(!input_mouse_state_set(s,blocked.platform(),7,5) && blocked.logs.size()==3);
    words[12]=0x71001000;mode=0;Fixture exclusive;exclusive.config={3,2,0};
    require(input_mouse_state_set(s,exclusive.platform(),7,4) && mode==4);
    require(exclusive.logs.size()==2 && exclusive.logs[0][0]==0x20 && exclusive.logs[1][0]==0x6f07f0);
}
