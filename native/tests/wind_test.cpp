#include "mco/wind.hpp"
#undef NDEBUG
#include <cassert>
#include <cmath>
#include <limits>
#include <stdexcept>

int main() {
    mco::WindState s{0,0,{0.,1.,1.},{1.,0.,0.,0.,1.,0.,0.,0.,1.}};
    const auto base=mco::calculate_wind(s);
    assert(base.present && base.body_velocity[0]==0. && base.body_velocity[1]==0.);
    assert(base.body_velocity[2]==static_cast<float>(3.*static_cast<double>(static_cast<float>(.44703))));
    s.disabled=true;
    const auto off=mco::calculate_wind(s);
    assert((!off.present && off.body_velocity==std::array<double,3>{}));
    s.disabled=false;s.simulation_counter=1920;s.weather_seed=-361;
    const auto negative=mco::calculate_wind(s);
    s.weather_seed=-1;
    assert(mco::calculate_wind(s).body_velocity==negative.body_velocity);
    s.world_to_body={0.,0.,0.,0.,0.,0.,0.,0.,0.};
    const auto zero_transform=mco::calculate_wind(s);
    assert((zero_transform.present && zero_transform.body_velocity==std::array<double,3>{}));
    s.world_to_body[0]=std::numeric_limits<double>::infinity();
    bool rejected=false;
    try { mco::calculate_wind(s); } catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
}
