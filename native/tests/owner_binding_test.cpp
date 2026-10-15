#include "mco/owner_binding.hpp"
#include <stdexcept>
void check(bool value) {if(!value) throw std::runtime_error("owner binding regression");}
int main() {
    check(mco::body_inertia_scales(99,{2,3,4})==std::array<float,3>{2,3,4});
    check(mco::body_inertia_scales(0)==mco::body_inertia_scales(2));
    auto inertia=mco::bind_owner_inertia(0,{1,1,1},0);check(inertia.mass==1000);
    auto levers=mco::bind_axle_levers(4,.25);check(levers.front==3 && levers.rear==1);
    auto com=mco::bind_startup_com(1.1f,1,2,.75f);check(com.longitudinal==1.25);
    bool rejected=false;try {mco::bind_finalized_owner({}, {1,1,1},false);} catch(const std::invalid_argument&) {rejected=true;}
    check(rejected);
}
