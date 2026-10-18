#pragma once
#include "mco/startup_thread_runtime.hpp"
#include "cell_io.hpp"
#include <vector>
struct Boundary{std::uint32_t profile,process_calls=0;std::vector<std::uint32_t> logs;};
static std::uint32_t invoke(mco::StartupThreadRuntime& s,std::uint32_t id,std::span<const std::uint32_t> args,void* user){
 auto& b=*static_cast<Boundary*>(user);b.logs.push_back(id);b.logs.push_back(static_cast<std::uint32_t>(args.size()));for(auto x:args)b.logs.push_back(x);for(auto x:s.words)b.logs.push_back(x);
 switch(id){case 1:return b.profile&1?0:0x71002000;case 2:return b.profile&2?8192:4096;case 3:return b.profile&4?0:0x71003000;case 4:if(b.profile&8){s.allocation()=0x71004000;s.capacity()=0xcafe;}return 0;case 5:return 0x1234;case 6:return 0xa000+(++b.process_calls);case 7:return 0xb000;case 8:if(!(b.profile&16))s.handle()=0xc000;if(b.profile&32)s.cleanup_registered()=1;return b.profile&16?0:1;default:throw std::invalid_argument("bridge id");}
}

namespace startup_thread_runtime_cases {
inline void compare(std::istream& in){using namespace cell_io;auto mode=read(in),count=read(in);Boundary boundary{read(in),0,{}};mco::StartupThreadRuntime s;for(auto& w:s.words)w=read(in);std::array<std::uint32_t,64> slots;for(auto& x:slots)x=read(in);mco::CleanupRegistry registry{slots};mco::StartupThreadPlatform p{invoke,&boundary};std::uint32_t bytes=count;
 auto step=[&](std::uint32_t which,std::uint32_t n){if(which==0){mco::startup_thread_initialize(s,registry,p,n);emit(0);}else if(which==1)emit(mco::startup_thread_capacity(s,p,n));else if(which==2)emit(mco::startup_thread_allocate(s,p,bytes));else throw std::invalid_argument("mode");};
 if(mode==3){step(0,count);step(1,count);step(0,count+1);step(1,count+1);}else step(mode,count);
 emit(bytes);emit(s.words);emit(slots);emit(static_cast<std::uint32_t>(boundary.logs.size()));for(auto x:boundary.logs)emit(x);
 }
}
