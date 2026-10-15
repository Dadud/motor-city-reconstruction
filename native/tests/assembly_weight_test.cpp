#include "mco/assembly_weight.hpp"
#include <stdexcept>
int main() {
    mco::AssemblyWeightInputs in{1000,.5,2.5,0,{},{}};
    if(mco::assembled_front_weight_fraction(in)!=.5) throw std::runtime_error("balanced body");
    in.front_masses[4]=250;
    if(mco::assembled_front_weight_fraction(in)!=2./3.) throw std::runtime_error("paired front mass");
    in.rear_masses[1]=250;
    if(mco::assembled_front_weight_fraction(in)!=.5) throw std::runtime_error("paired rear mass");
    in.body_mass=0;in.front_masses={};in.rear_masses={};
    bool rejected=false;
    try {mco::assembled_front_weight_fraction(in);}
    catch(const std::invalid_argument&) {rejected=true;}
    if(!rejected) throw std::runtime_error("zero combined moment accepted");
}
