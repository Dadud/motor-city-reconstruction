#include "mco/startup_thread_runtime.hpp"
#include <stdexcept>
int main(){mco::StartupThreadRuntime s;std::array<std::uint32_t,64> slots{};mco::CleanupRegistry registry{slots};mco::StartupThreadPlatform p;
 s.initialized()=1;mco::startup_thread_initialize(s,registry,p,0);
 s.lock()=1;s.allocation()=0x1234;if(mco::startup_thread_capacity(s,p,0)!=0x1234)return 1;
 s.page_size()=0xffffffff;std::uint32_t bytes=12;bool rejected=false;
 try{mco::startup_thread_allocate(s,p,bytes);}catch(const std::invalid_argument&){rejected=true;}
 return rejected?0:2;
}
