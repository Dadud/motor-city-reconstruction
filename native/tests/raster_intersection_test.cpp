#include "mco/raster_intersection.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <limits>
#include <stdexcept>

int main() {
    const auto result=mco::raster_scanline_intersections(
        {{{{1,0}},{{5,10}}}}, {{{{10,0}},{{14,10}}}}, 5);
    assert(result.leftmost_x==3 && result.rightmost_x==12);
    bool rejected=false;
    try {
        (void)mco::raster_scanline_intersections(
            {{{{1,0}},{{5,0}}}}, {{{{10,0}},{{14,10}}}}, 5);
    } catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
    rejected=false;
    try {
        (void)mco::raster_scanline_intersections(
            {{{{1,0}},{{5,10}}}}, {{{{10,0}},{{14,10}}}},
            std::numeric_limits<float>::infinity());
    } catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
}
