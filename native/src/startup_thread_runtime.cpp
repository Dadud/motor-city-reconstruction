#include "mco/startup_thread_runtime.hpp"
#include <bit>
#include <initializer_list>
#include <stdexcept>
namespace mco {
namespace {
std::uint32_t call(StartupThreadRuntime& s,const StartupThreadPlatform& p,std::uint32_t id,std::initializer_list<std::uint32_t> args={}){
 if(!p.invoke)throw std::invalid_argument("thread runtime platform boundary required");
 return p.invoke(s,id,{args.begin(),args.size()},p.user);
}
}
std::uint32_t startup_thread_allocate(StartupThreadRuntime& s,const StartupThreadPlatform& p,std::uint32_t& bytes){
 if(!s.page_size())s.page_size()=call(s,p,2);
 const auto divisor=std::bit_cast<std::int32_t>(s.page_size());
 if(divisor<=0)throw std::invalid_argument("thread runtime requires positive page size");
 const auto numerator=std::bit_cast<std::int32_t>(bytes-1u+s.page_size());
 bytes=static_cast<std::uint32_t>(static_cast<std::int64_t>(numerator)/divisor)*s.page_size();
 return call(s,p,3,{0,bytes,0x3000,4});
}
std::uint32_t startup_thread_capacity(StartupThreadRuntime& s,const StartupThreadPlatform& p,std::uint32_t count){
 if(!s.lock())s.lock()=call(s,p,1);
 auto result=s.allocation();
 if(!result){
  std::uint32_t bytes=count*12u;
  s.allocation()=startup_thread_allocate(s,p,bytes);
  result=0;
  if(s.allocation()){
   call(s,p,4,{s.allocation(),0,bytes});
   result=bytes*0xaaaaaaabu;
   s.capacity()=bytes/12u;
  }
 }
 return result;
}
void startup_thread_initialize(StartupThreadRuntime& s,CleanupRegistry& registry,const StartupThreadPlatform& p,std::uint32_t count){
 if(s.initialized())return;
 s.initialized()=1;
 startup_thread_capacity(s,p,count?count:100);
 s.thread_id()=call(s,p,5);
 const auto target=call(s,p,6);
 const auto source=call(s,p,7);
 const auto process=call(s,p,6);
 call(s,p,8,{process,source,target,0xb2bbc4,0,0,2});
 if(!s.cleanup_registered()){
  s.cleanup_registered()=1;
  cleanup_registry_register(registry,0x6be3b0);
 }
}
}
