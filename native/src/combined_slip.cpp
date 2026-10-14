#include "mco/combined_slip.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
double stored(double v) {
    if(!std::isfinite(v) || std::abs(v)>std::numeric_limits<float>::max()) throw std::invalid_argument("finite float32 slip value required");
    return static_cast<float>(v);
}
}
double longitudinal_slip_factor(double input) {
    const double s=stored(input);
    if(s>=0) {
        if(s<=stored(.15)) return 1;
        if(s<1) return stored((1-s)*stored(.4117647)+stored(.65));
        if(s<=8) return stored(stored(.7071)-s*stored(.0571));
        return std::max(.0625,stored(2/s));
    }
    if(s>=stored(-.05)) return 1;
    if(s>=stored(-.2)) return stored(s*stored(-4.375));
    if(s>-1) return stored(stored(.875)-std::abs(stored(s*stored(.375))));
    return std::max(.125,std::abs(stored(.5/s)));
}
CombinedSlipOutput limit_combined_slip(CombinedSlipState s) {
    const double speed=stored(s.speed),front=stored(s.front_quality),rear=stored(s.rear_quality);
    for(auto& w:s.wheels) {
        for(double* v:{&w.slip_ratio,&w.lateral_force,&w.longitudinal_force,&w.secondary_response,
            &w.normal_load,&w.primary_coefficient,&w.secondary_coefficient,&w.spin_value,&w.spin_scale,&w.projected_speed}) *v=stored(*v);
        if(w.spin_scale<=0 || w.normal_load<0 || w.primary_coefficient<0 || w.secondary_coefficient<0)
            throw std::invalid_argument("positive scale and nonnegative capacities required");
    }
    if(!s.parking_control) {
        auto& left=s.wheels[3];auto& right=s.wheels[2];
        const double lc=stored(left.normal_load*left.primary_coefficient),rc=stored(right.normal_load*right.primary_coefficient);
        if(left.longitudinal_force>lc && right.longitudinal_force<rc) {
            const double delta=std::min(stored(left.longitudinal_force-lc),stored(rc-right.longitudinal_force));
            left.longitudinal_force=stored(left.longitudinal_force-delta);right.longitudinal_force=stored(right.longitudinal_force+delta);
        } else if(right.longitudinal_force>rc && left.longitudinal_force<lc) {
            const double delta=std::min(stored(right.longitudinal_force-rc),stored(lc-left.longitudinal_force));
            left.longitudinal_force=stored(left.longitudinal_force+delta);right.longitudinal_force=stored(right.longitudinal_force-delta);
        }
    }
    CombinedSlipOutput out{};
    auto observe_loss=[&](int i,double input) {
        const auto& w=s.wheels[i];const double loss=stored(input);
        if(loss==0 || w.normal_load==0 || w.primary_coefficient==0 || !w.contact) return;
        if(w.component_code!=6 && w.component_code!=20 && s.vehicle_code==0 && w.wear_mode==1)
            out.effects.push_back({0,i,stored(5.2083333e-6),0,1,.25});
        const double amount=std::clamp(stored(loss*w.primary_coefficient),0.0,w.primary_coefficient);
        if(amount>0 && w.slip_ratio>0 && speed>0) {
            const double mismatch=std::min(stored(13.4109),std::abs(stored(w.spin_value-w.projected_speed/w.spin_scale)));
            out.effects.push_back({0,i,amount,stored(.15),stored(.000052083335),.25});
            out.effects.push_back({1,i,stored(mismatch*.03125)});
        }
    };
    for(int i=0;i<4;++i) {
        auto& w=s.wheels[i];const double factor=speed>1 ? longitudinal_slip_factor(w.slip_ratio) : 1;
        observe_loss(i,stored(1-factor));
        double longitudinal=stored(factor*w.longitudinal_force);
        if(w.slip_ratio<stored(-.05)) longitudinal=stored((1-(i<2 ? front : rear)*.5)*factor*w.longitudinal_force);
        const double magnitude=stored(std::sqrt(w.lateral_force*w.lateral_force+longitudinal*longitudinal));
        double capacity=stored(w.primary_coefficient*w.normal_load),secondary=stored(w.secondary_coefficient*w.normal_load);
        if(s.alternate_mode) {capacity=stored(capacity*factor);secondary=stored(secondary*factor);}
        if(capacity<magnitude && magnitude>0) {
            const double reduction=stored(std::sqrt(stored((secondary/magnitude)*stored(.99))));
            observe_loss(i,stored(1-reduction));
            w.lateral_force=stored(reduction*w.lateral_force);longitudinal=stored(reduction*longitudinal);
            w.secondary_response=stored((secondary/magnitude)*w.secondary_response);
        }
        w.longitudinal_force=longitudinal;
    }
    out.state=s;return out;
}
}
