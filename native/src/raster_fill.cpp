#include "mco/raster_fill.hpp"
#include "mco/raster_intersection.hpp"
#include "mco/raster_rounding.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace mco {
RasterTriangleMask rasterize_projected_triangle(
    RasterTriangle vertices, float xmin, float xmax, float ymin, float ymax) {
    for(const auto& point:vertices)
        if(!std::isfinite(point[0]) || !std::isfinite(point[1]))
            throw std::invalid_argument("finite float32 triangle coordinates required");
    if(!std::isfinite(xmin) || !std::isfinite(xmax) ||
       !std::isfinite(ymin) || !std::isfinite(ymax))
        throw std::invalid_argument("finite float32 bounds required");
    if(xmin==xmax || ymin==ymax)
        throw std::invalid_argument("projection bounds must have nonzero extents");

    const float sx=static_cast<float>((320.0/(static_cast<double>(xmax)-xmin)));
    const float sy=static_cast<float>((240.0/(static_cast<double>(ymax)-ymin)));
    for(auto& point:vertices) {
        point[0]=static_cast<float>((static_cast<double>(point[0])-xmin)*sx);
        point[1]=static_cast<float>((static_cast<double>(ymax)-point[1])*sy);
        point[0]=std::clamp(point[0],0.0f,320.0f);
        point[1]=std::clamp(point[1],0.0f,240.0f);
    }
    const auto [x1,y1]=vertices[0];
    const auto [x2,y2]=vertices[1];
    const auto [x3,y3]=vertices[2];
    if((static_cast<double>(y2)-y1)*(static_cast<double>(x3)-x1)==
       (static_cast<double>(y3)-y1)*(static_cast<double>(x2)-x1))
        return {};

    const auto ordered=order_triangle_vertices_by_y(vertices);
    const auto& low=ordered[0];
    const auto& middle=ordered[1];
    const auto& high=ordered[2];
    const auto first_row=raster_ceil(low[1]);
    const auto last_row=raster_floor(high[1]);
    RasterTriangleMask bitmap{};
    for(auto row=first_row;row<=last_row;++row) {
        const RasterEdge a = (static_cast<float>(row)<middle[1] || middle[1]==high[1])
            ? RasterEdge{{low,middle}} : RasterEdge{{low,high}};
        const RasterEdge b = (static_cast<float>(row)<middle[1] || middle[1]==high[1])
            ? RasterEdge{{low,high}} : RasterEdge{{middle,high}};
        const auto span=raster_scanline_intersections(a,b,static_cast<float>(row));
        const auto first_x=raster_ceil(span.leftmost_x);
        const auto last_x=raster_floor(span.rightmost_x);
        const auto offset=static_cast<std::size_t>(row)*raster_width;
        for(auto column=first_x;column<=last_x;++column)
            bitmap[offset+static_cast<std::size_t>(column)]=1;
    }
    return bitmap;
}
}
