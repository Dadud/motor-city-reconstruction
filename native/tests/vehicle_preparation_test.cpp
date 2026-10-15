#include "mco/vehicle_preparation.hpp"
#include <cmath>
#include <stdexcept>
void check(bool ok) {if(!ok)throw std::runtime_error("preparation behavior mismatch");}
int main() {
    mco::PreparationState s;
    s.support_count=2;s.pitch=.03;s.roll=-.02;s.extent=.05;s.auxiliary.fill(4);
    auto out=mco::prepare_vehicle(s);
    check(std::abs(out.pitch-.03)<1e-7 && out.auxiliary[0]==4 && out.angle_delta[0]==0);
    for(int i=0;i<3;++i)for(int j=0;j<3;++j)check(out.to_local[i*3+j]==out.to_world[j*3+i]);
    s.front_factor=2;s.local_vertical_acceleration=-1;check(mco::prepare_vehicle(s).damping==0);
    s.local_vertical_acceleration=1;s.rear_factor=.25;check(mco::prepare_vehicle(s).damping==.75);
    s.support_count=0;check(mco::prepare_vehicle(s).auxiliary[0]==0);
    mco::SupportState support{};support.phase=.25;support.local_longitudinal_speed=0;support.noise.fill(0);
    for(auto& w:support.wheels)w={true,4,.5,1,.9,3};
    auto corrected=mco::update_support_disturbance(support);
    check(corrected.wheels[0].correction==0 && std::abs(corrected.wheels[0].displacement)<=.5);
    support.wheels[0].contact=false;corrected=mco::update_support_disturbance(support);
    check(corrected.wheels[0].correction==0 && corrected.wheels[0].displacement==0);
    mco::PreparationState precision;
    precision.pitch=-.0020816968753933907;precision.minimum_pitch=.06;
    precision.pitch_reference=.1;precision.roll_reference=-1;
    precision.source_matrix={.8,.1,0,-.1,1,.3,0,-1,.9};
    auto retained=mco::prepare_vehicle(precision);
    check(retained.pitch==-.0029866702388972044);
    check(retained.pitch!=static_cast<float>(static_cast<double>(static_cast<float>(precision.pitch))+retained.angle_delta[0]));
    s.support_count=5;bool rejected=false;
    try {mco::prepare_vehicle(s);}catch(const std::invalid_argument&) {rejected=true;}check(rejected);
}
