"""Adapted GLFW viewer. AssignmentApp subclasses TrackballViewer to add ImGui."""
import glfw
import OpenGL.GL as GL
from .transform import Trackball


class Viewer:
    def __init__(self, width=1280, height=800, title='CG Assignment 1',
                 clear_color=(0.055, 0.070, 0.095, 1), depth=True, visible=True):
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL.GL_TRUE)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.RESIZABLE, True)
        glfw.window_hint(glfw.VISIBLE, visible)
        self.win = glfw.create_window(width, height, title, None, None)
        if not self.win:
            raise RuntimeError('Could not create an OpenGL 3.3 window. Check your GPU driver.')
        glfw.make_context_current(self.win)
        glfw.swap_interval(1)
        self.depth = depth
        self.clear_color = clear_color
        self.drawables = []
        glfw.set_key_callback(self.win, self.on_key)
        print('OpenGL:', GL.glGetString(GL.GL_VERSION).decode())

    def add(self, *drawables):
        self.drawables.extend(drawables)

    def on_key(self, window, key, scancode, action, mods):
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            glfw.set_window_should_close(window, True)


class TrackballViewer(Viewer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trackball = Trackball(distance=8)
        self.mouse = None
        glfw.set_cursor_pos_callback(self.win, self.on_mouse_move)
        glfw.set_scroll_callback(self.win, self.on_scroll)

    def on_mouse_move(self, win, x, y):
        new = (x, glfw.get_window_size(win)[1]-y)
        if self.mouse is not None:
            if glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_LEFT):
                self.trackball.drag(self.mouse, new, glfw.get_window_size(win))
            if glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_RIGHT):
                self.trackball.pan(self.mouse, new)
        self.mouse = new

    def on_scroll(self, win, dx, dy):
        self.trackball.zoom(dy, max(glfw.get_window_size(win)[1], 1))
