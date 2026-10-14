#include "mco/textures.hpp"
#include <algorithm>
#include <iostream>
#include <stdexcept>
namespace {
void put(std::vector<std::uint8_t> &b, size_t o, std::uint32_t n) {
  for (size_t i = 0; i < 4; ++i)
    b[o + i] = std::uint8_t(n >> (8 * i));
}
void require(bool value) {
  if (!value)
    throw std::runtime_error("texture test failed");
}
void rejects(const std::vector<std::uint8_t> &bytes) {
  bool rejected = false;
  try {
    (void)mco::decode_fsh(bytes);
  } catch (const std::runtime_error &) {
    rejected = true;
  }
  require(rejected);
}
std::vector<std::uint8_t> fixture(unsigned kind,
                                  std::initializer_list<std::uint8_t> pixels) {
  std::vector<std::uint8_t> b(40 + pixels.size());
  b[0] = 'S';
  b[1] = 'H';
  b[2] = 'P';
  b[3] = 'I';
  put(b, 4, std::uint32_t(b.size()));
  put(b, 8, 1);
  b[16] = 't';
  put(b, 20, 24);
  put(b, 24, kind);
  b[28] = 1;
  b[30] = 1;
  std::copy(pixels.begin(), pixels.end(), b.begin() + 40);
  return b;
}
} // namespace
int main(int argc, char **argv) {
  try {
    if (argc == 3) {
      auto images = mco::load_vehicle_textures(argv[1], argv[2]);
      for (auto &image : images) {
        std::uint64_t hash = 14695981039346656037ULL;
        for (auto byte : image.rgba) {
          hash ^= byte;
          hash *= 1099511628211ULL;
        }
        std::cout << image.name << ' ' << image.width << ' ' << image.height
                  << ' ' << hash << '\n';
      }
      return 0;
    }
    require(mco::decode_fsh(fixture(0x7d, {3, 2, 1, 4}))[0].rgba ==
            std::vector<std::uint8_t>({1, 2, 3, 4}));
    require(mco::decode_fsh(fixture(0x7f, {3, 2, 1}))[0].rgba ==
            std::vector<std::uint8_t>({1, 2, 3, 255}));
    require(mco::decode_fsh(fixture(0x78, {0, 248}))[0].rgba ==
            std::vector<std::uint8_t>({255, 0, 0, 255}));
    require(mco::decode_fsh(fixture(0x7e, {0, 252}))[0].rgba ==
            std::vector<std::uint8_t>({255, 0, 0, 255}));
    require(mco::decode_fsh(fixture(0x6d, {0x23, 0x41}))[0].rgba ==
            std::vector<std::uint8_t>({17, 34, 51, 68}));
    require(mco::decode_fsh(
                fixture(0xfd, {0x10, 0xfb, 0, 0, 4, 0xe0, 3, 2, 1, 4, 0xfc}))[0]
                .rgba == std::vector<std::uint8_t>({1, 2, 3, 4}));
    require(
        mco::decode_fsh(fixture(0xfd, {0x10, 0xfb, 0, 0, 4, 1, 0, 7, 0xfc}))[0]
            .rgba == std::vector<std::uint8_t>({7, 7, 7, 7}));
    auto plain = fixture(0x7d, {1, 2, 3, 4});
    std::vector<std::uint8_t> compressed{0x10, 0xfb, 0, 0, 44, 0xea};
    compressed.insert(compressed.end(), plain.begin(), plain.end());
    compressed.push_back(0xfc);
    require(mco::decode_fsh(compressed)[0].rgba ==
            std::vector<std::uint8_t>({3, 2, 1, 4}));
    rejects(fixture(0xfd, {0x10, 0xfb, 0, 0, 4, 0, 0, 0xfc}));
    rejects(fixture(0xfd, {0x10, 0xfb, 0, 0, 4, 0x80}));
    rejects(fixture(0xfd, {0x10, 0xfb, 0, 0, 4, 0xc0}));
    rejects(fixture(0xfd, {0x11, 0xfb, 0, 0, 4}));
    auto b = fixture(0x7d, {1, 2, 3, 4});
    auto broken = b;
    broken.resize(12);
    rejects(broken);
    broken = b;
    put(broken, 4, 12);
    rejects(broken);
    broken = b;
    put(broken, 8, 100);
    rejects(broken);
    broken = b;
    put(broken, 20, 12);
    rejects(broken);
    broken = b;
    put(broken, 24, 0x60);
    rejects(broken);
    broken = b;
    put(broken, 24, 0xfd);
    rejects(broken);
    broken = b;
    put(broken, 24, (17 << 8) | 0x7d);
    rejects(broken);
    broken = b;
    broken[28] = 0;
    rejects(broken);
    broken = b;
    broken[28] = 255;
    broken[29] = 255;
    broken[30] = 255;
    broken[31] = 255;
    rejects(broken);
    broken = b;
    broken.resize(43);
    put(broken, 4, 43);
    rejects(broken);
    rejects({0x10, 0xfb, 0, 0, 0});
    std::cout << "bounded direct-color FSH tests passed\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
