#include "mco/drafting.hpp"
#undef NDEBUG
#include <cassert>
#include <stdexcept>

int main() {
    mco::DraftVehicle own{1,{0.,0.,0.},{1.,0.,0.,0.,1.,0.,0.,0.,1.},{1.,.8,2.}};
    const auto none=mco::calculate_drafting(1,{own});
    assert(none.factor==1. && !none.selected_vehicle && !none.inside_wake);
    auto other=own;other.identifier=2;other.position[1]=20.;
    auto later=other;later.identifier=3;
    const auto out=mco::calculate_drafting(1,{own,other,later});
    assert(out.selected_vehicle==2 && !out.inside_wake && out.factor==1.25);
    assert(out.vehicles[1].wake_origin!=other.wake_origin);
    assert(out.vehicles[2].wake_origin==later.wake_origin);
    const auto reversed=mco::calculate_drafting(1,{later,other,own});
    assert(reversed.selected_vehicle==3);
    bool rejected=false;
    try { mco::calculate_drafting(1,{own,own}); } catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
    rejected=false;
    try { mco::calculate_drafting(42,{own}); } catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
}
