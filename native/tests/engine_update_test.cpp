#include "mco/engine_update.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace {
mco::EngineUpdateState base() {
 mco::EngineUpdateState s;
 s.rpm_state={600,7000,.3f,.4f,2400,true,.7f,100.f,314.15928f,3000,6800,2,175.5f,20.f,0.f};
 s.engine_flags=1;s.vehicle_flags=6;s.activation_delays.fill(32);s.current_counter=1000;
 for(int i=0;i<22;++i)s.torque_curve.push_back(100.f+i*13.5f);
 return s;
}
}
int main() {
 auto no_effect=[](const mco::EngineCall &,mco::EngineUpdateState &){return 0;};
 { auto s=base();s.override_value=1;auto o=mco::update_engine(s,no_effect);
   assert(o.state.rpm_state.rpm==5950);assert(o.calls.size()==1 && o.calls[0].stage=="curve_lookup");
   assert(o.state.effective_torque==100);assert(o.state.power>0);assert(s.rpm_state.rpm==3000); }
 { auto s=base();s.engine_flags=0;s.vehicle_flags=4;
   auto o=mco::update_engine(s,[](const mco::EngineCall &c,mco::EngineUpdateState &){return c.stage=="interface_query"?1:1224;});
   assert(o.state.engine_flags==1);assert(o.calls.size()==11);assert(o.calls[2]==mco::EngineCall({"enable_signal",1}));
   assert(o.calls[3].stage=="engine_setup" && o.calls.back().stage=="engine_finalize"); }
 { auto s=base();s.engine_flags=0;s.vehicle_flags=4;
   auto o=mco::update_engine(s,[](const mco::EngineCall &c,mco::EngineUpdateState &){return c.stage=="interface_query"?1:1225;});
   assert(o.state.engine_flags==0 && o.calls.size()==2); }
 { auto s=base();s.vehicle_flags=6;
   auto o=mco::update_engine(s,[](const mco::EngineCall &c,mco::EngineUpdateState &state){
     if(c.stage=="torque_update"){state.vehicle_flags=3;state.rpm_state.rpm=501;state.effective_torque=-13;}
     if(c.stage=="gear_link")state.engagement=.123456789f;
     return 0;
   });
   assert(o.state.rpm_state.rpm==501);assert(o.state.effective_torque==100);
   assert(o.calls.size()==4 && o.calls[2].stage=="gear_link" && o.calls[3].stage=="drivetrain_loads");
   assert(o.state.engagement==.123456789f); }
 { auto s=base();s.engine_flags=0;s.vehicle_flags=3;s.current_counter=10;
   auto o=mco::update_engine(s,[](const mco::EngineCall &c,mco::EngineUpdateState &state){
     if(c.stage=="interface_query")return c.argument==8?1:0;
     if(c.stage=="activation_counter")return 1000;
     if(c.stage=="start_counter")return 11;
     if(c.stage=="start_acceleration"){state.engine_flags=1;state.rpm_state.acceleration_input=800;}
     return 0;
   });
   assert(o.state.rpm_state.acceleration_input==0);assert(o.state.rpm_state.rpm>=600);
   assert(o.calls[5].stage=="rpm_update"); }
 { assert(mco::signed_engine_counter(0x80000000LL)==(-2147483647-1));
   assert(mco::signed_engine_counter(-2147483649LL)==2147483647);
   auto s=base();double a=mco::curve_torque_at_rpm(s.torque_curve,499),b=mco::curve_torque_at_rpm(s.torque_curve,500);
   assert(a<b && std::abs(b-113.5)<.00001);
   s.torque_curve.assign(22,-100.f);auto o=mco::update_engine(s,no_effect);assert(o.state.power==0); }
 { bool caught=false;try{mco::update_engine(base(),{});}catch(const std::invalid_argument &){caught=true;}assert(caught);
   caught=false;try{mco::curve_torque_at_rpm({1,2},500);}catch(const std::invalid_argument &){caught=true;}assert(caught); }
 { auto s=base();s.motion_metric=std::numeric_limits<float>::infinity();bool caught=false;
   try{mco::update_engine(s,no_effect);}catch(const std::invalid_argument &){caught=true;}assert(caught); }
}
