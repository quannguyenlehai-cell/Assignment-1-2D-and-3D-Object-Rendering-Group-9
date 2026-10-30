# Computer Graphics — Assignment 1

Complete Python application for both parts of the supplied assignment:
basic 2D/3D shapes and atom/molecule visualization. Rendering uses OpenGL
3.3 core, custom GLSL shaders, vertex buffers, index buffers and VAOs.
The GUI uses Dear ImGui through `imgui` (pyimgui).

## 1. Run on Windows with Conda

Extract the ZIP first. Open a terminal in the extracted `cg_assignment1`
folder (the folder containing `main.py` and `requirements.txt`).

```powershell
conda create -n cg_assignment1 python=3.11 -y
conda activate cg_assignment1
python -m pip install -r requirements.txt
python main.py
```

Use Python **3.11** for straightforward installation of the pinned GUI package.
Use `python` inside the activated Conda environment; `py` can select a different
Windows Python installation. An OpenGL 3.3-capable GPU driver and a desktop
session are required. This is a desktop application, not a Colab notebook.

If you prefer `venv` and have Python 3.11 installed:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

On Linux/macOS, create a Python 3.11 environment, install the same requirements,
and run `python main.py`. Linux also needs a desktop OpenGL driver. On Linux,
Tkinter may need your distribution's `python3-tk` package for native file
dialogs; the path fields work without Tkinter.

## 2. What is included

| Assignment requirement | Implementation / where to use it |
|---|---|
| Triangle, rectangle, pentagon, regular hexagon, circle, ellipse, trapezoid, star, arrow | **Basic shapes → Shape → Add shape** |
| Cube, sphere, cylinder, cone, truncated cone, tetrahedron, torus, prism | Same shape selector; prism has an editable number of sides |
| User-defined `z = f(x,y)` | **Function surface**: expression, square domain and grid resolution |
| Import `.obj` / `.ply` | **Import OBJ / PLY**: Browse or paste a path, then Import |
| GUI menus/toolbars | Scene/View menus, creation panel, object list and inspector |
| Zoom, pan, rotate | Mouse camera controls and per-object transform controls |
| Flat color | Render mode **Flat color**; one uniform color per mesh, without lighting |
| Gouraud shading | Render mode **Gouraud lighting**; vertex lighting interpolated across triangles |
| Phong shading | Render mode **Phong lighting**; lighting calculated per fragment |
| External texture images | **Texture image → Browse image → Apply texture** |
| Per-object wireframe | Render mode **Wireframe**, using triangle edges |
| Extra plain vertex interpolation | Render mode **Vertex colors (unlit)** |
| Bohr atom visualization | **Atoms and molecules → Element → Add Bohr atom**; H through Ar |
| Electron shells and animation | Concentric shell paths, sphere electrons, Animate/Speed/Show orbital paths controls |
| Ball-and-stick molecules | H2O, CO2, CH4 with colored spheres and cylinder bonds |
| Optional molecule animation | Animate enables illustrative stretch and rotation |
| Hierarchical objects | `Node` scene graph; a parent transform moves every child atom/bond |

## 3. First demonstration

1. The application starts with a cube. Select it in the left object list.
2. Choose each **Render mode** in the right panel. Each object stores its own
   mode, color, texture and transform. Turn **Use vertex colors in lighting**
   off if you want the object color picker to supply the Gouraud/Phong material.
3. Add a star or arrow. These use ear-clipping triangulation, so their concave
   boundaries render correctly. Try unlit vertex colors and wireframe.
4. Clear the scene and add a sphere. Open **Texture image**, browse to your PNG
   or JPG, then click **Apply texture**. `assets/checker.png` is a provided test
   texture; it is also used when Texture mode has no custom image.
5. Open **Function surface**, enter `sin(x)*cos(y)`, and click **Add surface**.
   Rotate it with the mouse to see that its height is `z`. You can also try
   `0.2*(x**2-y**2)` or `exp(-(x**2+y**2))`.
6. Import `assets/sample.obj` and `assets/sample.ply` to exercise both loaders.
7. Clear the scene, add an oxygen Bohr atom, and toggle Animate. Oxygen has
   2 electrons in the first shell and 6 in the second. Hide/show shell paths.
8. Clear the scene and add H2O or CO2. Change viewing angle, then enable Animate.
   CO2 has two cylinders for each double bond.

The canvas sits between the two sidebars. New objects appear near the origin;
multiple objects can overlap. Use Position to separate them or Visible to hide
one while studying another. **Clear all** removes the current in-memory scene.

## 4. Controls

| Input | Action |
|---|---|
| Left mouse drag on canvas | Orbit the camera around the focused object |
| Right mouse drag on canvas | Pan the view |
| Mouse wheel on canvas | Zoom |
| Position / Rotation / Scale controls | Transform the selected object or assembly |
| Home / Focus button | Center and fit the selected object, reset to a front view |
| F / G / P / T / W / I | Flat / Gouraud / Phong / Texture / Wireframe / Vertex colors |
| Space | Toggle animation for the selected assembly |
| Delete | Remove the selected object |
| Esc | Close the application |
| Orthographic checkbox | Switch perspective / orthographic projection |

Shortcuts are ignored when ImGui is capturing keyboard input. Camera drags must
start on the canvas, so dragging a GUI control does not also rotate the view.
Wireframe is set separately for each object and reset before the GUI is drawn.

## 5. Relationship to your existing files

This is a **separate complete project**, using the same nested package layout
shown in your screenshot: `cglibs/cglibs/`. Run its top-level `main.py`.
Do not copy only `app.py` into the old project; it needs the other new modules,
shaders and assets in this archive.

| Supplied module | Treatment in this project |
|---|---|
| `transform.py` | Copied unchanged; reused for matrices, quaternions and Trackball |
| `camera.py` | Copied unchanged for reference/compatibility; the app uses Trackball directly |
| `buffer.py` | Retains VAO/UManager approach; adds correct buffer replacement/cleanup and Pillow texture loading |
| `shader.py` | Same compile/link role; raises useful exceptions and provides explicit cleanup |
| `viewer.py` | Adapted GLFW/Trackball base; resizable window and creation failure handling |
| `shading.py` | Replaced by shared mode constants for the new unified shader pair |
| `hud.py` | Copied unchanged, but the application uses ImGui for help and controls |
| All seven supplied Python files | Unmodified copies in `reference_originals/` for comparison |

The new helpers intentionally avoid the original incidental `pandas` and
OpenCV imports. Cleanup happens before destroying the OpenGL context.
This project does not include the original unrelated demos, so those demos
may need adjustments if you transplant the revised helper files into them.

## 6. Source map and suggested reading order

| Order | File | What to understand |
|---|---|---|
| 1 | `main.py` | Initialize GLFW → create application → run loop → cleanup |
| 2 | `assignment/geometry.py` | CPU arrays for vertices, normals, colors, UVs, triangle indices |
| 3 | `cglibs/cglibs/buffer.py` | Upload arrays into VAO/VBO/EBO |
| 4 | `shaders/scene.vert` | Model/view/projection, transformed normals, Gouraud lighting |
| 5 | `shaders/scene.frag` | Flat/vertex colors, Phong lighting and texture sampling |
| 6 | `assignment/rendering.py` | Bind shader, uniforms, texture; issue `glDrawElements` |
| 7 | `assignment/scene.py` | Local/world transforms, parent/child graph, atom and bond animation |
| 8 | `assignment/app.py` | GUI state, event capture, selected object and the frame loop |

For a gentle starting point, follow `make_shape('Triangle')` into
`regular_polygon()` → `polygon()` → `MeshData`. Then follow that data into
`GPUMesh`. Attribute locations have the same meaning in Python and GLSL:

| GLSL location | CPU array | Components |
|---|---|---|
| 0 | `mesh.positions` | x, y, z |
| 1 | `mesh.colors` | r, g, b |
| 2 | `mesh.normals` | nx, ny, nz |
| 3 | `mesh.uvs` | u, v |

The vertex shader receives a different row from these arrays for each vertex.
It computes `gl_Position = projection * view * model * vec4(position, 1.0)`.
The GPU assembles triangles using the index buffer, clips them, divides by `w`,
maps to the viewport and rasterizes them. Interpolated values become fragment
shader inputs; depth testing decides which visible surface reaches the image.

## 7. Important rendering details

**Flat color vs flat lighting.** The assignment explicitly requests one uniform
object color. Mode 0 therefore outputs `base_color` directly. It does not use
the GLSL `flat` interpolation qualifier or per-face lighting. Gouraud lighting
is evaluated at vertices; Phong lighting is evaluated at fragments. The extra
unlit interpolation mode makes the difference easier to study.

**Normal matrices.** With nonuniform object scale, normals cannot be transformed
like positions. The renderer uploads the inverse transpose of the upper 3×3
part of `view @ model`. Positions, normals and lights then share view space.
Smooth surfaces use smooth normals. Cube/prism/tetrahedron vertices are split
at hard edges; caps and curved sides also have separate normals.

**Surface expressions.** A small AST interpreter permits numbers, `x`, `y`,
`pi`, `e`, `+ - * / **`, and `sin`, `cos`, `tan`, `sqrt`, `exp`, `log`, `abs`,
`minimum`, `maximum`, `clip`. Do not type `np.` or `z =`. No Python `eval` is
used. Undefined/nonfinite domains produce a status message. Domain half-width
is 0.1–10, grid resolution is 4–150, exponents are limited to ±12, and generated
heights must stay within ±10000. Normals come from sampled surface derivatives.

**Model import.** OBJ/PLY triangle meshes are loaded with Trimesh. Scene node
transforms are baked before the entire model is centered/scaled together.
Existing normals, vertex/face colors and UV coordinates are retained when
available; missing normals are computed and missing UVs get planar projection.
Parts share the selected object's render mode and manually selected texture.
Source material/MTL appearance is not reproduced automatically. A file with only
points is not a supported mesh; keep imported models under 2 million triangles.

**Textures.** PNG/JPG/BMP/TIFF images are converted to RGBA, flipped vertically
for UV coordinates, and uploaded with mipmaps. The current shader treats
textures as opaque RGB and applies lighting. Imported meshes without UVs use
a basic planar mapping, which can stretch on curved surfaces.

**Atoms/molecules.** The Bohr display uses neutral-element shell occupancies
for H–Ar. The nucleus is a single stylized sphere; it does not show individual
protons/neutrons. All shells are concentric circles in the XY plane. The water
model uses a 104.5-degree bond angle; CO2 is linear and CH4 is tetrahedral.
Radii, lengths and speeds are teaching-scale values. This is not a quantum
orbital or molecular dynamics simulation. Molecule animation is illustrative
stretch plus rotation, not an infrared spectrum or calculated normal mode.

**Scene persistence.** Scene state is in memory for the current run. Saving and
reopening scene files is not included in the supplied requirements.

## 8. Verification and troubleshooting

CPU checks:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

There are 62 tests covering mesh winding/normals, concave triangulation area,
surface generation and expression rejection, electron counts, bond endpoint
transforms, molecular assemblies and OBJ/PLY import. `tests/smoke_gl.py` adds
an optional Linux Mesa/EGL rendering check for all 17 basic shapes in all six
modes, surfaces, atoms, molecules, imported meshes, textures and GUI sections.
See `verification/VALIDATION.md` for the run performed on this package.

| Symptom | What to do |
|---|---|
| `ModuleNotFoundError` | Activate the environment; run `python -m pip install -r requirements.txt` |
| GUI package tries to compile on Windows | Use Python 3.11, then reinstall the requirements |
| GLFW/OpenGL context creation error | Run on the desktop and install/update your GPU manufacturer's driver |
| File browser unavailable | Paste a full filename in the path field, then Import/Apply texture |
| Surface fails | Check for invalid domains, e.g. `sqrt(x)` on negative x, or use `sqrt(x**2+y**2)` |
| Objects overlap or disappear after panning | Select the object and press Home; edit Position or hide other objects |
| Color picker seems ineffective | Choose Flat color, or turn off Use vertex colors in lighting |
| Molecule color picker seems ineffective | Disable Keep element colors to apply one color to the assembly |
| Opening the program from another folder | Run the full path to `main.py`; shaders/assets resolve relative to the project |

## 9. References

- Pyimgui GLFW integration: https://pyimgui.readthedocs.io/en/latest/reference/imgui.integrations.html
- Pyimgui API reference: https://pyimgui.readthedocs.io/en/latest/reference/modules.html
- Trimesh documentation: https://trimesh.org/
- Khronos OpenGL pipeline: https://www.khronos.org/opengl/wiki/Rendering_Pipeline_Overview
- Assignment's conceptual reference: https://en.wikipedia.org/wiki/Bohr_model
- Assignment's conceptual reference: https://en.wikipedia.org/wiki/Ball-and-stick_model

The uploaded source is retained with its original attribution in
`reference_originals/`. In particular, `transform.py` includes its supplied
author comment.
