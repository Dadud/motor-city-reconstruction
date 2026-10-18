#include "mco/input_mouse_state_set.hpp"
#include <initializer_list>
#include <stdexcept>
namespace mco {
namespace {
std::uint32_t call(InputMouseStateSet& s,const InputMouseStateSetPlatform& p,
    std::uint32_t code,std::uint32_t table=0,std::uint32_t id=0,
    std::initializer_list<std::uint32_t> args={}){
    if(!p.invoke)throw std::invalid_argument("mouse state bridge required");
    return p.invoke(s,code,table,id,{args.begin(),args.size()},p.user);
}
std::uint32_t table(InputMouseStateSet& s,const InputMouseStateSetPlatform& p){
    if(!p.resolve)throw std::invalid_argument("mouse state virtual-table resolver required");
    return p.resolve(s,s.lifetime.words[12],p.user);
}
void position(InputMouseStateSet& s,const InputMouseStateSetPlatform& p){
    call(s,p,0x6f07f0,0,0,{s.lifetime.words[4],s.lifetime.words[5]});
}
void diagnostic(InputMouseStateSet& s,const InputMouseStateSetPlatform& p,
                std::uint32_t line,std::uint32_t message){
    s.diagnostic_file=0x84a004;s.diagnostic_line=line;
    call(s,p,s.diagnostic_callback,0,0,{message});
}
}
bool input_mouse_state_set(InputMouseStateSet& s,const InputMouseStateSetPlatform& p,
                           std::uint32_t selector,std::uint32_t value){
    auto& w=s.lifetime.words;
    switch(selector){
    case 3:w[4]=value;if(s.access_mode==4)position(s,p);return true;
    case 4:w[5]=value;if(s.access_mode==4)position(s,p);return true;
    case 5:w[6]=value;return true;
    case 8:s.state8=value;return true;
    case 9:s.state9=value;return true;
    case 7:break;
    default:diagnostic(s,p,0x185,0x849fe8);return false;
    }
    bool success=true;
    if(s.access_mode!=value){
        if(w[11]==0){diagnostic(s,p,0x155,0x84a010);s.access_mode=value;return true;}
        if(value==4 && s.access_mode!=4){
            const auto captured=table(s,p);call(s,p,0x20,captured,w[12]);
            position(s,p);s.access_mode=value;return true;
        }
        const auto captured=table(s,p);const std::uint32_t flags=value==5?5:6;
        const auto window=call(s,p,0x584cf0);
        success=call(s,p,0x34,captured,w[12],{window,flags})==0;
        if(!success){
            const auto current=table(s,p);const auto status=call(s,p,0x20,current,w[12]);
            if(status==0 || status==1){
                const auto retry=table(s,p);const auto next_window=call(s,p,0x584cf0);
                success=call(s,p,0x34,retry,w[12],{next_window,flags})==0;
                const auto acquired=table(s,p);call(s,p,0x1c,acquired,w[12]);
            }
        }
    }
    s.access_mode=value;return success;
}
}
