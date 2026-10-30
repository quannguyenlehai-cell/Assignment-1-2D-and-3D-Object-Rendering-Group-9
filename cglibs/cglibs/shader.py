"""Adapted from your Shader: exceptions and explicit cleanup while context exists."""
from pathlib import Path
import OpenGL.GL as GL


class Shader:
    def __init__(self, vertex_source, fragment_source):
        self.render_idx = 0
        compiled = []
        try:
            for source, kind in [(vertex_source, GL.GL_VERTEX_SHADER), (fragment_source, GL.GL_FRAGMENT_SHADER)]:
                if '\n' not in str(source):
                    source = Path(source).read_text(encoding='utf-8')
                shader = GL.glCreateShader(kind); compiled.append(shader)
                GL.glShaderSource(shader, source); GL.glCompileShader(shader)
                if not GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS):
                    raise RuntimeError(GL.glGetShaderInfoLog(shader).decode())
            self.render_idx = GL.glCreateProgram()
            for shader in compiled:
                GL.glAttachShader(self.render_idx, shader)
            GL.glLinkProgram(self.render_idx)
            if not GL.glGetProgramiv(self.render_idx, GL.GL_LINK_STATUS):
                raise RuntimeError(GL.glGetProgramInfoLog(self.render_idx).decode())
        except Exception:
            self.close()
            raise
        finally:
            for shader in compiled:
                GL.glDeleteShader(shader)

    def close(self):
        if self.render_idx:
            GL.glDeleteProgram(self.render_idx)
            self.render_idx = 0
