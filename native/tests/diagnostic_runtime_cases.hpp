#pragma once
#include "mco/diagnostic_runtime.hpp"
#include "cell_io.hpp"
#include <vector>
namespace diagnostic_runtime_cases {
struct Boundary {std::uint32_t script;std::vector<std::uint32_t> logs;};
static std::uint32_t env(mco::DiagnosticRuntime&,bool channel,void* user){auto& b=*static_cast<Boundary*>(user);b.logs.push_back(channel?1:2);return b.script?0x71001000:0;}
static void config(mco::DiagnosticRuntime& s,bool channel,std::uint32_t id,void* user){auto& b=*static_cast<Boundary*>(user);b.logs.push_back(channel?3:4);b.logs.push_back(id);s.words[channel?1:136]^=0xabcde123;}
inline void compare(std::istream& in){using namespace cell_io;auto mode=read(in),a=read(in),b=read(in);Boundary boundary{read(in),{}};mco::DiagnosticRuntime s;s.initialized=read(in);for(auto& w:s.words)w=read(in);mco::DiagnosticPlatform p{env,config,&boundary};switch(mode){case 0:mco::diagnostic_initialize(s,p);break;case 1:mco::diagnostic_channel_bits(s,a,b);break;case 2:mco::diagnostic_device_bits(s,a,b);break;case 3:mco::diagnostic_channel_configure(s,p,a,b);break;case 4:mco::diagnostic_device_configure(s,p,a,b);break;default:throw std::invalid_argument("mode");}emit(s.initialized);emit(s.words);emit(static_cast<std::uint32_t>(boundary.logs.size()));for(auto x:boundary.logs)emit(x);}
}
