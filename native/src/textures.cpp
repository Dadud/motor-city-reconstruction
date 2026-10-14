#include "mco/textures.hpp"
#include "mco/viv.hpp"
#include <algorithm>
#include <array>
#include <fstream>
#include <stdexcept>
namespace mco {
namespace {
std::vector<std::uint8_t> unpack_qfs(std::span<const std::uint8_t> input) {
  if (input.size() < 5 || (input[0] != 0x10 && input[0] != 0x11) ||
      input[1] != 0xfb)
    throw std::runtime_error("unsupported QFS header");
  size_t expected =
      (size_t(input[2]) << 16) | (size_t(input[3]) << 8) | input[4];
  if (expected > 64 * 1024 * 1024)
    throw std::runtime_error("QFS output budget exceeded");
  size_t cursor = (input[0] & 1) ? 8 : 5;
  std::vector<std::uint8_t> output;
  output.reserve(expected);
  auto take = [&]() {
    if (cursor >= input.size())
      throw std::runtime_error("truncated QFS command");
    return input[cursor++];
  };
  auto literals = [&](size_t count) {
    if (cursor > input.size() || count > input.size() - cursor ||
        count > expected - output.size())
      throw std::runtime_error("QFS literal bounds exceeded");
    output.insert(output.end(), input.begin() + cursor,
                  input.begin() + cursor + count);
    cursor += count;
  };
  while (true) {
    unsigned command = take();
    if (command >= 0xfc) {
      literals(command & 3);
      break;
    }
    if (command >= 0xe0) {
      literals(((command & 31) + 1) * 4);
      continue;
    }
    size_t literal, length, distance;
    if (command < 0x80) {
      unsigned b = take();
      literal = command & 3;
      length = ((command >> 2) & 7) + 3;
      distance = ((command >> 5) << 8) + b + 1;
    } else if (command < 0xc0) {
      unsigned b = take(), c = take();
      literal = b >> 6;
      length = (command & 63) + 4;
      distance = ((b & 63) << 8) + c + 1;
    } else {
      unsigned b = take(), c = take(), d = take();
      literal = command & 3;
      length = ((command & 12) << 6) + d + 5;
      distance = ((command & 16) << 12) + (b << 8) + c + 1;
    }
    literals(literal);
    if (distance > output.size() || length > expected - output.size())
      throw std::runtime_error("invalid QFS backreference");
    for (size_t i = 0; i < length; ++i)
      output.push_back(output[output.size() - distance]);
  }
  if (output.size() != expected)
    throw std::runtime_error("QFS output size mismatch");
  return output;
}
std::string lower(std::string s) {
  for (char &c : s)
    if (c >= 'A' && c <= 'Z')
      c = char(c - 'A' + 'a');
  return s;
}
} // namespace
std::vector<TextureImage> decode_fsh(std::span<const std::uint8_t> b) {
  if (b.size() > 64 * 1024 * 1024)
    throw std::runtime_error("FSH input budget exceeded");
  std::vector<std::uint8_t> decompressed;
  if (b.size() >= 2 && (b[0] == 0x10 || b[0] == 0x11) && b[1] == 0xfb) {
    decompressed = unpack_qfs(b);
    b = decompressed;
  }
  if (b.size() < 16 || b[0] != 'S' || b[1] != 'H' || b[2] != 'P' || b[3] != 'I')
    throw std::runtime_error("unsupported FSH container");
  auto u = [&](size_t o) -> std::uint32_t {
    if (o > b.size() || b.size() - o < 4)
      throw std::runtime_error("FSH read outside file");
    return std::uint32_t(b[o]) | (std::uint32_t(b[o + 1]) << 8) |
           (std::uint32_t(b[o + 2]) << 16) | (std::uint32_t(b[o + 3]) << 24);
  };
  auto h = [&](size_t o) -> std::uint16_t {
    if (o > b.size() || b.size() - o < 2)
      throw std::runtime_error("FSH read outside file");
    return std::uint16_t(b[o]) | std::uint16_t(b[o + 1] << 8);
  };
  size_t size = u(4), count = u(8);
  if (count > 4096)
    throw std::runtime_error("FSH directory entry budget exceeded");
  if (size != b.size() || count > (size - 16) / 8)
    throw std::runtime_error("invalid FSH directory size");
  std::vector<size_t> offsets;
  for (size_t i = 0; i < count; ++i) {
    size_t o = u(20 + 8 * i);
    if (o < 16 + count * 8 || o > size || size - o < 16)
      throw std::runtime_error("FSH entry outside file");
    offsets.push_back(o);
  }
  auto sorted = offsets;
  std::sort(sorted.begin(), sorted.end());
  sorted.erase(std::unique(sorted.begin(), sorted.end()), sorted.end());
  std::vector<TextureImage> images;
  size_t total = 0;
  for (size_t i = 0; i < count; ++i) {
    size_t o = offsets[i];
    auto next = std::upper_bound(sorted.begin(), sorted.end(), o);
    size_t boundary = next == sorted.end() ? size : *next;
    if (boundary - o < 16)
      throw std::runtime_error("overlapping FSH entry header");
    auto code = u(o);
    unsigned kind = code & 127;
    if (kind == 0x22 || kind == 0x24 || kind == 0x29 || kind == 0x2a ||
        kind == 0x2d || kind == 0x6f)
      continue;

    size_t stride = kind == 0x7d                                     ? 4
                    : kind == 0x7f                                   ? 3
                    : (kind == 0x7e || kind == 0x78 || kind == 0x6d) ? 2
                                                                     : 0;
    if (!stride)
      throw std::runtime_error("unsupported native FSH pixel type " +
                               std::to_string(kind));
    TextureImage image;
    image.width = h(o + 4);
    image.height = h(o + 6);
    size_t pixels = size_t(image.width) * image.height;
    if (!pixels || pixels > 16777216 - total)
      throw std::runtime_error("invalid FSH dimensions or pixel budget");
    total += pixels;
    size_t link = code >> 8;
    if (link) {
      if (link < 16 || link > boundary - o)
        throw std::runtime_error("FSH attachment link outside entry");
      boundary = o + link;
    }
    auto raw = b.subspan(o + 16, boundary - o - 16);
    std::vector<std::uint8_t> uncompressed;
    if (code & 128) {
      uncompressed = unpack_qfs(raw);
      raw = uncompressed;
    }
    if (pixels > raw.size() / stride)
      throw std::runtime_error("truncated FSH pixels");
    for (size_t j = 0; j < 4; ++j) {
      auto c = b[16 + 8 * i + j];
      if (c < 128)
        image.name += char(c);
      else {
        image.name += char(0xc0 | (c >> 6));
        image.name += char(0x80 | (c & 63));
      }
    }
    image.rgba.resize(pixels * 4);
    for (size_t p = 0; p < pixels; ++p) {
      size_t source = p * stride, target = p * 4;
      unsigned r, g, blue, a = 255;
      if (stride >= 3) {
        blue = raw[source];
        g = raw[source + 1];
        r = raw[source + 2];
        if (stride == 4)
          a = raw[source + 3];
      } else {
        unsigned v = unsigned(raw[source]) | (unsigned(raw[source + 1]) << 8);
        if (kind == 0x78) {
          r = (v >> 11) * 255 / 31;
          g = ((v >> 5) & 63) * 255 / 63;
          blue = (v & 31) * 255 / 31;
        } else if (kind == 0x7e) {
          r = ((v >> 10) & 31) * 255 / 31;
          g = ((v >> 5) & 31) * 255 / 31;
          blue = (v & 31) * 255 / 31;
          a = (v & 0x8000) ? 255 : 0;
        } else {
          r = ((v >> 8) & 15) * 17;
          g = ((v >> 4) & 15) * 17;
          blue = (v & 15) * 17;
          a = (v >> 12) * 17;
        }
      }
      image.rgba[target] = std::uint8_t(r);
      image.rgba[target + 1] = std::uint8_t(g);
      image.rgba[target + 2] = std::uint8_t(blue);
      image.rgba[target + 3] = std::uint8_t(a);
    }
    images.push_back(std::move(image));
  }
  return images;
}
std::vector<TextureImage>
load_vehicle_textures(const std::filesystem::path &root,
                      const std::filesystem::path &model) {
  namespace fs = std::filesystem;
  auto base = fs::canonical(root), path = base;
  if (model.empty() || model.is_absolute() || model.has_root_name())
    throw std::runtime_error("model must be relative to data root");
  for (const auto &component : model) {
    if (component == "." || component == "..")
      throw std::runtime_error("model traversal rejected");
    fs::path found;
    for (auto &e : fs::directory_iterator(path))
      if (lower(e.path().filename().string()) == lower(component.string())) {
        if (!found.empty())
          throw std::runtime_error("case-ambiguous asset path");
        found = e.path();
      }
    if (found.empty())
      throw std::runtime_error("model path not found");
    path = fs::canonical(found);
    auto rel = path.lexically_relative(base);
    if (rel.empty() || *rel.begin() == "..")
      throw std::runtime_error("asset symlink leaves data root");
  }
  std::ifstream file(path, std::ios::binary | std::ios::ate);
  if (!file)
    throw std::runtime_error("cannot read model archive");
  auto size = file.tellg();
  if (size < 0 || size > 256 * 1024 * 1024)
    throw std::runtime_error("archive read budget exceeded");
  std::vector<std::uint8_t> bytes(static_cast<size_t>(size));
  file.seekg(0);
  if (!file.read(reinterpret_cast<char *>(bytes.data()), size))
    throw std::runtime_error("truncated archive read");
  auto entries = parse_viv_directory(bytes);
  const VivEntry *found = nullptr;
  for (auto &e : entries)
    if (lower(e.name) == "part.fsh") {
      if (found)
        throw std::runtime_error("case-ambiguous part.fsh");
      found = &e;
    }
  if (!found)
    return {};
  if (found->size > 64 * 1024 * 1024)
    throw std::runtime_error("FSH member budget exceeded");
  return decode_fsh(std::span(bytes).subspan(found->offset, found->size));
}
} // namespace mco
