// Native geometry inspection milestone: original assets remain external.
#include "mco/fce.hpp"
#include "mco/textures.hpp"
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>
#include <SDL3/SDL_opengl.h>
#include <SDL3/SDL_opengl_glext.h>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
template <class T> T proc(const char *name) {
  auto p = SDL_GL_GetProcAddress(name);
  if (!p)
    throw std::runtime_error(std::string("missing GL entry point: ") + name);
  return reinterpret_cast<T>(p);
}
struct GarageOptions {
  std::string root, model, capture;
  bool smoke = false;
};
GarageOptions parse_options(int argc, char **argv) {
  GarageOptions options;

  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    if (a == "--smoke")
      options.smoke = true;
    else if ((a == "--data" || a == "--model" || a == "--capture") &&
             i + 1 < argc) {
      if (a == "--data")
        options.root = argv[++i];
      else if (a == "--model")
        options.model = argv[++i];
      else
        options.capture = argv[++i];
    } else
      throw std::runtime_error(
          "Usage: mco_native_garage --data ROOT --model "
          "data/models/32ford.viv [--smoke] [--capture frame.ppm]");
  }
  if (options.root.empty() || options.model.empty())
    throw std::runtime_error("--data and --model are required");
  return options;
}
struct DrawBatch {
  std::uint32_t page;
  size_t first, count;
};
struct DrawMesh {
  std::vector<DrawBatch> batches;
  std::vector<float> vertices;
  size_t triangle_count = 0, vertex_count = 0;
};
DrawMesh prepare_draw_mesh(const mco::FceModel &mesh) {
  DrawMesh draw;
  auto &vertices = draw.vertices;
  mco::Vec3 low{INFINITY, INFINITY, INFINITY},
      high{-INFINITY, -INFINITY, -INFINITY};
  auto &triangle_count = draw.triangle_count;
  auto &vertex_count = draw.vertex_count;
  for (auto &p : mesh.parts) {
    vertex_count += p.vertices.size();
    triangle_count += p.triangles.size();
    for (auto &v : p.vertices)
      for (size_t j = 0; j < 3; ++j) {
        low[j] = std::min(low[j], v[j] + p.origin[j]);
        high[j] = std::max(high[j], v[j] + p.origin[j]);
      }
  }
  if (!triangle_count)
    throw std::runtime_error("model contains no drawable triangles");
  float extent = 0;
  mco::Vec3 center;
  for (size_t j = 0; j < 3; ++j) {
    center[j] = low[j] + (high[j] - low[j]) * 0.5f;
    extent = std::max(extent, high[j] - low[j]);
  }
  if (!std::isfinite(extent) || extent <= 0)
    throw std::runtime_error("model bounds cannot be rendered");
  for (auto &p : mesh.parts)
    for (auto &t : p.triangles)
      for (size_t corner = 0; corner < 3; ++corner) {
        auto index = t.indices[corner];
        if (corner == 0) {
          if (draw.batches.empty() ||
              draw.batches.back().page != t.texture_page)
            draw.batches.push_back({t.texture_page, vertices.size() / 8, 0});
          draw.batches.back().count += 3;
        }
        for (size_t j = 0; j < 3; ++j)
          vertices.push_back((p.vertices[index][j] + p.origin[j] - center[j]) *
                             2 / extent);
        for (float n : p.normals[index])
          vertices.push_back(n);
        vertices.push_back(t.uv[corner]);
        vertices.push_back(t.uv[corner + 3]);
      }
  return draw;
}
#define GLPROC(type, name) auto name = proc<type>(#name)
} // namespace
int main(int argc, char **argv) {
  SDL_Window *window = nullptr;
  SDL_GLContext context = nullptr;
  try {
    auto options = parse_options(argc, argv);
    auto &root = options.root;
    auto &model = options.model;
    auto &capture = options.capture;
    bool smoke = options.smoke;
    auto mesh = mco::load_vehicle(root, model);
    auto textures = mco::load_vehicle_textures(root, model);
    auto draw = prepare_draw_mesh(mesh);
    auto &vertices = draw.vertices;
    auto triangle_count = draw.triangle_count;
    auto vertex_count = draw.vertex_count;
    for (auto &w : mesh.warnings)
      std::cerr << w << '\n';
    if (!SDL_Init(SDL_INIT_VIDEO))
      throw std::runtime_error(SDL_GetError());
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,
                        SDL_GL_CONTEXT_PROFILE_CORE);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    window = SDL_CreateWindow(
        "Motor City native garage | drag: orbit, wheel: zoom, Esc: exit", 960,
        640,
        SDL_WINDOW_OPENGL | (smoke ? SDL_WINDOW_HIDDEN : SDL_WINDOW_RESIZABLE));
    if (!window)
      throw std::runtime_error(SDL_GetError());
    context = SDL_GL_CreateContext(window);
    if (!context)
      throw std::runtime_error(SDL_GetError());
    GLPROC(PFNGLCREATESHADERPROC, glCreateShader);
    GLPROC(PFNGLSHADERSOURCEPROC, glShaderSource);
    GLPROC(PFNGLCOMPILESHADERPROC, glCompileShader);
    GLPROC(PFNGLGETSHADERIVPROC, glGetShaderiv);
    GLPROC(PFNGLGETSHADERINFOLOGPROC, glGetShaderInfoLog);
    GLPROC(PFNGLCREATEPROGRAMPROC, glCreateProgram);
    GLPROC(PFNGLATTACHSHADERPROC, glAttachShader);
    GLPROC(PFNGLLINKPROGRAMPROC, glLinkProgram);
    GLPROC(PFNGLGETPROGRAMIVPROC, glGetProgramiv);
    GLPROC(PFNGLGETPROGRAMINFOLOGPROC, glGetProgramInfoLog);
    GLPROC(PFNGLUSEPROGRAMPROC, glUseProgram);
    GLPROC(PFNGLGENVERTEXARRAYSPROC, glGenVertexArrays);
    GLPROC(PFNGLBINDVERTEXARRAYPROC, glBindVertexArray);
    GLPROC(PFNGLGENBUFFERSPROC, glGenBuffers);
    GLPROC(PFNGLBINDBUFFERPROC, glBindBuffer);
    GLPROC(PFNGLBUFFERDATAPROC, glBufferData);
    GLPROC(PFNGLENABLEVERTEXATTRIBARRAYPROC, glEnableVertexAttribArray);
    GLPROC(PFNGLVERTEXATTRIBPOINTERPROC, glVertexAttribPointer);
    GLPROC(PFNGLGETUNIFORMLOCATIONPROC, glGetUniformLocation);
    GLPROC(PFNGLUNIFORM4FPROC, glUniform4f);
    GLPROC(PFNGLUNIFORM1IPROC, glUniform1i);
    using VoidEnum = void(APIENTRY *)(GLenum);
    using ClearColor = void(APIENTRY *)(GLfloat, GLfloat, GLfloat, GLfloat);
    using Viewport = void(APIENTRY *)(GLint, GLint, GLsizei, GLsizei);
    using Draw = void(APIENTRY *)(GLenum, GLint, GLsizei);
    using Read = void(APIENTRY *)(GLint, GLint, GLsizei, GLsizei, GLenum,
                                  GLenum, void *);
    using Error = GLenum(APIENTRY *)();
    auto glEnable = proc<VoidEnum>("glEnable"),
         glClear = proc<VoidEnum>("glClear");
    auto glClearColor = proc<ClearColor>("glClearColor");
    auto glViewport = proc<Viewport>("glViewport");
    auto glDrawArrays = proc<Draw>("glDrawArrays");
    auto glReadPixels = proc<Read>("glReadPixels");
    auto glGetError = proc<Error>("glGetError");
    const char *vs =
        "#version 330 core\nlayout(location=0) in vec3 p; layout(location=1) "
        "in vec3 n; layout(location=2) in vec2 uv; out vec2 texuv; uniform "
        "vec4 camera; out float light; void main(){texuv=uv;float "
        "c=cos(camera.x),s=sin(camera.x),a=cos(camera.y),b=sin(camera.y); vec3 "
        "q=vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z); "
        "q=vec3(q.x,a*q.y-b*q.z,b*q.y+a*q.z); float z=camera.z-q.z; "
        "gl_Position=vec4(q.x*1.7/camera.w,q.y*1.7,((100.0+0.1)/"
        "(100.0-0.1))*z-2.0*100.0*0.1/(100.0-0.1),z); "
        "light=0.28+0.72*abs(dot(normalize(n),normalize(vec3(0.4,0.8,0.6))));}";
    const char *fs = R"GLSL(#version 330 core
in float light;
in vec2 texuv;
uniform sampler2D image;
uniform bool textured;
out vec4 color;
void main() { vec3 base=textured?texture(image,texuv).rgb:vec3(0.42,0.67,0.82); color=vec4(base*light,1.0); }
)GLSL";
    auto shader = [&](GLenum type, const char *source) {
      auto id = glCreateShader(type);
      glShaderSource(id, 1, &source, nullptr);
      glCompileShader(id);
      GLint ok = 0;
      glGetShaderiv(id, GL_COMPILE_STATUS, &ok);
      if (!ok) {
        char log[2048];
        glGetShaderInfoLog(id, sizeof(log), nullptr, log);
        throw std::runtime_error(log);
      }
      return id;
    };
    auto program = glCreateProgram();
    glAttachShader(program, shader(GL_VERTEX_SHADER, vs));
    glAttachShader(program, shader(GL_FRAGMENT_SHADER, fs));
    glLinkProgram(program);
    GLint linked = 0;
    glGetProgramiv(program, GL_LINK_STATUS, &linked);
    if (!linked) {
      char log[2048];
      glGetProgramInfoLog(program, sizeof(log), nullptr, log);
      throw std::runtime_error(log);
    }
    glUseProgram(program);
    GLuint vao, vbo;
    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);
    glGenBuffers(1, &vbo);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, GLsizeiptr(vertices.size() * sizeof(float)),
                 vertices.data(), GL_STATIC_DRAW);
    for (GLuint i = 0; i < 2; ++i) {
      glEnableVertexAttribArray(i);
      glVertexAttribPointer(
          i, 3, GL_FLOAT, GL_FALSE, 8 * sizeof(float),
          reinterpret_cast<void *>(size_t(i) * 3 * sizeof(float)));
    }
    glEnableVertexAttribArray(2);
    glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 8 * sizeof(float),
                          reinterpret_cast<void *>(6 * sizeof(float)));
    using GenTextures = void(APIENTRY *)(GLsizei, GLuint *);
    using BindTexture = void(APIENTRY *)(GLenum, GLuint);
    using TexParameter = void(APIENTRY *)(GLenum, GLenum, GLint);
    using TexImage = void(APIENTRY *)(GLenum, GLint, GLint, GLsizei, GLsizei,
                                      GLint, GLenum, GLenum, const void *);
    auto glGenTextures = proc<GenTextures>("glGenTextures");
    auto glBindTexture = proc<BindTexture>("glBindTexture");
    auto glTexParameteri = proc<TexParameter>("glTexParameteri");
    auto glTexImage2D = proc<TexImage>("glTexImage2D");
    std::vector<GLuint> gpu_textures(textures.size());
    glGenTextures(GLsizei(gpu_textures.size()), gpu_textures.data());
    for (size_t i = 0; i < textures.size(); ++i) {
      auto &image = textures[i];
      glBindTexture(GL_TEXTURE_2D, gpu_textures[i]);
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
      glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
      glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, image.width, image.height, 0,
                   GL_RGBA, GL_UNSIGNED_BYTE, image.rgba.data());
    }
    GLint textured = glGetUniformLocation(program, "textured");
    glUniform1i(glGetUniformLocation(program, "image"), 0);
    GLint camera = glGetUniformLocation(program, "camera");
    glEnable(GL_DEPTH_TEST);
    glClearColor(0.055f, 0.07f, 0.09f, 1);
    float yaw = 0.6f, pitch = 0.25f, distance = 3.7f;
    bool running = true;
    while (running) {
      SDL_Event e;
      while (SDL_PollEvent(&e)) {
        if (e.type == SDL_EVENT_QUIT ||
            (e.type == SDL_EVENT_KEY_DOWN && e.key.key == SDLK_ESCAPE))
          running = false;
        if (e.type == SDL_EVENT_MOUSE_MOTION &&
            (e.motion.state & SDL_BUTTON_LMASK)) {
          yaw += e.motion.xrel * 0.01f;
          pitch = std::clamp(pitch + e.motion.yrel * 0.01f, -1.4f, 1.4f);
        }
        if (e.type == SDL_EVENT_MOUSE_WHEEL)
          distance = std::clamp(distance - e.wheel.y * 0.25f, 2.1f, 12.0f);
      }
      int width, height;
      SDL_GetWindowSizeInPixels(window, &width, &height);
      if (width < 1 || height < 1) {
        SDL_Delay(16);
        continue;
      }
      glViewport(0, 0, width, height);
      glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
      glUniform4f(camera, yaw, pitch, distance, float(width) / float(height));
      for (auto &batch : draw.batches) {
        bool has_texture = batch.page < gpu_textures.size();
        glUniform1i(textured, has_texture ? 1 : 0);
        if (has_texture)
          glBindTexture(GL_TEXTURE_2D, gpu_textures[batch.page]);
        glDrawArrays(GL_TRIANGLES, GLint(batch.first), GLsizei(batch.count));
      }
      if (smoke || !capture.empty()) {
        std::vector<unsigned char> pixels(size_t(width) * size_t(height) * 4);
        glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE,
                     pixels.data());
        size_t foreground = 0;
        for (size_t i = 0; i < pixels.size(); i += 4)
          if (pixels[i] > 30 || pixels[i + 1] > 35 || pixels[i + 2] > 40)
            ++foreground;
        if (!capture.empty()) {
          std::ofstream image(capture, std::ios::binary);
          if (!image)
            throw std::runtime_error("cannot create frame capture");
          image << "P6\n" << width << ' ' << height << "\n255\n";
          for (int y = height - 1; y >= 0; --y)
            for (int x = 0; x < width; ++x)
              image.write(reinterpret_cast<const char *>(
                              pixels.data() +
                              4 * (size_t(y) * size_t(width) + size_t(x))),
                          3);
          if (!image)
            throw std::runtime_error("failed to write frame capture");
          capture.clear();
        }
        if (glGetError() != GL_NO_ERROR || foreground < 100)
          throw std::runtime_error(
              "smoke frame contains no rendered geometry or GL error");
        std::cout << "Rendered " << mesh.parts.size() << " parts, "
                  << vertex_count << " vertices, " << triangle_count
                  << " triangles, " << textures.size()
                  << " texture pages; foreground pixels=" << foreground << "\n";
        if (smoke)
          running = false;
      }
      SDL_GL_SwapWindow(window);
      if (!smoke)
        SDL_Delay(16);
    }
    SDL_GL_DestroyContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    if (context)
      SDL_GL_DestroyContext(context);
    if (window)
      SDL_DestroyWindow(window);
    SDL_Quit();
    return 1;
  }
}
