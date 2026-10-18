#include "input_mouse_lifetime_cases.hpp"
using namespace mco;
using input_mouse_lifetime_cases::Fixture;
void require(bool b){if(!b)throw std::runtime_error("mouse lifetime invariant");}
int main(){
    std::array<std::uint32_t,15> words{};std::uint32_t width=640,height=480;
    InputMouseLifetimeState state{words,width,height};Fixture f;f.config[2]=128;
    require(input_mouse_lifetime(state,f.platform(),0x71001400)==1);
    require(words[11]==0x71001000 && words[12]==0x71001200 && words[14]==1);
    require(words[0]==1200 && words[1]==640 && words[2]==480 && words[3]==2);
    bool temporary_release=false,descriptor=false;
    for(const auto& row:f.logs){
        if(row[0]==8 && row[1]==0x71001500)temporary_release=true;
        if(row[0]==0x18){descriptor=true;require(row[4]==6 && row[5]==2 && row[6]==20 && row[7]==16 && row[10]==1);}
    }
    require(temporary_release && descriptor);
    f.logs.clear();f.config[2]=4;
    input_mouse_cleanup(state,f.platform());
    require(f.logs.size()==3 && f.logs[0][0]==0x20 && f.logs[0][1]==0x71001200);
    require(f.logs[1][0]==8 && f.logs[1][1]==0x71001300 && f.logs[2][1]==0x71001100);
    require(words[11]==0 && words[12]==0 && words[13]==1 && words[14]==1);
    words.fill(0);Fixture failure;failure.config[1]=3;
    require(input_mouse_lifetime(state,failure.platform(),0x71001400)==1 && words[11]==0 && words[12]==0);
    words.fill(0);Fixture conversion;conversion.config[1]=6;conversion.config[2]=32;
    require(input_mouse_lifetime(state,conversion.platform(),0x71001400)==0 && words[14]==1);
    for(const auto& row:conversion.logs)require(row[0]!=0x6efaf0 || (row[5]!=3 && row[5]!=4));
}
