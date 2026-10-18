#include "mco/path_side.hpp"
#include <stdexcept>
int main() {
    std::array<std::array<float,3>,2> points{{{0,0,0},{1,0,0}}};
    std::array<float,3> position{0,99,1};
    if(mco::path_side(points,position,0)!=2 || mco::path_side(points,position,1)!=8)
        throw std::runtime_error("path side or last-index wrap changed");
    position[2]=0;
    if(mco::path_side(points,position,0)!=2)
        throw std::runtime_error("collinear classification changed");
    try {mco::path_side(points,position,2);}
    catch(const std::invalid_argument&) {return 0;}
    throw std::runtime_error("unmapped point accepted");
}
