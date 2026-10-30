"""Upload meshes once, then draw scene-graph nodes with per-object materials."""
from pathlib import Path
import numpy as np
from PIL import Image
import OpenGL.GL as GL
from cglibs.cglibs.shader import Shader
from cglibs.cglibs.buffer import VAO, UManager
from cglibs.cglibs.shading import FLAT, WIREFRAME

ROOT = Path(__file__).resolve().parents[1]


class GPUMesh:
    def __init__(self, data):
        self.source = data  # keep identity alive while cached
        self.vao = VAO()
        for location, values in enumerate([data.positions, data.colors, data.normals, data.uvs]):
            self.vao.add_vbo(location, values, ncomponents=values.shape[1])
        self.vao.add_ebo(data.indices)
        self.count = data.indices.size

    def draw(self):
        self.vao.activate()
        GL.glDrawElements(GL.GL_TRIANGLES, self.count, GL.GL_UNSIGNED_INT, None)
        self.vao.deactivate()

    def close(self):
        self.vao.close()


class Texture:
    def __init__(self, path):
        with Image.open(path) as image:
            if max(image.size) > GL.glGetIntegerv(GL.GL_MAX_TEXTURE_SIZE):
                raise ValueError('Image exceeds this GPU texture size limit.')
            data = np.ascontiguousarray(image.convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM))
        self.id = GL.glGenTextures(1)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.id)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, data.shape[1], data.shape[0], 0,
                        GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, data)
        GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
        for parameter in (GL.GL_TEXTURE_WRAP_S, GL.GL_TEXTURE_WRAP_T):
            GL.glTexParameteri(GL.GL_TEXTURE_2D, parameter, GL.GL_REPEAT)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

    def close(self):
        if self.id:
            GL.glDeleteTextures([self.id]); self.id = 0


class Renderer:
    def __init__(self):
        self.shader = Shader(ROOT/'shaders/scene.vert', ROOT/'shaders/scene.frag')
        self.uniforms = UManager(self.shader)
        self.meshes = {}
        self.default_texture = Texture(ROOT/'assets/checker.png')
        self.ambient = .25
        self.light = [3., 5., 6.]

    def draw(self, objects, projection, view):
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LESS)
        GL.glDisable(GL.GL_CULL_FACE)  # 2D shapes can be viewed from either side
        GL.glDisable(GL.GL_BLEND)
        GL.glUseProgram(self.shader.render_idx)
        u = self.uniforms
        u.upload_uniform_matrix4fv(projection, 'projection')
        u.upload_uniform_matrix4fv(view, 'view')
        light_view = view @ np.array([*self.light, 1.])
        u.upload_uniform_vector3fv(light_view[:3], 'light_position')
        u.upload_uniform_scalar1f(self.ambient, 'ambient_strength')
        u.upload_uniform_scalar1i(0, 'image_texture')
        for obj in objects:
            if not obj.visible:
                continue
            texture = obj.texture or self.default_texture
            GL.glActiveTexture(GL.GL_TEXTURE0)
            GL.glBindTexture(GL.GL_TEXTURE_2D, texture.id)
            for node, world in obj.root.walk(obj.matrix(), obj.time):
                key = id(node.mesh)
                if key not in self.meshes:
                    self.meshes[key] = GPUMesh(node.mesh)
                mode = FLAT if node.unlit and obj.mode != WIREFRAME else obj.mode
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE if mode == WIREFRAME else GL.GL_FILL)
                color = node.color if obj.preserve_part_colors else obj.color
                u.upload_uniform_matrix4fv(world, 'model')
                normal_matrix = np.linalg.inv((view@world)[:3, :3]).T
                u.upload_uniform_matrix3fv(normal_matrix, 'normal_matrix')
                u.upload_uniform_vector3fv(color, 'base_color')
                u.upload_uniform_scalar1i(mode, 'mode')
                u.upload_uniform_scalar1i(obj.vertex_colors and not obj.preserve_part_colors, 'use_vertex_colors')
                u.upload_uniform_scalar1f(obj.shininess, 'shininess')
                self.meshes[key].draw()
        # ImGui must never inherit an object's wireframe mode.
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

    def collect_unused(self, objects):
        def walk(node):
            yield node
            for child in node.children:
                yield from walk(child)
        alive = {id(n.mesh) for obj in objects for n in walk(obj.root) if n.mesh is not None}
        for key in list(self.meshes):
            if key not in alive:
                self.meshes.pop(key).close()

    def close(self):
        for mesh in self.meshes.values():
            mesh.close()
        self.meshes.clear()
        self.default_texture.close()
        self.shader.close()
