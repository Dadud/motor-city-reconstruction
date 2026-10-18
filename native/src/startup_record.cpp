#include "mco/startup_record.hpp"
#include "mco/detail/wide_int.hpp"
#include "mco/layouts.hpp"
#include "mco/acceleration_table.hpp"
#include "mco/gear_binding.hpp"
#include "mco/gear_force_table.hpp"
#include "mco/startup_balance.hpp"
#include "mco/startup_resistance.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <bit>
#include <stdexcept>

namespace mco {
namespace {

// Every translated expression runs in binary64 and narrows where the
// original stores binary32; the helpers return the narrowed value widened
// so no operation ever mixes binary32 operands.
double f32(double value) {
    return static_cast<double>(static_cast<float>(value));
}

std::uint32_t load_bits(const std::span<const std::byte>& data,
                        size_t offset) {
    std::uint32_t bits = 0;
    for (unsigned k = 0; k < 4; ++k)
        bits |= std::to_integer<std::uint32_t>(data[offset+k]) << (k*8);
    return bits;
}

double load_f32(const std::span<const std::byte>& data, size_t offset) {
    return static_cast<double>(std::bit_cast<float>(load_bits(data, offset)));
}

std::int32_t load_i32(const std::span<const std::byte>& data, size_t offset) {
    return static_cast<std::int32_t>(load_bits(data, offset));
}

void store_f32(std::array<std::byte,0x4a8>& record, size_t offset,
               double value) {
    const auto bits = std::bit_cast<std::uint32_t>(static_cast<float>(value));
    for (unsigned k = 0; k < 4; ++k)
        record[offset+k] = static_cast<std::byte>((bits>>(k*8))&255);
}

double turns(double rise, double run) {
    // Original 0x6f1430: atan2 scaled to turns; the result stays binary64
    // until the caller's binary32 store.
    return std::atan2(rise, run)*0.15915493667125702;
}

double turn_limit(double delta) {
    // Original 0x536d80: degrees-to-samples scale clamped to half a turn.
    const double scaled = f32(f32(delta*360.)*f32(0.08330000191926956));
    return std::max(-0.5, std::min(scaled, 0.5));
}

// The tire radius chains products and their sum through the x87 result
// register at 64-bit mantissa precision before one binary32 store; binary64
// intermediates double-round differently on boundary inputs, so the sum is
// rounded exactly through 64-bit and 53-bit mantissas.
using i128 = detail::wide_int;

struct exact {
    i128 mantissa;
    int exponent;        // value = mantissa * 2^exponent
    bool sticky = false; // nonzero bits below the mantissa's low bit
};

exact from_f32(float value) {
    const auto bits = std::bit_cast<std::uint32_t>(value);
    const bool negative = (bits>>31) != 0;
    const int biased = int((bits>>23)&255);
    std::uint32_t fraction = bits&((1u<<23)-1);
    exact result{static_cast<i128>(biased ? (fraction|(1u<<23)) : fraction),
                 biased-127-23};
    if (negative) result.mantissa = -result.mantissa;
    return result;
}

exact multiply(const std::initializer_list<exact>& terms) {
    exact result{1, 0};
    for (const auto& term : terms) {
        result.mantissa *= term.mantissa;
        result.exponent += term.exponent;
    }
    while (result.mantissa != 0 && (result.mantissa&1) == 0) {
        result.mantissa >>= 1;
        ++result.exponent;
    }
    return result;
}

exact add(const exact& left, const exact& right) {
    // Align the lower-exponent term downward so both mantissas stay inside
    // the 127-bit budget; the discarded bits only feed the sticky flag.
    exact result{};
    result.exponent = std::max(left.exponent, right.exponent);
    for (const exact* term : {&left, &right}) {
        const int shift = result.exponent-term->exponent;
        i128 contribution = 0;
        bool sticky = term->sticky;
        if (term->mantissa != 0) {
            if (shift <= 0) {
                contribution = term->mantissa;
            } else if (shift < 127) {
                contribution = term->mantissa>>shift;
                sticky = sticky || (term->mantissa&((i128(1)<<shift)-1)) != 0;
            } else {
                sticky = true;
            }
        }
        result.mantissa += contribution;
        result.sticky = result.sticky || sticky;
    }
    return result;
}

// Round a positive exact value to `bits` significant bits (half-even).
std::pair<i128, int> round_significand(const exact& value, unsigned bits) {
    i128 mantissa = value.mantissa;
    int exponent = value.exponent;
    int length = 0;
    for (i128 scan = mantissa; scan != 0; scan >>= 1) ++length;
    if (length > int(bits)) {
        const int shift = length-int(bits);
        const i128 rest = mantissa&((i128(1)<<shift)-1);
        const bool guard = ((rest>>(shift-1))&1) != 0;
        const bool sticky = value.sticky
            || (rest&((i128(1)<<(shift-1))-1)) != 0;
        mantissa >>= shift;
        exponent += shift;
        if (guard && (sticky || (mantissa&1) != 0)) {
            ++mantissa;
            if (mantissa == (i128(1)<<bits)) {
                mantissa >>= 1;
                ++exponent;
            }
        }
    }
    return {mantissa, exponent};
}

float wheel_radius(float diameter, float aspect, float rim) {
    const exact sum = add(
        multiply({from_f32(diameter), from_f32(0.0254f)}),
        multiply({from_f32(aspect), from_f32(0.01f), from_f32(rim),
                  from_f32(0.001f), exact{2, 0}}));
    const auto [mantissa64, exponent64] = round_significand(sum, 64);
    const auto [mantissa53, exponent53] =
        round_significand({mantissa64, exponent64-1}, 53);
    return static_cast<float>(
        std::ldexp(static_cast<double>(mantissa53), exponent53));
}

std::int32_t marker_index(const std::span<const std::byte>& model,
                          const char* name) {
    // Original 0x4c5ca0: 0x40-stride NUL-terminated name search.
    const std::int32_t count = load_i32(model, 0x11c);
    const size_t length = std::strlen(name);
    for (std::int32_t index = 0; index < count; ++index) {
        const size_t base = 0xe28+size_t(index)*0x40;
        size_t end = base;
        while (end < base+0x40 && std::to_integer<unsigned>(model[end]) != 0)
            ++end;
        if (end-base == length) {
            bool equal = true;
            for (size_t k = 0; k < length; ++k)
                if (std::to_integer<unsigned>(model[base+k])
                        != unsigned(name[k]))
                    equal = false;
            if (equal) return index;
        }
    }
    return -1;
}

constexpr double k_shape_scales[8][3] = {
    {0.88, 0.94, 0.83}, {0.6, 0.8, 0.7}, {0.88, 0.94, 0.83},
    {0.6, 0.8, 0.7}, {0.65, 0.73, 0.85}, {0.65, 0.73, 0.85},
    {0.65, 0.68, 0.8}, {0.6, 0.8, 0.7}};

}

bool startup_record(const std::span<const std::byte> owner,
    const std::span<const std::byte> configuration, bool has_model,
    const std::span<const std::byte> model, float area_query,
    std::array<std::byte,0x4a8>& record) {
    if (configuration.size() < 0x380 || owner.size() < 0x1c94
            || (has_model && model.size() < 0xe68))
        throw std::invalid_argument("startup record input truncated");
    record.fill(std::byte{0});
    const auto number = [&](size_t offset) {
        return load_f32(configuration, offset);
    };
    const auto own = [&](size_t offset) { return load_f32(owner, offset); };
    const auto integer = [&](size_t offset) {
        return load_i32(configuration, offset);
    };
    const double wheelbase = number(configuration::wheelbase);
    double front_axle = 0;
    double rear_axle = 0;
    if (!has_model) {
        front_axle = f32(wheelbase*f32(0.5));
        rear_axle = f32(wheelbase*f32(-0.5));
    } else {
        const std::int32_t front = marker_index(model, ":PPLFwheel");
        if (front < 0) return false;
        front_axle = f32(load_f32(model, 0x128+size_t(front)*0xc));
        const std::int32_t rear = marker_index(model, ":PPLRwheel");
        if (rear < 0) return false;
        rear_axle = f32(load_f32(model, 0x128+size_t(rear)*0xc));
    }
    const std::int32_t shape = integer(0x48);
    const double* scales = (shape >= 0 && shape < 8)
        ? k_shape_scales[shape] : nullptr;
    const double scale0 = scales ? f32(scales[0]) : 1.0;
    const double scale1 = scales ? f32(scales[1]) : 1.0;
    const double scale2 = scales ? f32(scales[2]) : 1.0;
    const double width_sq = own(owner::half_extent_x)*own(owner::half_extent_x)*4.;
    const double length_sq = own(owner::half_extent_y)*own(owner::half_extent_y)*4.;
    const double height_sq = own(owner::half_extent_z)*own(owner::half_extent_z)*4.;
    const double mass = own(owner::mass);
    const double quarter = f32(0.0833333358168602);
    const double inertia_1 = f32((height_sq+length_sq)*scale0*mass*quarter);
    const double inertia_2 = f32((height_sq+width_sq)*scale1*mass*quarter);
    const double inertia_3 = f32((length_sq+width_sq)*scale2*mass*quarter);
    store_f32(record, startup_record::turn_scale_rear, turns(number(0x120), wheelbase));
    store_f32(record, startup_record::turn_scale_front, turns(number(0x11c), wheelbase));
    store_f32(record, startup_record::turn_scale_span,
              turns(std::max(number(0x11c), number(0x120)),
                    f32(own(owner::half_extent_x)*2.)));
    const std::int32_t gear_count = integer(0x32c);
    if (gear_count < 0 || gear_count > 8)
        throw std::invalid_argument("startup record gear count out of range");
    std::array<double,8> ratios{}, losses{};
    for (std::int32_t i = 0; i < gear_count; ++i) {
        ratios[size_t(i)] = number(0x334+size_t(i)*4);
        losses[size_t(i)] = number(0x354+size_t(i)*4);
    }
    const GearBinding binding = bind_gear_tables(integer(configuration::maximum_rpm),
        number(configuration::rear_tire_width), number(configuration::rear_tire_aspect), number(configuration::rear_tire_rim),
        std::span<const double>(ratios.data(), size_t(gear_count)),
        std::span<const double>(losses.data(), size_t(gear_count)),
        number(configuration::final_drive));
    store_f32(record, startup_record::final_drive_inertia, binding.final_drive_inertia);
    store_f32(record, startup_record::wheelbase_turns, turns(wheelbase, number(0xec)));
    for (size_t i = 0; i < 8; ++i) {
        store_f32(record, startup_record::inverse_near_limit_speed+i*4, binding.inverse_near_limit_speed[i]);
        store_f32(record, startup_record::rpm_per_speed+i*4, binding.rpm_per_speed[i]);
        store_f32(record, startup_record::speed_per_rpm+i*4, binding.speed_per_rpm[i]);
        store_f32(record, startup_record::loss_final_ratio+i*4, binding.loss_final_ratio[i]);
        store_f32(record, startup_record::wheel_inertia_factors+i*4, binding.wheel_inertia_factors[i]);
    }
    if (gear_count != 0) {
        store_f32(record, startup_record::top_gear_speed,
                  f32(double(integer(configuration::maximum_rpm)-250)
                      * binding.speed_per_rpm[size_t(gear_count-1)]));
    }
    if (0.5 < std::abs(f32(front_axle-rear_axle)-wheelbase)) return false;
    const double front_radius = wheel_radius(float(number(configuration::front_tire_rim)),
        float(number(configuration::front_tire_aspect)), float(number(configuration::front_tire_width)));
    const double rear_radius = wheel_radius(float(number(configuration::rear_tire_rim)),
        float(number(configuration::rear_tire_aspect)), float(number(configuration::rear_tire_width)));
    store_f32(record, startup_record::front_wheel_radius, front_radius);
    store_f32(record, startup_record::rear_wheel_radius, rear_radius);
    const double clamped_front = std::max(f32(front_radius-f32(0.37)), 0.);
    const double clamped_rear = std::max(f32(rear_radius-f32(0.37)), 0.);
    const double rear_sum = f32(clamped_rear+rear_radius);
    const double front_outer = f32(clamped_front+front_radius);
    const double forward = std::max(f32(front_outer-rear_sum), 0.);
    const double reverse = std::max(f32(rear_sum-front_outer), 0.);
    const double turn_difference =
        f32(f32(turns(forward, wheelbase))-turns(reverse, wheelbase));
    store_f32(record, startup_record::turn_difference, turn_difference);
    store_f32(record, startup_record::turn_limit, turn_limit(turn_difference));
    store_f32(record, startup_record::rear_lever, f32((1.0-number(0x3c))*wheelbase));
    store_f32(record, startup_record::front_lever, f32(number(0x3c)*wheelbase));
    store_f32(record, startup_record::load_coefficient, startup_load_coefficient(configuration));
    store_f32(record, startup_record::balance_coefficient, startup_balance_coefficient(configuration));
    store_f32(record, startup_record::brake_balance, startup_brake_balance(configuration));
    const double fallback = f32((own(owner::half_extent_y)*2.)*(own(owner::half_extent_x)*2.)*f32(0.8));
    const double area = area_query != 0.f ? f32(area_query) : fallback;
    store_f32(record, startup_record::surface_area, area);
    const double weight_delta = number(0x20)-number(0x28);
    const double springs = number(0x104)+number(0xfc);
    store_f32(record, startup_record::rolling_forward,
              f32(springs-number(0x38)*f32(0.45454543828964233)
                  * weight_delta*f32(0.17121680080890656)));
    store_f32(record, startup_record::rolling_reverse,
              f32(springs-number(0x38)*f32(0.3181818127632141)
                  * weight_delta*f32(0.17121680080890656)));
    store_f32(record, startup_record::inertia_pitch, inertia_1);
    store_f32(record, startup_record::inertia_yaw, inertia_2);
    store_f32(record, startup_record::inertia_roll, inertia_3);
    store_f32(record, startup_record::inverse_inertia_pitch, inertia_1 != 0. ? f32(1./inertia_1) : 0.);
    store_f32(record, startup_record::inverse_inertia_yaw, inertia_2 != 0. ? f32(1./inertia_2) : 0.);
    store_f32(record, startup_record::inverse_inertia_roll, inertia_3 != 0. ? f32(1./inertia_3) : 0.);
    store_f32(record, startup_record::front_axle, front_axle);
    store_f32(record, startup_record::rear_axle, rear_axle);
    const std::array<float,8> rpm_steps = [&] {
        std::array<float,8> values{};
        for (size_t i = 0; i < 8; ++i)
            values[i] = static_cast<float>(binding.rpm_per_speed[i]);
        return values;
    }();
    for (int gear = 0; gear < 8; ++gear) {
        if (gear < 2) {
            store_f32(record, startup_record::shift_threshold+size_t(gear)*4, f32(-10000.));
            continue;
        }
        if (gear >= gear_count-1) {
            store_f32(record, startup_record::shift_threshold+size_t(gear)*4, f32(12000.));
            continue;
        }
        double fraction = -1.0;
        if (gear <= gear_count-2) {
            const auto first_raw = gear_force_table(configuration, rpm_steps,
                                                    unsigned(gear));
            const auto second_raw = gear_force_table(configuration, rpm_steps,
                                                    unsigned(gear+1));
            const auto resistance = startup_resistance_table(
                float(number(0x20)), float(number(0x00)), float(area),
                std::uint32_t(integer(0x238)));
            std::array<float,135> first{}, second{};
            for (size_t i = 0; i < 135; ++i) {
                first[i] = static_cast<float>(std::max(
                    f32(double(first_raw[i])-double(resistance[i])), 0.));
                second[i] = static_cast<float>(std::max(
                    f32(double(second_raw[i])-double(resistance[i])), 0.));
            }
            bool accepted = false;
            for (int index = 0; index < 134; ++index) {
                const double a = first[size_t(index)];
                const double a1 = first[size_t(index)+1];
                const double b = second[size_t(index)];
                const double b1 = second[size_t(index)+1];
                if (!(a1 < b1 && a >= b)) continue;
                const double interpolated = f32(
                    (a*(index+1)+(b1*index-b*(index+1))-a1*index)
                    / ((a-a1)+b1-b));
                const double crossing =
                    f32(interpolated*binding.rpm_per_speed[size_t(gear)]);
                const auto rounded = static_cast<long long>(
                    std::nearbyint(crossing));
                if (rounded >= (integer(0x6c)+integer(configuration::maximum_rpm))/2) {
                    fraction = interpolated;
                    accepted = true;
                    if (gear < gear_count-2)
                        fraction = f32(interpolated*f32(0.9800000190734863));
                    break;
                }
            }
            if (!accepted) {
                const std::int32_t maximum = integer(configuration::maximum_rpm);
                const std::int32_t fallback_rpm =
                    gear == 2 ? maximum*7/10 : maximum*3/4;
                fraction = f32(double(fallback_rpm)
                              / binding.rpm_per_speed[size_t(gear)]);
            }
        }
        store_f32(record, startup_record::shift_threshold+size_t(gear)*4, f32(fraction));
    }
    const auto tables = acceleration_table(configuration,
        std::span<const std::byte>(record.data(), record.size()));
    std::memcpy(record.data()+startup_record::acceleration_table, tables.data()+0x128, 0x4a8-0x128);
    return true;
}
}
