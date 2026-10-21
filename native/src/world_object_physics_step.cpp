#include "mco/world_object_physics_step.hpp"
#include <array>
#include <cmath>
#include <cstring>
#include <stdexcept>

namespace mco {
namespace {
float read_float(std::span<std::uint8_t> bytes, std::size_t offset) {
    float value{};
    std::memcpy(&value, bytes.data()+offset, sizeof(value));
    return value;
}
void write_float(std::span<std::uint8_t> bytes, std::size_t offset, float value) {
    std::memcpy(bytes.data()+offset, &value, sizeof(value));
}
}

void step_world_object_physics(
    std::span<std::uint8_t> record, bool mode_active, std::uint32_t mode_number,
    const WorldObjectPhysicsChild& environment_step,
    const WorldObjectPhysicsChild& contact_force_step) {
    if (record.size()<world_object_record_size)
        throw std::invalid_argument("mutable 0x4f8-byte world-object record required");
    if (!environment_step || !contact_force_step)
        throw std::invalid_argument("both 0x520c20 child stages are required");

    const bool run_forces = !(record[6]!=0 && mode_active && mode_number==1);
    environment_step(record);
    if (run_forces && record[4]!=0 && record[7]==0) {
        write_float(record,0x2c,0.0f);
        write_float(record,0x30,-9.81f);
        write_float(record,0x34,0.0f);
        std::int16_t contacts{};
        std::memcpy(&contacts,record.data()+0x3bc,sizeof(contacts));
        if (contacts==0) {
            // 0x520c20 stores each local gravity component before multiplying
            // it by the corresponding object basis row. Keeping these products
            // in double here changes the original x87 FSTP boundaries and can
            // move the final stored acceleration by one or two float ULPs.
            const auto ax=static_cast<float>(read_float(record,0x320)*-9.81f);
            const auto ay=static_cast<float>(read_float(record,0x32c)*-9.81f);
            const auto az=static_cast<float>(read_float(record,0x338)*-9.81f);
            const std::array<float,9> basis{
                read_float(record,0x31c),read_float(record,0x320),read_float(record,0x324),
                read_float(record,0x328),read_float(record,0x32c),read_float(record,0x330),
                read_float(record,0x334),read_float(record,0x338),read_float(record,0x33c)};
            write_float(record,0x2c,static_cast<float>(
                static_cast<double>(az)*basis[6]+static_cast<double>(ay)*basis[3]+
                static_cast<double>(ax)*basis[0]));
            write_float(record,0x30,static_cast<float>(
                static_cast<double>(az)*basis[7]+static_cast<double>(ay)*basis[4]+
                static_cast<double>(ax)*basis[1]));
            write_float(record,0x34,static_cast<float>(
                static_cast<double>(az)*basis[8]+static_cast<double>(ay)*basis[5]+
                static_cast<double>(ax)*basis[2]));
        }
        if (read_float(record,0x6c)==0.0f) {
            constexpr std::array<std::size_t,3> velocity{0x14,0x18,0x1c};
            constexpr std::array<std::size_t,3> acceleration{0x2c,0x30,0x34};
            for (std::size_t i=0;i<3;++i) {
                const auto value=static_cast<double>(read_float(record,velocity[i]))+
                                 static_cast<double>(read_float(record,acceleration[i]))*0.03125;
                write_float(record,velocity[i],static_cast<float>(value));
            }
        } else {
            for (const auto offset:{0x14u,0x18u,0x1cu,0x38u,0x3cu,0x40u})
                write_float(record,offset,0.0f);
        }
    }
    if (run_forces) contact_force_step(record);

    const auto vector_length=[&](std::size_t offset) {
        const auto x=static_cast<double>(read_float(record,offset));
        const auto y=static_cast<double>(read_float(record,offset+4));
        const auto z=static_cast<double>(read_float(record,offset+8));
        return std::sqrt(x*x+y*y+z*z);
    };
    const auto angular_speed=vector_length(0x38);
    const auto linear_speed=static_cast<float>(vector_length(0x14));
    const auto turns_per_second=static_cast<float>(angular_speed*6.2831855f);
    const auto inertia=vector_length(0x2f0);
    const auto mass=static_cast<double>(read_float(record,0x50));
    const auto energy=static_cast<double>(linear_speed)*mass*linear_speed*0.5+
                      inertia*turns_per_second*turns_per_second*0.5;
    write_float(record,0x3c0,static_cast<float>(energy));
}
}
