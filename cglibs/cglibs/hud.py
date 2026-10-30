"""On-screen key legend for Viewer (Pillow texture + NDC quad)."""
import ctypes
import os

import numpy as np
import OpenGL.GL as GL
from PIL import Image, ImageDraw, ImageFont

from .shader import Shader

_VERT = """#version 330 core
layout(location = 0) in vec2 position;
layout(location = 1) in vec2 texcoord;
out vec2 v_uv;
void main() {
    v_uv = texcoord;
    gl_Position = vec4(position, 0.0, 1.0);
}
"""

_FRAG = """#version 330 core
in vec2 v_uv;
uniform sampler2D hud;
out vec4 out_color;
void main() {
    out_color = texture(hud, v_uv);
}
"""

_SHADING_KEYS = (
    ('F', 'Flat shading', 'flat'),
    ('G', 'Gouraud shading', 'gouraud'),
    ('P', 'Phong shading', 'phong'),
    ('I', 'Vertex color', 'interp'),
    ('T', 'Texture', 'texture'),
    ('E', 'Edges', 'edge'),
)

_FONT_CANDIDATES = (
    '/System/Library/Fonts/Supplemental/Courier New Bold.ttf',
    '/System/Library/Fonts/Supplemental/Courier New.ttf',
    '/Library/Fonts/Courier New.ttf',
    'C:\\Windows\\Fonts\\consola.ttf',
    'C:\\Windows\\Fonts\\courbd.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
)


def _font(size):
    for path in _FONT_CANDIDATES:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def help_rows(viewer):
    """Build (key, description, highlight) rows for the current drawables."""
    programs = {}
    shading = None
    has_side_switch = False
    for drawable in viewer.drawables:
        programs.update(getattr(drawable, 'programs', {}) or {})
        shading = getattr(drawable, 'shading', shading)
        if hasattr(drawable, 'selected_texture'):
            has_side_switch = True

    rows = []
    if shading:
        rows.append(('', f'Now: {shading.upper()}', True))
        rows.append(('', '', False))

    rows.append(('', 'Keys', False))
    for key, label, mode in _SHADING_KEYS:
        if mode in programs:
            rows.append((key, label, shading == mode))
    rows.append(('W', 'Wire / points / fill', False))
    if has_side_switch:
        rows.append(('1 / 2', 'Switch side image', False))
    rows.append(('H', 'Hide / show this help', False))
    rows.append(('Q', 'Quit', False))

    if getattr(viewer, 'depth', False):
        rows.append(('', '', False))
        rows.append(('', 'Mouse', False))
        rows.append(('Drag', 'Rotate', False))
        rows.append(('Scroll', 'Zoom', False))
        rows.append(('Right-drag', 'Pan', False))
    return rows


def help_text(viewer):
    lines = []
    for key, label, _on in help_rows(viewer):
        if not key and not label:
            lines.append('')
        elif not key:
            lines.append(label)
        else:
            lines.append(f'{key:<10} {label}')
    return '\n'.join(lines)


class HelpOverlay:
    """Textured panel in the top-left corner. Uses texture unit 7."""

    _UNIT = 7

    def __init__(self):
        self.shader = Shader(_VERT, _FRAG)
        self.tex = GL.glGenTextures(1)
        self.size = (1, 1)
        self._signature = None
        self.vao = GL.glGenVertexArrays(1)
        self.vbo = GL.glGenBuffers(1)
        GL.glBindVertexArray(self.vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, 4 * 4 * 4, None, GL.GL_DYNAMIC_DRAW)
        GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, False, 16, None)
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(1, 2, GL.GL_FLOAT, False, 16, ctypes.c_void_p(8))
        GL.glEnableVertexAttribArray(1)
        GL.glBindVertexArray(0)
        GL.glUseProgram(self.shader.render_idx)
        loc = GL.glGetUniformLocation(self.shader.render_idx, 'hud')
        GL.glUniform1i(loc, self._UNIT)

    def refresh(self, viewer):
        rows = help_rows(viewer)
        signature = tuple(rows)
        if signature == self._signature:
            return
        self._signature = signature
        self._upload_image(_render_panel(rows))

    def _upload_image(self, img):
        h, w = img.shape[:2]
        self.size = (w, h)
        GL.glActiveTexture(GL.GL_TEXTURE0 + self._UNIT)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.tex)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, w, h, 0,
                        GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)

    def draw(self, win):
        import glfw
        fw, fh = glfw.get_framebuffer_size(win)
        pw, ph = self.size
        margin = 14 * (fw / max(glfw.get_window_size(win)[0], 1))
        x0 = -1.0 + 2.0 * margin / fw
        y1 = 1.0 - 2.0 * margin / fh
        x1 = x0 + 2.0 * pw / fw
        y0 = y1 - 2.0 * ph / fh
        # NDC: v=0 is the first texture row = top of the PIL image
        quad = np.array([
            [x0, y1, 0.0, 0.0],
            [x0, y0, 0.0, 1.0],
            [x1, y1, 1.0, 0.0],
            [x1, y0, 1.0, 1.0],
        ], dtype=np.float32)

        depth = GL.glIsEnabled(GL.GL_DEPTH_TEST)
        blend = GL.glIsEnabled(GL.GL_BLEND)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

        GL.glUseProgram(self.shader.render_idx)
        GL.glActiveTexture(GL.GL_TEXTURE0 + self._UNIT)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.tex)
        GL.glBindVertexArray(self.vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glBufferSubData(GL.GL_ARRAY_BUFFER, 0, quad)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
        GL.glBindVertexArray(0)

        if depth:
            GL.glEnable(GL.GL_DEPTH_TEST)
        if not blend:
            GL.glDisable(GL.GL_BLEND)
        GL.glActiveTexture(GL.GL_TEXTURE0)


def _render_panel(rows):
    font = _font(16)
    header = _font(16)
    pad_x, pad_y, gap = 14, 12, 4
    dummy = Image.new('RGBA', (8, 8))
    draw = ImageDraw.Draw(dummy)

    texts = []
    max_w = 0
    line_h = 0
    for key, label, _on in rows:
        if not key and not label:
            texts.append('')
            continue
        text = label if not key else f'{key:<10} {label}'
        texts.append(text)
        bbox = draw.textbbox((0, 0), text, font=font)
        max_w = max(max_w, bbox[2] - bbox[0])
        line_h = max(line_h, bbox[3] - bbox[1])
    line_h = max(line_h + gap, 20)
    width = max(max_w + 2 * pad_x, 220)
    height = pad_y * 2 + line_h * max(len(texts), 1)

    img = Image.new('RGBA', (int(width), int(height)), (12, 12, 16, 185))
    draw = ImageDraw.Draw(img)
    y = pad_y
    for (key, label, on), text in zip(rows, texts):
        if text == '':
            y += line_h // 2
            continue
        color = (255, 210, 70, 255) if on or not key else (240, 240, 240, 255)
        if on and key:
            color = (90, 220, 255, 255)
        use = header if (not key and label) else font
        draw.text((pad_x, y), text, font=use, fill=color)
        y += line_h
    return np.ascontiguousarray(np.array(img, dtype=np.uint8))
