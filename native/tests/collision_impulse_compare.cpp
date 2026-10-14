#include "mco/collision_impulse.hpp"
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
int main() {
    std::cout<<std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count=0;
    while (true) {
        char mode;
        if (!(std::cin>>mode)) return std::cin.eof()?0:2;
        if (++count>100000) return 2;
        std::array<double,3> p{},l{},r{};
        try {
            if (mode=='I') {
                mco::CollisionInertia b{};
                if (!(std::cin>>b.inverse_mass)) return 2;
                for(auto& v:b.inverse_inertia) if(!(std::cin>>v)) return 2;
                for(auto& v:b.world_to_body) if(!(std::cin>>v)) return 2;
                for(auto& v:b.body_to_world) if(!(std::cin>>v)) return 2;
                for(auto* a:{&p,&l,&r}) for(auto& v:*a) if(!(std::cin>>v)) return 2;
                const auto output=mco::impulse_motion(b,p,l,r);
                for(auto v:output.linear) std::cout<<v<<' ';
                for(auto v:output.angular) std::cout<<v<<' ';
                std::cout<<'\n';
            } else if(mode=='H') {
                for(auto* a:{&p,&l,&r}) for(auto& v:*a) if(!(std::cin>>v)) return 2;
                std::cout<<mco::plane_height(p,l,r)<<'\n';
            } else return 2;
        } catch (const std::invalid_argument&) {return 3;}
    }
}
