#pragma once
#include <array>
#include <cmath>
#include <cstdint>

namespace mco::detail {
// The startup radius calculation needs at most 127 magnitude bits. Store
// two's-complement words explicitly so MSVC and Clang use the same arithmetic.
// Operations wrap modulo 2^128; callers must keep signed results in range.
class wide_int {
    std::array<std::uint32_t, 4> words_{};

public:
    constexpr wide_int() = default;
    constexpr wide_int(std::int64_t value) {
        const auto bits = static_cast<std::uint64_t>(value);
        words_ = {static_cast<std::uint32_t>(bits),
                  static_cast<std::uint32_t>(bits >> 32),
                  value < 0 ? 0xffffffffu : 0u,
                  value < 0 ? 0xffffffffu : 0u};
    }
    static constexpr wide_int from_words(std::array<std::uint32_t, 4> words) {
        wide_int result;
        result.words_ = words;
        return result;
    }
    constexpr const auto& words() const { return words_; }
    constexpr bool negative() const { return (words_[3] & 0x80000000u) != 0; }
    friend constexpr bool operator==(const wide_int&, const wide_int&) = default;

    constexpr wide_int& operator+=(const wide_int& other) {
        std::uint64_t carry = 0;
        for (unsigned k = 0; k < 4; ++k) {
            const auto sum = std::uint64_t(words_[k]) + other.words_[k] + carry;
            words_[k] = static_cast<std::uint32_t>(sum);
            carry = sum >> 32;
        }
        return *this;
    }
    friend constexpr wide_int operator+(wide_int left, const wide_int& right) {
        return left += right;
    }
    constexpr wide_int operator-() const {
        wide_int result;
        for (unsigned k = 0; k < 4; ++k) result.words_[k] = ~words_[k];
        return result += wide_int(1);
    }
    friend constexpr wide_int operator-(wide_int left, const wide_int& right) {
        return left += -right;
    }
    constexpr wide_int& operator++() { return *this += wide_int(1); }
    friend constexpr wide_int operator&(const wide_int& left, const wide_int& right) {
        wide_int result;
        for (unsigned k = 0; k < 4; ++k)
            result.words_[k] = left.words_[k] & right.words_[k];
        return result;
    }
    constexpr wide_int& operator*=(const wide_int& other) {
        wide_int result;
        for (unsigned i = 0; i < 4; ++i) {
            std::uint64_t carry = 0;
            for (unsigned j = 0; i+j < 4; ++j) {
                // Maximum product + existing word + carry fits uint64 exactly.
                const auto sum = std::uint64_t(words_[i]) * other.words_[j]
                    + result.words_[i+j] + carry;
                result.words_[i+j] = static_cast<std::uint32_t>(sum);
                carry = sum >> 32;
            }
        }
        return *this = result;
    }
    friend constexpr wide_int operator*(wide_int left, const wide_int& right) {
        return left *= right;
    }
    friend constexpr wide_int operator<<(const wide_int& value, unsigned shift) {
        wide_int result;
        if (shift >= 128) return result;
        const unsigned whole = shift / 32, part = shift % 32;
        for (unsigned k = whole; k < 4; ++k) {
            result.words_[k] = value.words_[k-whole] << part;
            if (part && k > whole)
                result.words_[k] |= value.words_[k-whole-1] >> (32-part);
        }
        return result;
    }
    friend constexpr wide_int operator>>(const wide_int& value, unsigned shift) {
        const auto fill = value.negative() ? 0xffffffffu : 0u;
        if (shift >= 128) return wide_int(value.negative() ? -1 : 0);
        wide_int result;
        const unsigned whole = shift / 32, part = shift % 32;
        const auto word = [&](unsigned index) {
            return index < 4 ? value.words_[index] : fill;
        };
        for (unsigned k = 0; k < 4; ++k) {
            result.words_[k] = word(k+whole) >> part;
            if (part) result.words_[k] |= word(k+whole+1) << (32-part);
        }
        return result;
    }
    constexpr wide_int& operator>>=(unsigned shift) { return *this = *this >> shift; }

    explicit operator double() const {
        // Round the magnitude once to binary64, ties to even. Converting the
        // high and low halves separately could introduce a second rounding.
        const bool sign = negative();
        const wide_int magnitude = sign ? -*this : *this;
        unsigned length = 0;
        // Logical magnitude scan also handles the magnitude of INT128_MIN.
        for (unsigned k = 0; k < 4; ++k) {
            auto word = magnitude.words_[k];
            unsigned bits = 0;
            while (word) { word >>= 1; ++bits; }
            if (bits) length = k*32 + bits;
        }
        const unsigned shift = length > 53 ? length-53 : 0;
        // After shifting, only the low 53 bits are used; arithmetic sign
        // extension of INT128_MIN does not affect those bits.
        const auto top = magnitude >> shift;
        std::uint64_t significand = std::uint64_t(top.words_[0])
            | (std::uint64_t(top.words_[1] & 0x1fffffu) << 32);
        if (shift) {
            const auto rest = magnitude & ((wide_int(1) << shift)-wide_int(1));
            const bool guard = ((rest >> (shift-1)) & wide_int(1)) != wide_int(0);
            const bool sticky = (rest & ((wide_int(1) << (shift-1))-wide_int(1)))
                != wide_int(0);
            if (guard && (sticky || (significand & 1))) ++significand;
        }
        const double result = std::ldexp(static_cast<double>(significand), int(shift));
        return sign ? -result : result;
    }
};
}  // namespace mco::detail
