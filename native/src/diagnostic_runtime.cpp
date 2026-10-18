#include "mco/diagnostic_runtime.hpp"
#include <stdexcept>
namespace mco {
namespace {
std::uint32_t& at(DiagnosticRuntime& s,std::uint32_t address){ return s.words.at((address-0x8c4730)/4); }
void bit(std::uint32_t& word,std::uint32_t enabled){word=(word&~1u)|(enabled&1u);}
void environment(DiagnosticRuntime& s,const DiagnosticPlatform& p,bool channel){
 if(!p.environment)throw std::invalid_argument("diagnostic environment boundary required");
 const auto value=p.environment(s,channel,p.user);
 if(value){if(!p.configure)throw std::invalid_argument("diagnostic parser boundary required");p.configure(s,channel,value,p.user);}
}
}
void diagnostic_channel_bits(DiagnosticRuntime& s,std::uint32_t selector,std::uint32_t enabled){
 if(selector==0||selector==1){for(std::uint32_t a=0x8c4734;a<0x8c4934;a+=8){auto& w=at(s,a);if(selector==0||(w&2))bit(w,enabled!=0);}}
 else {if(selector>=64)throw std::out_of_range("diagnostic channel selector");bit(at(s,0x8c4734+selector*8),enabled!=0);}
}
void diagnostic_device_bits(DiagnosticRuntime& s,std::uint32_t selector,std::uint32_t enabled){
 if(selector>=8)throw std::out_of_range("diagnostic device selector");
 bit(at(s,0x8c4950+selector*12),enabled);
}
void diagnostic_channel_configure(DiagnosticRuntime& s,const DiagnosticPlatform& p,std::uint32_t selector,std::uint32_t enabled){
 if(!s.initialized)diagnostic_initialize(s,p);
 diagnostic_channel_bits(s,selector,enabled);environment(s,p,true);
}
void diagnostic_device_configure(DiagnosticRuntime& s,const DiagnosticPlatform& p,std::uint32_t selector,std::uint32_t enabled){
 if(selector>=8)throw std::out_of_range("diagnostic device selector");
 if(at(s,0x8c494c+selector*12)){if(!s.initialized)diagnostic_initialize(s,p);diagnostic_device_bits(s,selector,enabled);environment(s,p,false);}
}
void diagnostic_initialize(DiagnosticRuntime& s,const DiagnosticPlatform& p){
 if(s.initialized)return;
 s.initialized=1;
 for(std::uint32_t a=0x8c4950;a<0x8c49b0;a+=12)at(s,a)&=~1u;
 for(std::uint32_t a=0x8c4734;a<0x8c4934;a+=8)at(s,a)&=~1u;
 for(std::uint32_t a=0x8c497c;a<0x8c49ac;a+=12){at(s,a-4)=0;at(s,a)=0;}
 for(std::uint32_t a=0x8c47b4;a<0x8c4934;a+=8){at(s,a-4)=0;at(s,a)&=~2u;}
 diagnostic_channel_configure(s,p,2,1);diagnostic_device_configure(s,p,1,1);
}
}
