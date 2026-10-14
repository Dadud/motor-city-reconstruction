#include "mco/wheel_force_correction.hpp"
#include <cassert>
#include <stdexcept>

int main() {
    mco::ForceCorrectionWheel wheel{10,20,3,.5,0,0,2000,1,.8,true,false};
    std::array<mco::ForceCorrectionWheel,4> wheels{wheel,wheel,wheel,wheel};
    auto result=mco::correct_wheel_forces(wheels,0,0,false,1,false);
    assert(result[0].spin_adjustment==0 && result[0].spin_value==20);
    for(auto& w:wheels) {w.contact=false;w.longitudinal_force=1;}
    result=mco::correct_wheel_forces(wheels,0,0,false,1,false);
    assert(result[0].spin_value==20 && result[0].spin_adjustment==3);
    for(auto& w:wheels) {w.contact=true;w.longitudinal_force=-1000;w.projected_speed=0;}
    result=mco::correct_wheel_forces(wheels,0,0,true,1,false);
    assert(result[2].spin_adjustment>result[0].spin_adjustment);
    wheels[0].spin_scale=0;
    try { mco::correct_wheel_forces(wheels,0,0,false,1,false); return 1; }
    catch(const std::invalid_argument&) {}
}
