#include "mco/gear_binding.hpp"
#include <stdexcept>
int main() {
    const double ratios[]{2.5,0,2.2,1.7},losses[]{.8,1,.7,.9};
    const auto result=mco::bind_gear_tables(7000,205,75,15,ratios,losses,3.5);
    if(result.rpm_per_speed[1]!=0 || result.wheel_inertia_factors[1]!=0 ||
        result.rpm_per_speed[2]<=result.rpm_per_speed[3] || result.speed_per_rpm[4]!=0)
        throw std::runtime_error("gear ordering, neutral or unused table failed");
    const auto stopped=mco::bind_gear_tables(0,205,75,15,ratios,losses,3.5);
    if(stopped.rpm_per_speed[0]!=0) throw std::runtime_error("zero RPM branch failed");
    bool rejected=false;
    try {mco::bind_gear_tables(250,205,75,15,ratios,losses,3.5);}
    catch(const std::invalid_argument&) {rejected=true;}
    if(!rejected) throw std::runtime_error("zero near-limit denominator accepted");
}
