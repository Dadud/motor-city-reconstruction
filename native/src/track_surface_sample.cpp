#include "mco/track_surface_sample.hpp"
#include "mco/detail/byte_words.hpp"
#include "mco/track_surface_lookup.hpp"
#include <bit>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
std::uint32_t load(std::span<const std::byte, 68> bytes, std::size_t offset) {
  return detail::read_word(bytes, offset);
}
float as_float(std::uint32_t bits) { return std::bit_cast<float>(bits); }
std::array<float, 3> cross(const std::array<double, 3> &a,
                           const std::array<double, 3> &b) {
  return {static_cast<float>(a[1] * b[2] - a[2] * b[1]),
          static_cast<float>(a[2] * b[0] - a[0] * b[2]),
          static_cast<float>(a[0] * b[1] - a[1] * b[0])};
}
std::array<float, 3> unit(const std::array<float, 3> &v) {
  const double squared = static_cast<double>(v[2]) * v[2] +
                         static_cast<double>(v[1]) * v[1] +
                         static_cast<double>(v[0]) * v[0];
  if (squared == 0.0) return v;
  const double inverse = 1.0 / std::sqrt(squared);
  return {static_cast<float>(static_cast<double>(v[0]) * inverse),
          static_cast<float>(static_cast<double>(v[1]) * inverse),
          static_cast<float>(static_cast<double>(v[2]) * inverse)};
}
std::array<float, 3> read_point(const TrackSurfaceWorld &world, std::uint32_t address) {
  return {world.real(address), world.real(address + 4), world.real(address + 8)};
}
}

TrackPlane track_plane_from_query(const TrackSurfaceWorld &world,
                                  std::span<const std::byte, 68> query,
                                  std::array<float, 3> normal_seed,
                                  std::optional<std::array<float, 3>> query_point) {
  TrackPlane result;
  result.normal = normal_seed;
  const auto mode = load(query, 12);
  if (mode == 0) {
    const auto index = load(query, 0);
    const std::uint64_t address = std::uint64_t(world.paths_address) +
                                  std::uint64_t(index) * 0x54u;
    if (address > std::numeric_limits<std::uint32_t>::max() - 8u)
      throw std::invalid_argument("track path point address overflow");
    result.reference = read_point(world, static_cast<std::uint32_t>(address));
    return result;
  }

  std::array<std::array<float, 3>, 4> p{};
  for (std::size_t i = 0; i < 4; ++i)
    p[i] = read_point(world, load(query, 16 + i * 4));
  const auto x = query_point ? (*query_point)[0] :
      static_cast<float>(std::bit_cast<std::int32_t>(load(query, 32)));
  const auto z = query_point ? (*query_point)[2] :
      static_cast<float>(std::bit_cast<std::int32_t>(load(query, 40)));
  const double xd = static_cast<double>(x), zd = static_cast<double>(z);
  const bool first =
      ((static_cast<double>(p[0][0]) - p[1][0]) * (zd - p[1][2]) <=
       (static_cast<double>(p[0][2]) - p[1][2]) * (xd - p[1][0])) &&
      ((zd - p[3][2]) * (p[1][0] - p[3][0]) <=
       (xd - p[3][0]) * (p[1][2] - p[3][2])) &&
      ((zd - p[0][2]) * (p[3][0] - p[0][0]) <=
       (xd - p[0][0]) * (p[3][2] - p[0][2]));
  if (first) {
    const std::array<double, 3> a{double(p[0][0]) - p[1][0], double(p[0][1]) - p[1][1], double(p[0][2]) - p[1][2]};
    const std::array<double, 3> b{double(p[3][0]) - p[1][0], double(p[3][1]) - p[1][1], double(p[3][2]) - p[1][2]};
    const auto normal = cross(a, b);
    if (normal[0] != 0.f || normal[1] != 0.f || normal[2] != 0.f) {
      result.reference = p[1];
      result.normal = unit(normal);
      result.normal_written = true;
      return result;
    }
  }
  const std::array<double, 3> a{double(p[2][0]) - p[3][0], double(p[2][1]) - p[3][1], double(p[2][2]) - p[3][2]};
  const std::array<double, 3> b{double(p[1][0]) - p[3][0], double(p[1][1]) - p[3][1], double(p[1][2]) - p[3][2]};
  result.reference = p[1];
  result.normal = unit(cross(a, b));
  result.normal_written = true;
  return result;
}

bool sample_track_surface(const TrackSurfaceWorld &world,
                          std::span<std::byte, 68> query,
                          std::array<float, 3> &point,
                          std::int32_t track_index,
                          std::array<float, 3> normal_seed) {
  detail::write_word(query, 0, std::bit_cast<std::uint32_t>(track_index));
  const auto bits = std::bit_cast<std::uint32_t>(track_index);
  detail::write_word(query, 4, (bits >> 3) | (track_index < 0 ? 0xe0000000u : 0));
  for (std::size_t offset = 8; offset < 32; offset += 4)
    detail::write_word(query, offset, 0);
  if (track_surface_lookup(world, std::span<const float, 3>(point), query) == 0)
    return false;

  const auto plane = track_plane_from_query(world, query, normal_seed, point);
  const double nx = plane.normal[0], ny = plane.normal[1], nz = plane.normal[2];
  const double numerator = (static_cast<double>(point[0]) - plane.reference[0]) * nx +
                           (static_cast<double>(point[2]) - plane.reference[2]) * nz;
  const double height = static_cast<double>(plane.reference[1]) - numerator / ny;
  point[1] = static_cast<float>(height);
  return true;
}
}
