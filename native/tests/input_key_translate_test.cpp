#include "mco/input_key_translate.hpp"
#include <stdexcept>
int main() {
    if(mco::input_key_translate(0x100,0x70)!=0x3b00 ||
       mco::input_key_translate(0x104,0x7b)!=0x8800 ||
       mco::input_key_translate(0x100,0x25)!=mco::input_key_translate(0x100,0x64) ||
       mco::input_key_translate(0x101,0x70)!=0 ||
       mco::input_key_translate(0x100,0x41)!=0)
        throw std::runtime_error("packed key translation changed");
}
