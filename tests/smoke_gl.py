"""Offscreen Linux smoke check for real GLSL draws and ImGui layout.

Run from the project root:
  PYOPENGL_PLATFORM=egl EGL_PLATFORM=surfaceless python tests/smoke_gl.py

Requires Mesa EGL. Uses GLFW's null window for window size/input bookkeeping,
and a real EGL pbuffer/core context for rendering. Native window creation and
native file dialogs still need a desktop check on the target OS.
"""
import os
os.environ.setdefault('PYOPENGL_PLATFORM', 'egl')
os.environ.setdefault('EGL_PLATFORM', 'surfaceless')
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ctypes import c_int, pointer
import numpy as np
import glfw
from OpenGL import EGL, GL
from PIL import Image


def main():
    display = EGL.eglGetDisplay(EGL.EGL_DEFAULT_DISPLAY)
    major, minor = c_int(), c_int()
    EGL.eglInitialize(display, pointer(major), pointer(minor))
    attrs = (c_int*13)(EGL.EGL_SURFACE_TYPE, EGL.EGL_PBUFFER_BIT,
                      EGL.EGL_RENDERABLE_TYPE, EGL.EGL_OPENGL_BIT,
                      EGL.EGL_RED_SIZE, 8, EGL.EGL_GREEN_SIZE, 8,
                      EGL.EGL_BLUE_SIZE, 8, EGL.EGL_DEPTH_SIZE, 24, EGL.EGL_NONE)
    config, count = EGL.EGLConfig(), c_int()
    EGL.eglChooseConfig(display, attrs, pointer(config), 1, pointer(count))
    assert count.value
    EGL.eglBindAPI(EGL.EGL_OPENGL_API)
    surface = EGL.eglCreatePbufferSurface(display, config, (c_int*5)(EGL.EGL_WIDTH, 1280, EGL.EGL_HEIGHT, 800, EGL.EGL_NONE))
    # EGL_KHR_create_context: major=3, minor=3, core profile bit=1.
    context = EGL.eglCreateContext(display, config, EGL.EGL_NO_CONTEXT,
                                  (c_int*7)(0x3098, 3, 0x30FB, 3, 0x30FD, 1, EGL.EGL_NONE))
    EGL.eglMakeCurrent(display, surface, surface, context)
    glfw.init_hint(glfw.PLATFORM, glfw.PLATFORM_NULL)
    assert glfw.init()
    glfw.window_hint(glfw.CLIENT_API, glfw.NO_API)
    old_current, old_swap_interval = glfw.make_context_current, glfw.swap_interval
    glfw.make_context_current = lambda window: None
    glfw.swap_interval = lambda interval: None
    from assignment.app import AssignmentApp
    from assignment.geometry import SHAPES_2D, SHAPES_3D, make_shape, surface as make_surface
    from assignment.scene import shape_object, bohr_atom, molecule
    from assignment.rendering import ROOT
    import imgui
    app = None
    frames = 0
    try:
        app = AssignmentApp(visible=False)
        glfw.set_window_size(app.win, 1280, 800)
        def frame():
            nonlocal frames
            app.draw_frame(1/60)
            GL.glFinish()
            assert GL.glGetError() == GL.GL_NO_ERROR
            raw = GL.glReadPixels(0, 0, 1280, 800, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
            pixels = np.frombuffer(raw, np.uint8).reshape(800,1280,3)[::-1].copy()
            canvas = pixels[30:795, 305:975]
            background = np.array(app.background)*255
            assert np.count_nonzero(np.max(np.abs(canvas-background),axis=2)>20) > 100
            frames += 1
            return pixels
        frame()
        for name in SHAPES_2D+SHAPES_3D:
            app.clear_scene(); app.add_object(shape_object(name, make_shape(name)))
            for mode in range(6):
                app.active.mode = mode
                frame()
        app.clear_scene()
        app.add_object(shape_object('z = sin(x)*cos(y)', make_surface()))
        app.active.rotation = [-55, 0, -30]
        frame()
        app.clear_scene(); app.add_object(bohr_atom(7)); frame()
        before = app.active.time
        app.active.animate = False; frame()
        assert app.active.time == before
        app.active.animate = True; frame(); assert app.active.time > before
        snapshots = Path(os.environ.get('CG_SMOKE_OUTPUT', str(ROOT/'verification')))
        snapshots.mkdir(exist_ok=True, parents=True)
        Image.fromarray(frame()).save(snapshots/'atom.png')
        for name in ['H2O', 'CO2', 'CH4']:
            app.clear_scene(); app.add_object(molecule(name))
            app.active.animate = True
            pixels = frame()
            if name == 'H2O':
                Image.fromarray(pixels).save(snapshots/'molecule.png')
        for filename in ['sample.obj', 'sample.ply']:
            app.clear_scene(); app.model_path = str(ROOT/'assets'/filename)
            app.load_model(); app.load_texture(); frame()
            app.orthographic = True; frame(); app.orthographic = False
            app.active.scaling = [.6, 1.7, .85]; frame()
        # Exercise all collapsed GUI branches to detect API/signature errors.
        original_header = imgui.collapsing_header
        imgui.collapsing_header = lambda *a, **k: (True, True)
        frame()
        imgui.collapsing_header = original_header
        # Error handling must retain the previous scene.
        previous = app.active
        app.expression = '__import__("os")'
        app.attempt(lambda: make_surface(app.expression))
        assert app.is_error and app.active is previous
        app.expression = 'sin(x)*cos(y)'; app.is_error = False
        app.clear_scene(); app.add_object(shape_object('Sphere', make_shape('Sphere')))
        app.active.vertex_colors = False; app.active.mode = 2
        Image.fromarray(frame()).save(snapshots/'application.png')
        print(f'PASS: {frames} frames; 17 shapes x 6 modes; surfaces, assemblies, model/texture import, GUI branches.')
    finally:
        if app:
            app.close()
        glfw.make_context_current, glfw.swap_interval = old_current, old_swap_interval
        glfw.terminate()
        EGL.eglMakeCurrent(display, EGL.EGL_NO_SURFACE, EGL.EGL_NO_SURFACE, EGL.EGL_NO_CONTEXT)
        EGL.eglDestroyContext(display, context)
        EGL.eglDestroySurface(display, surface)
        EGL.eglTerminate(display)


if __name__ == '__main__':
    main()
