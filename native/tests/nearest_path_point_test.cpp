#include "mco/nearest_path_point.hpp"
#include <stdexcept>
int main() {
    std::array<std::array<float,3>,17> points{};
    for(unsigned i=0;i<points.size();++i) points[i]={static_cast<float>(i),0,0};
    std::array<float,3> position{9.25f,999,0};
    if(mco::nearest_path_point(points,position,1,8)!=9 ||
       mco::nearest_path_point(points,position,1,0)!=8 ||
       mco::nearest_path_point(points,position,1,-1)!=8)
        throw std::runtime_error("group/count semantics changed");
    position[0]=9.5f;
    if(mco::nearest_path_point(points,position,1,8)!=9)
        throw std::runtime_error("strict equal-distance selection changed");
    try {mco::nearest_path_point(points,position,2,2);}
    catch(const std::invalid_argument&) {return 0;}
    throw std::runtime_error("unmapped point range accepted");
}
