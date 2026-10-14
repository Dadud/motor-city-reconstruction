#include "mco/drivetrain_coupling.hpp"
#include <stdexcept>
namespace { void check(bool condition) { if (!condition) throw std::runtime_error("drivetrain coupling check failed"); } }
int main() {
    mco::DrivetrainCoupling s{3000,250,200,2,30,2,.5f,12,0,false,false,0};
    s.gear_index=1; s.engagement=1;
    auto out=mco::couple_drivetrain(s);
    check(out.acceleration_input==out.corrected_torque);
    s.gear_index=2;
    out=mco::couple_drivetrain(s);
    check(out.acceleration_input==-12);
    s.effective_torque=-200;
    out=mco::couple_drivetrain(s);
    check(out.acceleration_input<out.corrected_torque);
    check(mco::environment_correction(0,false,false,1)==mco::environment_correction(0,false,false,2));
    check(mco::environment_correction(0,false,true,2)>mco::environment_correction(0,false,true,1));
}
