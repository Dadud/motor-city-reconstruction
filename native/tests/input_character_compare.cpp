#include "mco/input_character.hpp"
#include "input_queue_cases.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto enabled=read(input),window=read(input),message=read(input);
        const auto character=read(input),bits=read(input);
        auto f=queue_cases::Fixture::read(input);auto state=f.state();
        emit(mco::input_character(state,enabled,window,message,character,bits));
        f.emit();
    });
}
