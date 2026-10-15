#include "mco/model_bounds.hpp"
#include <cmath>
#include <stdexcept>
int main() {
    mco::FcePart part{};
    if(mco::transformed_part_bounds(part)) throw std::runtime_error("empty geometry returned bounds");
    part.origin={-0.f,-0.f,-0.f};part.vertices={{0.f,0.f,0.f},{-0.f,-0.f,-0.f}};
    auto result=mco::transformed_part_bounds(part);
    for(unsigned axis=0;axis<3;++axis)
        if(!std::signbit(result->minimum[axis]) || !std::signbit(result->maximum[axis]))
            throw std::runtime_error("original signed-zero tie changed");
    part.origin={10.f,20.f,30.f};part.vertices={{2.f,3.f,4.f},{-5.f,-6.f,-7.f}};
    result=mco::transformed_part_bounds(part,true);
    if(result->minimum!=mco::Vec3{8.f,14.f,23.f} || result->maximum!=mco::Vec3{15.f,23.f,34.f})
        throw std::runtime_error("mirror/translation order changed");
}
