"""GLFW window and render loop shared by basicdemo samples."""
from itertools import cycle

import OpenGL.GL as GL
import glfw

from .hud import HelpOverlay, help_text
from .transform import Trackball


class Viewer:
    """GLFW window: OpenGL 3.3 core, drawable list, W wireframe, Q/Esc to quit."""

    def __init__(self, width=640, height=480, title="Viewer",
                 clear_color=(0.5, 0.5, 0.5, 0.1), depth=False):
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL.GL_TRUE)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.RESIZABLE, False)

        self.depth = depth
        self._title = title
        self.win = glfw.create_window(width, height, title, None, None)
        glfw.make_context_current(self.win)
        glfw.set_key_callback(self.win, self.on_key)

        print('OpenGL', GL.glGetString(GL.GL_VERSION).decode() + ', GLSL',
              GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION).decode() +
              ', Renderer', GL.glGetString(GL.GL_RENDERER).decode())

        GL.glClearColor(*clear_color)
        if depth:
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glDepthFunc(GL.GL_LESS)

        self.fill_modes = cycle([GL.GL_LINE, GL.GL_POINT, GL.GL_FILL])
        self._polygon_mode = GL.GL_FILL
        self.drawables = []
        self.show_help = True
        self._hud = None

    def add(self, *drawables):
        self.drawables.extend(drawables)

    def _draw_matrices(self):
        """projection, view, model passed to drawable.draw(); None if unused."""
        return None, None, None

    def _set_window_title(self):
        glfw.set_window_title(self.win, f'{self._title}   [H] help   [Q] quit')

    def _ensure_hud(self):
        if self._hud is None:
            self._hud = HelpOverlay()
        self._hud.refresh(self)

    def run(self):
        self._set_window_title()
        self._ensure_hud()
        print()
        print(help_text(self))
        print('  (Press H to hide or show the on-screen help.)')
        print()

        clear = GL.GL_COLOR_BUFFER_BIT
        if self.depth:
            clear |= GL.GL_DEPTH_BUFFER_BIT
        while not glfw.window_should_close(self.win):
            GL.glClear(clear)
            projection, view, model = self._draw_matrices()
            for drawable in self.drawables:
                drawable.draw(projection, view, model)
            if self.show_help:
                self._ensure_hud()
                self._hud.draw(self.win)
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, self._polygon_mode)
            glfw.swap_buffers(self.win)
            glfw.poll_events()

    def on_key(self, _win, key, _scancode, action, _mods):
        if action != glfw.PRESS and action != glfw.REPEAT:
            return
        if key == glfw.KEY_ESCAPE or key == glfw.KEY_Q:
            glfw.set_window_should_close(self.win, True)
        elif action == glfw.PRESS and key == glfw.KEY_W:
            self._polygon_mode = next(self.fill_modes)
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, self._polygon_mode)
        elif action == glfw.PRESS and key == glfw.KEY_H:
            self.show_help = not self.show_help
        for drawable in self.drawables:
            if hasattr(drawable, 'key_handler'):
                drawable.key_handler(key)
        if self._hud is not None:
            self._hud.refresh(self)


class TrackballViewer(Viewer):
    """Viewer with depth test and trackball camera."""

    def __init__(self, width=800, height=800, title="Viewer",
                 clear_color=(0.5, 0.5, 0.5, 0.1)):
        glfw.window_hint(glfw.DEPTH_BITS, 16)
        glfw.window_hint(glfw.DOUBLEBUFFER, True)
        super().__init__(width, height, title, clear_color, depth=True)

        self.trackball = Trackball()
        self.mouse = (0, 0)
        glfw.set_cursor_pos_callback(self.win, self.on_mouse_move)
        glfw.set_scroll_callback(self.win, self.on_scroll)

    def _draw_matrices(self):
        win_size = glfw.get_window_size(self.win)
        view = self.trackball.view_matrix()
        projection = self.trackball.projection_matrix(win_size)
        return projection, view, None

    def on_mouse_move(self, win, xpos, ypos):
        old = self.mouse
        self.mouse = (xpos, glfw.get_window_size(win)[1] - ypos)
        if glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_LEFT):
            self.trackball.drag(old, self.mouse, glfw.get_window_size(win))
        if glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_RIGHT):
            self.trackball.pan(old, self.mouse)

    def on_scroll(self, win, _deltax, deltay):
        self.trackball.zoom(deltay, glfw.get_window_size(win)[1])
