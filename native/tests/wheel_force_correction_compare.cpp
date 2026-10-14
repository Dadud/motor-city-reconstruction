#include "mco/wheel_force_correction.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main() {
    std::cout<<std::setprecision(9);
    std::size_t count=0;
    while(true) {
        double service,other;
        int parking,direction,override;
        if(!(std::cin>>service)) return std::cin.eof()?0:2;
        if(++count>100000 || !(std::cin>>other>>parking>>direction>>override)
            || parking<0 || parking>1 || direction<0 || direction>255 || override<0 || override>1) return 2;
        std::array<mco::ForceCorrectionWheel,4> wheels{};
        for(auto& w:wheels) {
            int contact,enabled;
            if(!(std::cin>>w.projected_speed>>w.spin_value>>w.spin_adjustment>>w.spin_scale
                >>w.lateral_force>>w.longitudinal_force>>w.normal_load>>w.primary_coefficient
                >>w.secondary_coefficient>>contact>>enabled) || contact<0 || contact>1 || enabled<0 || enabled>1) return 2;
            w.contact=contact!=0; w.correction_enabled=enabled!=0;
        }
        try {
            auto result=mco::correct_wheel_forces(wheels,service,other,parking!=0,
                static_cast<std::uint8_t>(direction),override!=0);
            for(const auto& w:result) std::cout<<w.spin_value<<' '<<w.spin_adjustment<<' ';
            std::cout<<'\n';
        } catch(const std::invalid_argument&) { return 3; }
    }
}
