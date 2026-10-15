#include "mco/body_vertical_load.hpp"
#undef NDEBUG
#include <cassert>
int main() {
    mco::BodyVerticalLoadState s{0,0,1,2,.3,.4,0,0,0,0,{-100,0,200,1000}};
    auto out=mco::adjust_body_vertical_load(s);
    assert(out.total_vertical==0 && out.wheel_loads[0]==0 && out.wheel_loads[3]==1000);
    s.longitudinal_speed=2;s.front_parameter=-1;
    out=mco::adjust_body_vertical_load(s);
    assert(out.front_vertical<0 && out.rear_vertical>0 && out.wheel_loads[1]==0);
}
