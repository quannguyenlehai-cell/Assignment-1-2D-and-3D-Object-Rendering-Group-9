"""Shared shading-mode names and F/G/P/I (optional T/E) key handling."""
import glfw
import os

from .shader import Shader
from .buffer import UManager

def shading_files(shader_dir="./shaders"):
    """Map F/G/P/I names to (vert, frag) paths under ``shader_dir``."""
    return {
        'flat':    (os.path.join(shader_dir, "flat.vert"),    os.path.join(shader_dir, "flat.frag")),
        'gouraud': (os.path.join(shader_dir, "gouraud.vert"), os.path.join(shader_dir, "gouraud.frag")),
        'phong':   (os.path.join(shader_dir, "phong.vert"),   os.path.join(shader_dir, "phong.frag")),
        'interp':  (os.path.join(shader_dir, "interp.vert"),  os.path.join(shader_dir, "interp.frag")),
    }

def load_fgpi(programs, src_py):
    """Compile F/G/P/I from ``src_py``'s ``shaders/`` folder."""
    py_file = os.path.join(os.path.dirname(os.path.abspath(src_py)), "shaders")
    for name, (vs, fs) in shading_files(py_file).items():
        shader = Shader(vs, fs)
        programs[name] = (shader, UManager(shader))

def load_shape_programs(programs, src_py):
    """F/G/P/I from ``src_py``, plus shared Blinn and textured Phong."""
    load_fgpi(programs, src_py)

SHADING_FILES = {
    'flat':    ("./shaders/flat.vert",    "./shaders/flat.frag"),
    'gouraud': ("./shaders/gouraud.vert", "./shaders/gouraud.frag"),
    'phong':   ("./shaders/phong.vert",   "./shaders/phong.frag"),
    'interp':  ("./shaders/interp.vert",  "./shaders/interp.frag"),
}

_LABELS = {
    'flat':    "FLAT",
    'gouraud': "GOURAUD",
    'phong':   "PHONG",
    'interp':  "INTERP (vertex color)",
    'texture': "TEXTURE",
    'edge':    "EDGE",
}


def handle_shading_key(obj, key):
    mapping = {
        glfw.KEY_F: 'flat',
        glfw.KEY_G: 'gouraud',
        glfw.KEY_P: 'phong',
        glfw.KEY_I: 'interp',
        glfw.KEY_T: 'texture',
        glfw.KEY_E: 'edge',
    }
    name = mapping.get(key)
    if name is None or name not in getattr(obj, 'programs', {}):
        return
    obj.shading = name
    print("Shading:", _LABELS.get(name, name.upper()))
