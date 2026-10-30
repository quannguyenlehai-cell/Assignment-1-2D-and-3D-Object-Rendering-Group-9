# Validation performed

## Environment

- Linux, Python 3.12.14
- NumPy 1.26.4
- PyOpenGL 3.1.7
- GLFW Python package 2.9.0 (GLFW 3.4)
- imgui 2.0.0 (built locally with GCC)
- Pillow 12.3.0
- Trimesh 4.4.9
- pytest 8.4.2
- Mesa 25.2.8, EGL offscreen surface, OpenGL 4.5 core context
- Application shaders declare GLSL 330 core and use OpenGL 3.3 features

The recommended Windows setup is Python 3.11. Availability of the
`imgui-2.0.0-cp311-cp311-win_amd64.whl` binary wheel was verified, but the
application was not executed on Windows during this validation.

## Results

`python -m pytest -q` — **62 passed**.

The tests cover:

- All 17 basic shape meshes: valid indices, nondegenerate triangles,
  triangle winding consistent with normals, unit normals and UV ranges.
- Concave arrow/star triangulation area.
- Function surfaces and allowed/rejected expression forms.
- Cylinder endpoint transforms in several orientations, including parallel
  and antiparallel Y-axis bonds.
- Shell/electron counts for H through Ar, plus moving and paused electrons.
- H2O/CO2/CH4 assembly counts and valid animated matrices.
- OBJ and PLY fixtures and the model normalization behavior.

`PYOPENGL_PLATFORM=egl EGL_PLATFORM=surfaceless python tests/smoke_gl.py`
— **119 frames rendered successfully** with no OpenGL errors.

The rendering check compiled/linked the real GLSL shaders, uploaded real GPU
buffers/textures and rendered:

- 17 shapes × 6 modes.
- A function surface.
- A Bohr atom with moving and paused electrons.
- H2O, CO2 and CH4 assemblies.
- OBJ and PLY imports with an applied image texture.
- Orthographic projection and nonuniform object scaling.
- All expandable inspector/creation GUI sections.
- A rejected expression while retaining the previous scene.

The expression-rejection test intentionally prints a `ValueError` status
message before the PASS line. It is an expected check of GUI error handling.

Screenshots `application.png`, `atom.png` and `molecule.png` were captured from
the actual rendered framebuffer and visually inspected.

## Scope of verification

The offscreen test uses a real EGL graphics context, GLFW's null window for
window bookkeeping, and actual ImGui drawing. It substitutes EGL context
management for the desktop GLFW context operations. It does not prove native
desktop window creation, OS file dialogs, physical mouse input or high-DPI
behavior on Windows/macOS. Exercise those on the target computer using the
demonstration steps in README.md.
