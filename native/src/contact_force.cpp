#include "mco/contact_force.hpp"
#include <cmath>
#include <cstring>
#include <stdexcept>

namespace mco {
namespace {
float read_float(std::span<const std::uint8_t> bytes,std::size_t offset) {
    float value{}; std::memcpy(&value,bytes.data()+offset,4); return value;
}
float read_float(std::span<std::uint8_t> bytes,std::size_t offset) {
    return read_float(std::span<const std::uint8_t>(bytes.data(),bytes.size()),offset);
}
void write_float(std::span<std::uint8_t> bytes,std::size_t offset,float value) {
    std::memcpy(bytes.data()+offset,&value,4);
}
double dot(const std::array<float,3>& a,const std::array<float,3>& b) {
    return static_cast<double>(a[0])*b[0]+static_cast<double>(a[1])*b[1]+
           static_cast<double>(a[2])*b[2];
}
std::array<float,3> normalized(const std::array<float,3>& value) {
    const auto magnitude=std::sqrt(dot(value,value));
    if(magnitude==0.0) return {};
    return {static_cast<float>(value[0]/magnitude),
            static_cast<float>(value[1]/magnitude),
            static_cast<float>(value[2]/magnitude)};
}
std::array<float,3> cross(const std::array<float,3>& a,
                          const std::array<float,3>& b) {
    return {static_cast<float>(a[1]*b[2]-a[2]*b[1]),
            static_cast<float>(a[2]*b[0]-a[0]*b[2]),
            static_cast<float>(a[0]*b[1]-a[1]*b[0])};
}
std::array<float,3> read_vector(std::span<const std::uint8_t> bytes,
                                std::size_t offset) {
    return {read_float(bytes,offset),read_float(bytes,offset+4),
            read_float(bytes,offset+8)};
}
}

ContactResponse contact_response(
    std::span<const std::uint8_t> record,
    const std::array<float,3>& force,
    const std::array<float,3>& contact_point,
    const std::array<float,3>& normal) {
    if(record.size()<0x4f8) throw std::invalid_argument("complete world-object record required");
    ContactResponse result{};
    const auto normal_speed=dot(force,normal);
    if(normal_speed<0.0) {
        const auto direction=normalized(force);
        const auto mass_scale=read_float(record,0x54);
        const auto impulse=static_cast<float>(-normal_speed);
        for(std::size_t i=0;i<3;++i)
            result.linear[i]=static_cast<float>(static_cast<double>(direction[i])*
                                                mass_scale*impulse);
    }

    const auto moment=cross(contact_point,force);
    const auto m=read_vector(record,0x9c);
    const auto m1=read_vector(record,0xa8);
    const auto m2=read_vector(record,0xb4);
    const auto scale=read_vector(record,0x2fc);
    // 0x457780 spills the matrix product to a float local before scaling it.
    const std::array<float,3> unscaled{
        static_cast<float>(static_cast<double>(moment[2])*m2[0]+
                            static_cast<double>(moment[1])*m1[0]+
                            static_cast<double>(moment[0])*m[0]),
        static_cast<float>(static_cast<double>(moment[2])*m2[1]+
                            static_cast<double>(moment[1])*m1[1]+
                            static_cast<double>(moment[0])*m[1]),
        static_cast<float>(static_cast<double>(moment[2])*m2[2]+
                            static_cast<double>(moment[1])*m1[2]+
                            static_cast<double>(moment[0])*m[2])};
    const std::array<float,3> transformed{
        static_cast<float>(unscaled[0]*scale[0]),
        static_cast<float>(unscaled[1]*scale[1]),
        static_cast<float>(unscaled[2]*scale[2])};
    const auto rotation0=read_vector(record,0x78);
    const auto rotation1=read_vector(record,0x84);
    const auto rotation2=read_vector(record,0x90);
    result.angular={
        static_cast<float>(static_cast<double>(transformed[2])*rotation2[0]+
                           static_cast<double>(transformed[1])*rotation1[0]+
                           static_cast<double>(transformed[0])*rotation0[0]),
        static_cast<float>(static_cast<double>(transformed[2])*rotation2[1]+
                           static_cast<double>(transformed[1])*rotation1[1]+
                           static_cast<double>(transformed[0])*rotation0[1]),
        static_cast<float>(static_cast<double>(transformed[2])*rotation2[2]+
                           static_cast<double>(transformed[1])*rotation1[2]+
                           static_cast<double>(transformed[0])*rotation0[2])};
    return result;
}

void contact_forces_step(std::span<std::uint8_t> record,
                         const ContactResponseFn& response) {
    if(record.size()<0x4f8) throw std::invalid_argument("mutable 0x4f8-byte world-object record required");
    if(!response) throw std::invalid_argument("per-contact response is required");
    std::int16_t contacts{};std::memcpy(&contacts,record.data()+0x3bc,2);
    if(contacts==0 || (record[6]!=0 && read_float(record,0x88)>=0.707f)) return;

    const auto velocity=read_vector(record,0x14);
    const auto speed=std::sqrt(dot(velocity,velocity));
    const auto direction=normalized(velocity);
    const std::array<std::size_t,3> basis_offsets{0x78,0x84,0x90};
    std::array<float,3> projection{};
    for(std::size_t row=0;row<3;++row) {
        const auto row_vector=read_vector(record,basis_offsets[row]);
        projection[row]=std::abs(static_cast<float>(dot(direction,row_vector)));
    }
    const auto d0=read_float(record,0xd0),d1=read_float(record,0xcc),
               d2=read_float(record,0xd4);
    const auto term1=static_cast<float>(static_cast<double>(d0)*d2*
        read_float(record,0x30c)*projection[0]*4.0);
    const auto term2=static_cast<float>(static_cast<double>(d2)*d1*
        read_float(record,0x310)*projection[1]*4.0+term1);
    const auto coefficient=(static_cast<double>(d0)*d1*read_float(record,0x314)*
        projection[2]*4.0+term2)*read_float(record,0x308)*0.6125f;
    std::array<float,3> drag{};
    for(std::size_t i=0;i<3;++i)
        drag[i]=static_cast<float>(-speed*velocity[i]*coefficient);

    const auto position=read_vector(record,8);
    constexpr std::array<std::size_t,6> point_offsets{
        0x248,0x254,0x260,0x26c,0x278,0x284};
    std::array<float,3> linear_total{},angular_total{};
    for(const auto offset:point_offsets) {
        auto point=read_vector(record,offset);
        for(std::size_t i=0;i<3;++i) point[i]=static_cast<float>(point[i]-position[i]);
        if(dot(velocity,point)>0.0) {
            const auto normal=normalized(point);
            const auto contribution=response(
                std::span<const std::uint8_t>(record.data(),record.size()),
                drag,point,normal);
            for(std::size_t i=0;i<3;++i) {
                linear_total[i]=static_cast<float>(linear_total[i]+contribution.linear[i]);
                angular_total[i]=static_cast<float>(angular_total[i]+contribution.angular[i]);
            }
        }
    }
    for(std::size_t i=0;i<3;++i) {
        const auto velocity_offset=0x14+i*4;
        const auto angular_offset=0x38+i*4;
        write_float(record,velocity_offset,static_cast<float>(read_float(record,velocity_offset)+
                    static_cast<float>(linear_total[i]*0.03125f)));
        write_float(record,angular_offset,static_cast<float>(read_float(record,angular_offset)+
                    static_cast<float>(angular_total[i]*0.004973592f)));
    }
}
}
