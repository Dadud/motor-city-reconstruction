#include "mco/driving_support.hpp"
#include "mco/detail/byte_words.hpp"
#include <bit>
#include <stdexcept>

namespace mco {
namespace {
float real(std::span<const std::byte, 68> query, std::size_t offset) {
  return std::bit_cast<float>(detail::read_word(query, offset));
}
}

SupportProjection project_track_surface(const TrackSurfaceWorld &world,
                                         const SupportQuery &query,
                                         std::array<float, 3> normal_seed) {
  std::array<std::byte, 68> record{};
  auto identity_address = [](const std::optional<std::uint32_t> &value) {
    return value.value_or(0u);
  };
  detail::write_word(record, 0, std::bit_cast<std::uint32_t>(query.record.sector));
  detail::write_word(record, 4, std::bit_cast<std::uint32_t>(query.record.group));
  detail::write_word(record, 8, query.record.status);
  detail::write_word(record, 12, identity_address(query.record.surface_id));
  for (std::size_t i = 0; i < 4; ++i)
    detail::write_word(record, 16 + i * 4, identity_address(query.record.vertex_ids[i]));
  for (std::size_t i = 0; i < 3; ++i)
    detail::write_word(record, 32 + i * 4, std::bit_cast<std::uint32_t>(static_cast<float>(query.previous_world[i])));
  if (query.query_tail)
    for (std::size_t i = 0; i < query.query_tail->size(); ++i)
      record[44 + i] = static_cast<std::byte>((*query.query_tail)[i]);
  std::array<float, 3> point{};
  for (std::size_t i = 0; i < 3; ++i) point[i] = static_cast<float>(query.point[i]);
  sample_track_surface(world, record, point, query.context, normal_seed);
  SupportRecord output;
  output.sector = std::bit_cast<std::int32_t>(detail::read_word(record, 0));
  output.group = std::bit_cast<std::int32_t>(detail::read_word(record, 4));
  output.status = detail::read_word(record, 8);
  const auto descriptor = detail::read_word(record, 12);
  if (descriptor != 0) {
    output.surface_id = descriptor;
    output.surface_code = static_cast<std::uint8_t>(world.word(descriptor + 4) & 0xffu);
  }
  for (std::size_t i = 0; i < 4; ++i) {
    const auto address = detail::read_word(record, 16 + i * 4);
    if (address != 0) output.vertex_ids[i] = address;
  }
  SupportVector reference{};
  for (std::size_t i = 0; i < 3; ++i) reference[i] = real(record, 32 + i * 4);
  std::array<std::uint8_t, 24> tail{};
  for (std::size_t i = 0; i < tail.size(); ++i)
    tail[i] = std::to_integer<std::uint8_t>(record[44 + i]);
  return {SupportVector{point[0], point[1], point[2]}, reference, output, tail};
}

SupportPredictionOutput predict_support_on_track(
    SupportPredictionState state, const TrackSurfaceWorld &world,
    const SupportNormalSeedProvider &normal_seed_for_query) {
  if (!normal_seed_for_query)
    throw std::invalid_argument("row-mode normal seed provider required");
  return predict_support(std::move(state), [&](const SupportQuery &query) {
    return project_track_surface(world, query, normal_seed_for_query(query));
  });
}
}
