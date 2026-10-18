#include "mco/diagnostic_runtime.hpp"
#include <stdexcept>
int main(){
 mco::DiagnosticRuntime state; mco::DiagnosticPlatform platform;
 // Absent device callback returns without requiring unresolved environment services.
 mco::diagnostic_device_configure(state,platform,1,1);
 if(state.initialized)return 1;
 for(auto& word:state.words)word=0xfffffffe;
 mco::diagnostic_channel_bits(state,1,0xffffffff);
 if(state.words[1]!=0xffffffff||state.words[3]!=0xffffffff)return 2;
 mco::diagnostic_device_bits(state,0,2);
 if(state.words[136]!=0xfffffffe)return 3;
 bool channel=false,device=false;
 try{mco::diagnostic_channel_bits(state,64,1);}catch(const std::out_of_range&){channel=true;}
 try{mco::diagnostic_device_bits(state,8,1);}catch(const std::out_of_range&){device=true;}
 return channel&&device?0:4;
}
