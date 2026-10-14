#include "mco/body_moments.hpp"
#include <iostream>
#include <iomanip>
int main() {
    std::cout<<std::setprecision(17);
    mco::BodyMomentState s{}; int alternate,contact;
    while (std::cin>>s.speed) {
        if (!(std::cin>>s.front_lever>>s.rear_lever>>s.front_track>>s.rear_track>>s.height_parameter
            >>s.mass_parameter>>s.inverse_pitch>>s.inverse_yaw>>s.inverse_roll>>s.pitch_multiplier
            >>s.front_vertical>>s.rear_vertical>>s.yaw_contribution>>alternate)) return 2;
        s.alternate_mode=alternate!=0;
        for (auto& w:s.wheels) {
            if (!(std::cin>>w.lateral_force>>w.longitudinal_force>>w.secondary_response>>w.support_correction>>contact)) return 2;
            w.contact=contact!=0;
        }
        const auto out=mco::accumulate_body_moments(s);
        std::cout<<out[0]<<' '<<out[1]<<' '<<out[2]<<'\n';
    }
}
