#include "mco/raster_triangle.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <limits>
#include <stdexcept>

int main() {
    const mco::RasterTriangle unique{{{{1,10}},{{2,30}},{{3,20}}}};
    assert((mco::order_triangle_vertices_by_y(unique)==
            mco::RasterTriangle{{{{1,10}},{{3,20}},{{2,30}}}}));
    const mco::RasterTriangle equal{{{{1,10}},{{2,10}},{{3,10}}}};
    assert((mco::order_triangle_vertices_by_y(equal)==
            mco::RasterTriangle{{{{1,10}},{{3,10}},{{2,10}}}}));
    bool rejected=false;
    auto invalid=unique;
    invalid[1][1]=std::numeric_limits<float>::quiet_NaN();
    try { (void)mco::order_triangle_vertices_by_y(invalid); }
    catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
}
