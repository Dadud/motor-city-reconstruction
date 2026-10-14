#include "mco/combined_slip.hpp"
#include <stdexcept>
void check(bool ok){if(!ok) throw std::runtime_error("combined slip mismatch");}
int main() {
    check(mco::longitudinal_slip_factor(-.05)==1);
    check(mco::longitudinal_slip_factor(-.05000001)<.25);
    check(mco::longitudinal_slip_factor(100)==.0625);
    mco::CombinedSlipState s{};s.speed=20;
    for(auto& w:s.wheels) w={0,0,0,10,100,1,.5,1,.3,20,true,6,1};
    s.wheels[2].longitudinal_force=50;s.wheels[3].longitudinal_force=200;
    check(mco::limit_combined_slip(s).state.wheels[2].longitudinal_force==100);
    s.parking_control=true;
    check(mco::limit_combined_slip(s).state.wheels[2].longitudinal_force==50);
}
