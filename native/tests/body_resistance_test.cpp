#include "mco/body_resistance.hpp"
#undef NDEBUG
#include <cassert>
int main() {
    mco::BodyResistanceState s{};
    s.front_lever=1;s.rear_lever=1;s.wind_lateral=2;s.density=1;s.area_parameter=1;
    s.resistance_disabled=true;s.load_transfer_disabled=true;
    const auto out=mco::calculate_body_resistance(s);
    assert(out.longitudinal_drag==0 && out.pitch_contribution==0 && out.yaw_contribution==20);
}
