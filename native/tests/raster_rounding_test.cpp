#include "mco/raster_rounding.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <limits>
#include <stdexcept>

int main() {
    assert(mco::raster_ceil(1.25f)==2);
    assert(mco::raster_ceil(-1.25f)==-1);
    assert(mco::raster_ceil(-0.0f)==0);
    assert(mco::raster_floor(1.25f)==1);
    assert(mco::raster_floor(-1.25f)==-2);
    assert(mco::raster_floor(0.0f)==0);
    assert(mco::raster_ceil(-2147483648.0f)==std::numeric_limits<std::int32_t>::min());
    assert(mco::raster_floor(2147483520.0f)==2147483520);
    bool rejected=false;
    try { (void)mco::raster_ceil(std::numeric_limits<float>::infinity()); }
    catch(const std::invalid_argument&) { rejected=true; }
    assert(rejected);
}
