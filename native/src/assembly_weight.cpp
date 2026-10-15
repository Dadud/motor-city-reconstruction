#include "mco/assembly_weight.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
double observed(double v) {
    if(!std::isfinite(v) || std::abs(v)>std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 weight inputs required");
    return static_cast<float>(v);
}
}
double assembled_front_weight_fraction(const AssemblyWeightInputs& inputs) {
    auto in=inputs;
    in.body_mass=observed(in.body_mass);in.body_fraction=observed(in.body_fraction);
    in.wheelbase=observed(in.wheelbase);in.shared_mass=observed(in.shared_mass);
    for(auto& v:in.front_masses) v=observed(v);
    for(auto& v:in.rear_masses) v=observed(v);
    if(in.wheelbase<=0 || in.body_fraction<0 || in.body_fraction>1 ||
        in.body_mass<0 || in.shared_mass<0)
        throw std::invalid_argument("physical weight distribution domain required");
    const double half=static_cast<float>(in.body_mass*.5);
    double front=in.shared_mass*.25+half;
    for(std::size_t i=0;i<in.front_masses.size();++i) {
        const double mass=in.front_masses[i];
        if(mass<0) throw std::invalid_argument("nonnegative component masses required");
        front+=i>=4 && i<9 ? mass+mass : mass;
    }
    const double front_moment=front*(in.body_fraction*in.wheelbase);
    double rear=in.shared_mass*.75+half;
    for(std::size_t i=0;i<in.rear_masses.size();++i) {
        const double mass=in.rear_masses[i];
        if(mass<0) throw std::invalid_argument("nonnegative component masses required");
        rear+=i>=1 && i<6 ? mass+mass : mass;
    }
    const double rear_moment=((1.-in.body_fraction)*in.wheelbase)*rear;
    const double denominator=rear_moment+front_moment;
    if(denominator==0) throw std::invalid_argument("nonzero combined mass moment required");
    return front_moment/denominator;
}
}
