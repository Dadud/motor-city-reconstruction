#include "mco/collision_impulse.hpp"
#include <stdexcept>
namespace {void check(bool value) {if (!value) throw std::runtime_error("collision impulse check failed");}}
int main() {
    const std::array<double,9> identity{1,0,0,0,1,0,0,0,1};
    const mco::CollisionInertia body{0.5,{1,2,3},identity,identity};
    const auto central=mco::impulse_motion(body,{0,-2,0},{0,0,0},{0,1,0});
    check(central.linear==std::array<float,3>{0,-1,0} && central.angular==std::array<float,3>{0,0,0});
    const auto outward=mco::impulse_motion(body,{0,2,0},{1,0,0},{0,1,0});
    check(outward.linear==std::array<float,3>{0,0,0} && outward.angular[2]==6);
    check(mco::plane_height({1,2,3},{1,10,2},{3,-999,4})==6);
    bool rejected=false;
    try {mco::plane_height({1,0,0},{0,0,0},{0,0,0});} catch(const std::invalid_argument&) {rejected=true;}
    check(rejected);
}
