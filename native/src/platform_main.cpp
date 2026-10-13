// Platform bring-up only. No reconstructed gameplay is claimed by this probe.
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>
#include <iostream>
#include <string_view>

int main(int argc, char** argv) {
    bool smoke = false;
    if (argc == 2 && std::string_view(argv[1]) == "--smoke") smoke = true;
    else if (argc != 1) {
        std::cerr << "Usage: mco_platform_probe [--smoke]\n";
        return 2;
    }
    if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_GAMEPAD)) {
        std::cerr << SDL_GetError() << '\n';
        return 1;
    }
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE);
    SDL_Window* window = SDL_CreateWindow("Motor City native platform probe", 960, 540,
        SDL_WINDOW_OPENGL | (smoke ? SDL_WINDOW_HIDDEN : SDL_WINDOW_RESIZABLE));
    SDL_GLContext context = window ? SDL_GL_CreateContext(window) : nullptr;
    if (!context) {
        std::cerr << SDL_GetError() << '\n';
        if (window) SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    bool running = !smoke;
    while (running) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_EVENT_QUIT) running = false;
        }
        SDL_Delay(16);
    }
    SDL_GL_DestroyContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    std::cout << "SDL3/OpenGL 3.3 context created successfully; gameplay not implemented here.\n";
    return 0;
}
