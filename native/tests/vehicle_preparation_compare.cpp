#include "mco/vehicle_preparation.hpp"
#include <iostream>
#include <iomanip>
template<class T> bool read(T& values) {for(auto& x:values)if(!(std::cin>>x))return false;return true;}
template<class T> void write(const T& values) {for(const auto& x:values)std::cout<<x<<' ';}
int main() {
    std::cout<<std::setprecision(17);
    for(int n=0;n<100000;++n) {
        int mode;if(!(std::cin>>mode))return std::cin.eof()?0:2;
        if(mode==0) {
            mco::PreparationState s;
            for(double* p:{&s.local_vertical_acceleration,&s.front_observation,&s.rear_observation,&s.front_factor,&s.rear_factor})if(!(std::cin>>*p))return 2;
            if(!(std::cin>>s.support_count))return 2;
            for(double* p:{&s.pitch_extent,&s.roll_extent,&s.pitch_limit,&s.roll_limit,&s.orientation_scale,&s.pitch_reference,&s.roll_reference,
                &s.minimum_pitch,&s.maximum_pitch,&s.maximum_roll,&s.pitch_offset,&s.pitch,&s.roll,&s.extent})if(!(std::cin>>*p))return 2;
            if(!read(s.source_vector) || !read(s.source_matrix) || !read(s.motion_matrix))return 2;
            if(!(std::cin>>s.damping>>s.pitch_target>>s.roll_target) || !read(s.angle_delta) || !read(s.auxiliary) || !read(s.to_world) || !read(s.to_local))return 2;
            auto out=mco::prepare_vehicle(s);
            std::cout<<out.damping<<' '<<out.pitch_target<<' '<<out.roll_target<<' '<<out.pitch<<' '<<out.roll<<' '<<out.extent<<' ';
            write(out.angle_delta);write(out.auxiliary);write(out.to_world);write(out.to_local);
        } else if(mode==1) {
            mco::SupportState s{};
            for(auto& w:s.wheels) {int contact;if(!(std::cin>>contact>>w.bound_parameter>>w.amplitude>>w.frequency>>w.displacement>>w.correction))return 2;w.contact=contact!=0;}
            if(!(std::cin>>s.phase>>s.local_longitudinal_speed))return 2;
            for(auto& x:s.noise) {int byte;if(!(std::cin>>byte) || byte<0 || byte>255)return 2;x=static_cast<std::uint8_t>(byte);}
            for(auto& w:mco::update_support_disturbance(s).wheels)std::cout<<w.displacement<<' '<<w.correction<<' ';
        } else return 2;
        std::cout<<'\n';
    }
    return 2;
}
