#include "mco/gear_binding.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>
namespace mco {
namespace {
double stored(double v) {
    if(!std::isfinite(v) || std::abs(v)>std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 gear observation required");
    return static_cast<float>(v);
}
}
GearBinding bind_gear_tables(std::int32_t rpm,double width,double aspect,double rim,
    std::span<const double> ratios,std::span<const double> losses,double final) {
    if(ratios.size()!=losses.size() || ratios.size()>8)
        throw std::invalid_argument("matching gear tables of at most eight entries required");
    width=stored(width);aspect=stored(aspect);rim=stored(rim);final=stored(final);
    std::vector<double> r(ratios.begin(),ratios.end()),l(losses.begin(),losses.end());
    for(auto& value:r) value=stored(value);
    for(auto& value:l) value=stored(value);
    const double circumference=stored(((width*stored(.001))*(aspect*stored(.01))*2.+
        rim*stored(.0254))*stored(3.1415927));
    const double revolutions=stored(rpm*stored(1./60.));
    GearBinding out;
    for(std::size_t i=0;i<r.size();++i) {
        const double denominator=final*r[i];
        const double speed=denominator==0 ? 0 : stored(revolutions/denominator*circumference);
        out.rpm_per_speed[i]=std::abs(speed)>0 ? stored(rpm/speed) : 0;
    }
    out.rpm_per_speed[1]=0;
    const auto wide=static_cast<std::int64_t>(rpm)-250;
    const auto shifted=wide<std::numeric_limits<std::int32_t>::min() ? wide+0x100000000LL : wide;
    for(std::size_t i=0;i<r.size();++i) {
        out.speed_per_rpm[i]=out.rpm_per_speed[i]!=0 ? stored(1./out.rpm_per_speed[i]) : stored(.01);
        out.loss_final_ratio[i]=stored(l[i]*final*r[i]);
        if(out.rpm_per_speed[i]!=0) {
            const double denominator=static_cast<double>(shifted)*out.speed_per_rpm[i];
            if(denominator==0) throw std::invalid_argument("nonzero near-limit speed denominator required");
            out.inverse_near_limit_speed[i]=stored(1./denominator);
        }
        out.wheel_inertia_factors[i]=stored(r[i]*stored(.0014241834));
    }
    out.wheel_inertia_factors[1]=0;
    out.final_drive_inertia=stored(final*stored(.0154740065));
    return out;
}
}
