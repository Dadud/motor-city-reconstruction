#include "mco/drivetrain_links.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <stdexcept>
int main(){
 mco::DrivetrainLinksConfig c;mco::DrivetrainLinksState s;
 auto empty=[](const mco::LinkCall&,mco::DrivetrainLinksState&){};
 {auto in=s;in.gate_one=.8f;auto out=mco::update_gear_link(in,c,empty);assert(out.state.engagement==0);assert(out.calls.size()==1&&out.calls[0].code==4);}
 {auto in=s;in.engine_flags=0;in.request=.1f;auto out=mco::update_gear_link(in,c,empty);assert(out.state.engagement==0);assert(out.calls.size()==1&&out.calls[0].code==5);}
 {auto in=s;in.bypass=true;in.condition=1.1f;auto out=mco::update_drivetrain_loads(in,c,empty);assert(out.state.main_temperature==100&&out.state.auxiliary_temperature==125&&out.state.condition==.9f&&out.calls.empty());}
 {auto in=s;in.gate_two=1;in.engagement=0;auto out=mco::update_drivetrain_loads(in,c,empty);assert(out.state.auxiliary_temperature==150&&out.state.condition==1);assert(out.calls.size()==3&&out.calls[0].stage=="damage"&&out.calls[1].code==18&&out.calls[2].code==22);}
 {auto in=s;in.main_temperature=300;in.third_temperature=200;in.condition=1.1f;auto out=mco::update_drivetrain_loads(in,c,[](const mco::LinkCall&a,mco::DrivetrainLinksState&state){if(a.stage=="damage"&&a.code==15)state.third_temperature=150;});assert(out.state.third_temperature==150);assert(out.calls[0].code==15&&out.calls[1].code==24);assert(out.calls[1].values[0]>.03f&&out.calls[1].values[0]<.04f);}
 {auto in=s;in.main_temperature=89;auto out=mco::update_drivetrain_loads(in,c,empty);assert(out.state.loss==0);in.main_temperature=90;out=mco::update_drivetrain_loads(in,c,empty);assert(out.state.loss>0);}
 {bool caught=false;try{mco::update_gear_link(s,c,{});}catch(const std::invalid_argument&){caught=true;}assert(caught);
 c.material_index=-4;caught=false;try{mco::update_gear_link(s,c,empty);}catch(const std::invalid_argument&){caught=true;}assert(caught);}
}
