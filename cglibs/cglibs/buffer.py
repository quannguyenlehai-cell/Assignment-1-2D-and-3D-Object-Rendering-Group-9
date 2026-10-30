"""VAO and uniform helpers, retaining the interfaces of the supplied framework."""
import numpy as np
from PIL import Image
import OpenGL.GL as GL


class VAO:
    def __init__(self):
        self.vao = GL.glGenVertexArrays(1)
        self.vbo = {}; self.ebo = None

    def activate(self):
        GL.glBindVertexArray(self.vao)

    def deactivate(self):
        GL.glBindVertexArray(0)

    def add_vbo(self, location, data, ncomponents=3, dtype=GL.GL_FLOAT,
                normalized=False, stride=0, offset=None):
        self.activate()
        if location in self.vbo:
            GL.glDeleteBuffers(1, [self.vbo.pop(location)])
        data = np.ascontiguousarray(data)
        buffer = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(location, ncomponents, dtype, normalized, stride, offset)
        GL.glEnableVertexAttribArray(location)
        self.vbo[location] = buffer
        self.deactivate()

    def add_ebo(self, indices):
        self.activate()
        if self.ebo is not None:
            GL.glDeleteBuffers(1, [self.ebo])
        indices = np.ascontiguousarray(indices, dtype=np.uint32)
        self.ebo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL.GL_STATIC_DRAW)
        self.deactivate()

    def close(self):
        if self.vbo:
            buffers = list(self.vbo.values())
            GL.glDeleteBuffers(len(buffers), buffers); self.vbo.clear()
        if self.ebo is not None:
            GL.glDeleteBuffers(1, [self.ebo]); self.ebo = None
        if self.vao:
            GL.glDeleteVertexArrays(1, [self.vao]); self.vao = 0


class UManager:
    def __init__(self, shader):
        self.shader = shader
        self.locations = {}
        self.textures = {}

    def location(self, name):
        GL.glUseProgram(self.shader.render_idx)
        if name not in self.locations:
            self.locations[name] = GL.glGetUniformLocation(self.shader.render_idx, name)
        return self.locations[name]

    def upload_uniform_matrix4fv(self, matrix, name, transpose=True):
        GL.glUniformMatrix4fv(self.location(name), 1, transpose, np.asarray(matrix, dtype=np.float32))

    def upload_uniform_matrix3fv(self, matrix, name, transpose=True):
        GL.glUniformMatrix3fv(self.location(name), 1, transpose, np.asarray(matrix, dtype=np.float32))

    def upload_uniform_vector3fv(self, vector, name):
        GL.glUniform3fv(self.location(name), 1, np.asarray(vector, dtype=np.float32))

    def upload_uniform_vector4fv(self, vector, name):
        GL.glUniform4fv(self.location(name), 1, np.asarray(vector, dtype=np.float32))

    def upload_uniform_scalar1f(self, value, name):
        GL.glUniform1f(self.location(name), float(value))

    def upload_uniform_scalar1i(self, value, name):
        GL.glUniform1i(self.location(name), int(value))

    @staticmethod
    def load_texture(filename):
        with Image.open(filename) as image:
            return np.ascontiguousarray(image.convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM))

    def setup_texture(self, sampler_name, image_file):
        image = self.load_texture(image_file)
        unit = len(self.textures)
        texture = GL.glGenTextures(1)
        GL.glActiveTexture(GL.GL_TEXTURE0+unit)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, image.shape[1], image.shape[0],
                        0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, image)
        GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        self.upload_uniform_scalar1i(unit, sampler_name)
        self.textures[unit] = {'id': texture, 'name': sampler_name}

    def close(self):
        if self.textures:
            GL.glDeleteTextures([v['id'] for v in self.textures.values()])
            self.textures.clear()
