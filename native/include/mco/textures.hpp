#pragma once
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <vector>
namespace mco {
struct TextureImage {
  std::string name;
  std::uint16_t width, height;
  std::vector<std::uint8_t> rgba;
};
// First mip only. Direct-color SHPI types 7d/7f/7e/78/6d; unsupported codecs
// fail.
std::vector<TextureImage> decode_fsh(std::span<const std::uint8_t> bytes);
// Returns empty only when part.fsh is absent. Invalid/unsupported members fail.
std::vector<TextureImage>
load_vehicle_textures(const std::filesystem::path &root,
                      const std::filesystem::path &model);
} // namespace mco
