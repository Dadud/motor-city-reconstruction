#pragma once
#include <array>
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <vector>
namespace mco {
using Vec3 = std::array<float, 3>;
struct FceTriangle {
  std::array<std::uint32_t, 3> indices;
  std::array<float, 6> uv;
  std::uint32_t texture_page, flags;
};
struct FcePart {
  std::string name;
  Vec3 origin;
  std::vector<Vec3> vertices, normals;
  std::vector<FceTriangle> triangles;
};
struct FceModel {
  std::uint32_t version;
  std::vector<FcePart> parts;
  std::vector<std::string> warnings;
};
FceModel decode_fce(std::span<const std::uint8_t> bytes);
// Relative model path is resolved case-insensitively inside the explicit root.
FceModel load_vehicle(const std::filesystem::path &root,
                      const std::filesystem::path &model);
} // namespace mco
