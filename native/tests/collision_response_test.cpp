#include "mco/collision_response.hpp"
#include <limits>
#include <stdexcept>
namespace { void check(bool value) { if (!value) throw std::runtime_error("collision response check failed"); } }
int main() {
    const std::array<double,3> n{0,1,0}, v{0,-1,0};
    check(mco::tangential_response({1,1,0},n,1,0.5).status == 0);
    check(mco::tangential_response({1,0,0},n,1,0.5).vector == std::array<float,3>{0,0,0});
    const auto bounded = mco::tangential_response(v,n,2,0.5);
    check(bounded.status == 1 && bounded.vector[1] == 2);
    const auto sliding = mco::tangential_response(v,n,1.9999998807907104,0.5);
    check(sliding.status == 2 && sliding.vector[1] == 0.5);
    check(mco::tangential_response(v,{0,2,0},4,0.5).vector[1] == 5);
    bool rejected=false;
    try { mco::tangential_response({std::numeric_limits<double>::infinity(),0,0},n,1,0.5); }
    catch (const std::invalid_argument&) { rejected=true; }
    check(rejected);
}
