#include "mco/collision_support.hpp"
#include "mco/collision_pair_response.hpp"
#include "mco/detail/byte_words.hpp"
#include "mco/geometry_transform.hpp"
#include "mco/track_surface_lookup.hpp"
#include <bit>
#include <cmath>
#include <stdexcept>

namespace mco {
namespace {
using V3 = std::array<float,3>;

float dot(const V3& a,const V3& b) {
    return static_cast<float>((static_cast<double>(a[0])*b[0] +
                               static_cast<double>(a[1])*b[1]) +
                               static_cast<double>(a[2])*b[2]);
}
V3 add(const V3& a,const V3& b) {
    return {static_cast<float>(static_cast<double>(a[0])+b[0]),
            static_cast<float>(static_cast<double>(a[1])+b[1]),
            static_cast<float>(static_cast<double>(a[2])+b[2])};
}
V3 subtract(const V3& a,const V3& b) {
    return {static_cast<float>(static_cast<double>(a[0])-b[0]),
            static_cast<float>(static_cast<double>(a[1])-b[1]),
            static_cast<float>(static_cast<double>(a[2])-b[2])};
}
V3 scale(const V3& a,float s) {
    return {static_cast<float>(static_cast<double>(a[0])*s),
            static_cast<float>(static_cast<double>(a[1])*s),
            static_cast<float>(static_cast<double>(a[2])*s)};
}
std::uint32_t u32(const std::array<std::byte,68>& record,std::size_t offset) {
    return detail::read_word(record,offset);
}
float f32(const std::array<std::byte,68>& record,std::size_t offset) {
    return std::bit_cast<float>(u32(record,offset));
}
void put_u32(std::array<std::uint8_t,0x400>& bytes,std::size_t offset,std::uint32_t value) {
    for(unsigned i=0;i<4;++i) bytes[offset+i]=static_cast<std::uint8_t>(value>>(i*8));
}
} // namespace

SupportGeometryResult correct_support_geometry(
    const TrackSurfaceWorld& world,const std::array<float,3>& initial_position,
    const std::array<float,9>& orientation,const std::array<float,66>& local_points,
    const std::array<std::byte,68>& query_seed,float vertical_velocity) {
    SupportGeometryResult result{};
    result.position=initial_position;
    result.relative_points=transform_world_vertices_22(local_points,orientation,{0,0,0});
    const float one_step=static_cast<float>(static_cast<double>(vertical_velocity)*.03125);
    const float allowance=one_step<0.f ? -one_step : 0.f;

    for(std::size_t i=0;i<22;++i) {
        auto& query=result.queries[i];
        query.index=static_cast<std::uint32_t>(i);
        const auto offset=i*3;
        query.relative_point={result.relative_points[offset],result.relative_points[offset+1],
                              result.relative_points[offset+2]};
        query.record=query_seed;
        if(query.relative_point[1]>0.f) continue;
        const V3 point=add(result.position,query.relative_point);
        if(track_surface_lookup(world,point,query.record)==0) continue;

        const V3 coefficients{f32(query.record,0x2c),f32(query.record,0x30),
                              f32(query.record,0x34)};
        const float squared=dot(coefficients,coefficients);
        if(squared!=0.f) {
            const float inverse=static_cast<float>(1.0/std::sqrt(static_cast<double>(squared)));
            query.normal=scale(coefficients,inverse);
        }
        const auto reference_pointer=u32(query.record,0x10);
        const V3 reference{world.real(reference_pointer),world.real(reference_pointer+4),
                           world.real(reference_pointer+8)};
        query.signed_distance=dot(subtract(point,reference),query.normal);
        query.has_surface=true;
        query.eligible=(-1.f<=static_cast<float>(static_cast<double>(query.signed_distance)-one_step) &&
                        query.signed_distance<allowance &&
                        dot(query.relative_point,query.normal)<0.f);
        if(query.eligible && query.signed_distance<0.f) {
            const V3 correction=scale(query.normal,-query.signed_distance);
            result.position=add(result.position,correction);
            result.correction=add(result.correction,correction);
        }
    }
    return result;
}

SupportImpactResult resolve_support_contacts(
    const TrackSurfaceWorld& world,const CollisionImpactBody& input,
    const SupportGeometryResult& geometry,
    const std::array<std::array<float,2>,32>& coefficient_table,
    float response_scale,std::uint32_t response_mode) {
    SupportImpactResult output{};
    output.body=input;
    output.body.position=geometry.position;
    const float velocity_step=static_cast<float>(static_cast<double>(input.linear_velocity[1])*.03125);
    const float allowance=velocity_step<0.f ? -velocity_step : 0.f;
    const float mode_scale=response_mode==1 ? .65f : response_mode==2 ? .25f : 1.f;

    for(const auto& query:geometry.queries) {
        if(!query.eligible || !query.has_surface) continue;
        const V3 point=add(geometry.position,query.relative_point);
        const auto reference_pointer=u32(query.record,0x10);
        const V3 reference{world.real(reference_pointer),world.real(reference_pointer+4),
                           world.real(reference_pointer+8)};
        const float distance=dot(subtract(point,reference),query.normal);
        if(static_cast<double>(distance)>static_cast<double>(allowance)+.001) continue;

        const auto descriptor=u32(query.record,0x0c);
        const std::uint32_t material=descriptor==0 ? 0u : world.word(descriptor+4)&0x1fu;
        float threshold=static_cast<float>(static_cast<double>(coefficient_table[material][0])*response_scale);
        float sliding=static_cast<float>(static_cast<double>(coefficient_table[material][1])*response_scale);
        if(response_mode==1 || response_mode==2) {
            threshold=static_cast<float>(static_cast<double>(threshold)*mode_scale);
            sliding=static_cast<float>(static_cast<double>(sliding)*mode_scale);
        }
        const auto impact=resolve_surface_impulse(output.body,point,query.normal,threshold,sliding);
        if(!impact.collided) continue;
        output.body=impact.body;
        put_u32(output.body.contact_record,0x3f8,material);
        output.impacted_points[output.support_count++]=query.index;
    }
    return output;
}
} // namespace mco
