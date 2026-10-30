"""CPU geometry: indexed triangles with position, color, normal and UV attributes.

All generated meshes are centered near the origin. Y is up for solids; 2D
shapes and z=f(x,y) use the XY plane. No OpenGL calls belong in this module.
"""
from dataclasses import dataclass
import ast
import operator
from pathlib import Path
import numpy as np
import trimesh

def unit(v):
    v = np.asarray(v, dtype=np.float64)
    length = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(length, 1e-12)


def vertex_normals(vertices, faces):
    """Area-weighted average of adjacent triangle normals."""
    n = np.zeros_like(vertices, dtype=np.float64)
    p = vertices[faces]
    face_n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    for k in range(3):
        np.add.at(n, faces[:, k], face_n)
    missing = np.linalg.norm(n, axis=1) < 1e-12
    n[missing] = (0, 0, 1)
    return unit(n)


def planar_uv(vertices):
    """Fallback for imported models without UV: project onto two longest axes."""
    axes = np.argsort(np.ptp(vertices, axis=0))[-2:]
    xy = vertices[:, axes]
    return (xy - xy.min(axis=0)) / np.maximum(np.ptp(xy, axis=0), 1e-9)


@dataclass
class MeshData:
    positions: np.ndarray
    indices: np.ndarray
    normals: np.ndarray = None
    uvs: np.ndarray = None
    colors: np.ndarray = None

    def __post_init__(self):
        self.positions = np.ascontiguousarray(self.positions, dtype=np.float32)
        self.indices = np.ascontiguousarray(self.indices, dtype=np.uint32).reshape(-1, 3)
        p, f = self.positions, self.indices
        if p.ndim != 2 or p.shape[1] != 3 or len(p) < 3 or not len(f):
            raise ValueError('A mesh needs 3D vertices and triangle faces.')
        if not np.isfinite(p).all() or f.max() >= len(p):
            raise ValueError('Invalid vertex or face data.')
        if self.normals is None:
            self.normals = vertex_normals(p, f)
        if self.uvs is None:
            self.uvs = planar_uv(p)
        if self.colors is None:
            self.colors = 0.25 + 0.7 * (p - p.min(axis=0)) / np.maximum(np.ptp(p, axis=0), 1e-8)
        for name, width in [('normals', 3), ('uvs', 2), ('colors', 3)]:
            value = np.ascontiguousarray(getattr(self, name), dtype=np.float32)
            if value.shape != (len(p), width) or not np.isfinite(value).all():
                raise ValueError(f'Invalid {name}.')
            setattr(self, name, value)


def cross2(a, b):
    return a[0] * b[1] - a[1] * b[0]


def triangulate_polygon(points):
    """Ear clipping for a simple concave/convex polygon (star and arrow included)."""
    p = np.asarray(points, dtype=float)
    area2 = sum(cross2(p[i], p[(i + 1) % len(p)]) for i in range(len(p)))
    remaining = list(range(len(p)))
    if area2 < 0:
        remaining.reverse()
    result = []
    while len(remaining) > 3:
        found = False
        for k, b in enumerate(remaining):
            a, c = remaining[k - 1], remaining[(k + 1) % len(remaining)]
            if cross2(p[b] - p[a], p[c] - p[b]) <= 1e-10:
                continue
            def inside(q):
                return (cross2(p[b]-p[a], q-p[a]) >= -1e-10 and
                        cross2(p[c]-p[b], q-p[b]) >= -1e-10 and
                        cross2(p[a]-p[c], q-p[c]) >= -1e-10)
            if any(inside(p[j]) for j in remaining if j not in (a, b, c)):
                continue
            result.append((a, b, c))
            remaining.pop(k)
            found = True
            break
        if not found:
            raise ValueError('Polygon is degenerate or self-intersecting.')
    result.append(tuple(remaining))
    return np.asarray(result, dtype=np.uint32)


def polygon(points):
    p = np.asarray(points, dtype=float)
    xyz = np.column_stack([p, np.zeros(len(p))])
    uv = (p - p.min(axis=0)) / np.maximum(np.ptp(p, axis=0), 1e-8)
    return MeshData(xyz, triangulate_polygon(p), np.tile((0, 0, 1), (len(p), 1)), uv)


def regular_polygon(n, rx=1.0, ry=1.0):
    a = np.linspace(0, 2*np.pi, n, endpoint=False) + np.pi/2
    return polygon(np.column_stack([rx*np.cos(a), ry*np.sin(a)]))


class FaceBuilder:
    """Duplicate vertices at hard edges; each planar face gets its own normal."""
    def __init__(self):
        self.p, self.n, self.uv, self.f = [], [], [], []

    def face(self, points, outward):
        points = np.asarray(points, dtype=float)
        if np.dot(np.cross(points[1]-points[0], points[2]-points[0]), outward) < 0:
            points = points[::-1]
        start = len(self.p)
        self.p.extend(points)
        self.n.extend(np.tile(unit(outward), (len(points), 1)))
        self.uv.extend(planar_uv(points))
        self.f.extend((start, start+i, start+i+1) for i in range(1, len(points)-1))

    def mesh(self):
        return MeshData(self.p, self.f, self.n, self.uv)


def prism(sides=6, radius=1.0, height=1.6):
    a = np.linspace(0, 2*np.pi, sides, endpoint=False)
    lower = np.column_stack([radius*np.cos(a), np.full(sides, -height/2), radius*np.sin(a)])
    upper = lower.copy(); upper[:, 1] = height/2
    b = FaceBuilder()
    b.face(lower, (0, -1, 0)); b.face(upper, (0, 1, 0))
    for i in range(sides):
        j = (i+1) % sides
        b.face([lower[i], upper[i], upper[j], lower[j]],
               (lower[i] + lower[j]) * (1, 0, 1))
    return b.mesh()


def cube():
    b = FaceBuilder()
    for axis in range(3):
        others = [i for i in range(3) if i != axis]
        for sign in (-1, 1):
            points = np.zeros((4, 3)); points[:, axis] = sign
            points[:, others] = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
            normal = np.zeros(3); normal[axis] = sign
            b.face(points, normal)
    return b.mesh()


def tetrahedron():
    p = np.asarray([(1, 1, 1), (-1, -1, 1), (-1, 1, -1), (1, -1, -1)]) / np.sqrt(3)
    b = FaceBuilder()
    for ids in [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]:
        face = p[list(ids)]
        b.face(face, face.mean(axis=0))
    return b.mesh()


def sphere(radius=1.0, segments=48, rings=24):
    p, n, uv, f = [], [], [], []
    for i in range(rings+1):
        phi = np.pi*i/rings
        for j in range(segments+1):
            theta = 2*np.pi*j/segments
            normal = (np.sin(phi)*np.cos(theta), np.cos(phi), np.sin(phi)*np.sin(theta))
            n.append(normal); p.append(np.asarray(normal)*radius); uv.append((j/segments, 1-i/rings))
    stride = segments+1
    for i in range(rings):
        for j in range(segments):
            a = i*stride+j; b = a+stride
            if i > 0:
                f.append((a, a+1, b))
            if i < rings-1:
                f.append((a+1, b+1, b))
    return MeshData(p, f, n, uv)


def frustum(bottom=1.0, top=0.55, height=2.0, segments=48):
    """Cylinder/cone/frustum, smooth side normals and separate flat cap normals."""
    p, n, uv, f = [], [], [], []
    slope = (bottom-top)/height
    for row, radius in enumerate((bottom, top)):
        for j in range(segments+1):
            a = 2*np.pi*j/segments
            p.append((radius*np.cos(a), (row-0.5)*height, radius*np.sin(a)))
            n.append(unit((np.cos(a), slope, np.sin(a))))
            uv.append((j/segments, row))
    stride = segments+1
    for j in range(segments):
        if bottom > 0:
            f.append((j, j+stride, j+1))
        if top > 0:
            f.append((j+1, j+stride, j+stride+1))
    for row, radius in enumerate((bottom, top)):
        if radius <= 0:
            continue
        base = len(p); y = (row-0.5)*height
        p.append((0, y, 0)); n.append((0, 2*row-1, 0)); uv.append((0.5, 0.5))
        for j in range(segments+1):
            a = 2*np.pi*j/segments
            p.append((radius*np.cos(a), y, radius*np.sin(a)))
            n.append((0, 2*row-1, 0)); uv.append((0.5+0.5*np.cos(a), 0.5+0.5*np.sin(a)))
        for j in range(segments):
            f.append((base, base+j+1, base+j+2) if row == 0 else (base, base+j+2, base+j+1))
    return MeshData(p, f, n, uv)


def torus(major=0.85, minor=0.3, segments=64, tube_segments=20):
    p, n, uv, f = [], [], [], []
    for i in range(segments+1):
        u = 2*np.pi*i/segments
        for j in range(tube_segments+1):
            v = 2*np.pi*j/tube_segments
            p.append(((major+minor*np.cos(v))*np.cos(u), minor*np.sin(v),
                      (major+minor*np.cos(v))*np.sin(u)))
            n.append((np.cos(v)*np.cos(u), np.sin(v), np.cos(v)*np.sin(u)))
            uv.append((i/segments, j/tube_segments))
    stride = tube_segments+1
    for i in range(segments):
        for j in range(tube_segments):
            a=i*stride+j; b=a+stride
            f.extend([(a, a+1, b), (a+1, b+1, b)])
    return MeshData(p, f, n, uv)


FUNCTIONS = {name: getattr(np, name) for name in
             ('sin', 'cos', 'tan', 'sqrt', 'exp', 'log', 'abs', 'minimum', 'maximum', 'clip')}
OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
             ast.Div: operator.truediv, ast.Pow: operator.pow}


def evaluate_surface(expression, x, y):
    """Interpret a tiny math AST; never execute Python code from the text field."""
    if len(expression) > 300:
        raise ValueError('Use a function expression shorter than 300 characters.')
    tree = ast.parse(expression, mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 100:
        raise ValueError('Expression is too complex.')
    names = {'x': x, 'y': y, 'pi': np.pi, 'e': np.e}
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = float(node.value)
            if not np.isfinite(value) or abs(value) > 1e6:
                raise ValueError('Numeric constants must be finite and <= 1e6.')
            return value
        if isinstance(node, ast.Name) and node.id in names:
            return names[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and np.any(np.abs(right) > 12):
                raise ValueError('Exponents must be between -12 and 12.')
            return OPERATORS[type(node.op)](left, right)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in FUNCTIONS and not node.keywords and len(node.args) <= 3):
            return FUNCTIONS[node.func.id](*(visit(a) for a in node.args))
        raise ValueError('Use x, y, numbers and allowed math functions only (e.g. sin(x)*cos(y)).')
    try:
        with np.errstate(all='ignore'):
            z = np.broadcast_to(np.asarray(visit(tree.body), dtype=float), x.shape).copy()
    except (TypeError, OverflowError) as exc:
        raise ValueError(f'Invalid expression: {exc}') from exc
    if not np.isfinite(z).all() or np.max(np.abs(z)) > 1e4:
        raise ValueError('Function must be finite on the entire domain, with |z| <= 10000.')
    return z


def surface(expression='sin(x)*cos(y)', extent=2.0, resolution=50):
    if not 4 <= resolution <= 150 or not 0.1 <= extent <= 10:
        raise ValueError('Resolution: 4..150; domain half-width: 0.1..10.')
    axis = np.linspace(-extent, extent, resolution)
    x, y = np.meshgrid(axis, axis)
    z = evaluate_surface(expression, x, y)
    dz_dy, dz_dx = np.gradient(z, axis, axis)
    normals = unit(np.stack([-dz_dx, -dz_dy, np.ones_like(z)], axis=-1)).reshape(-1, 3)
    p = np.stack([x, y, z], axis=-1).reshape(-1, 3)
    uv = np.stack([(x+extent)/(2*extent), (y+extent)/(2*extent)], axis=-1).reshape(-1, 2)
    f = []
    for i in range(resolution-1):
        for j in range(resolution-1):
            a = i*resolution+j; b=a+resolution
            f.extend([(a, a+1, b), (a+1, b+1, b)])
    return MeshData(p, f, normals, uv)


SHAPES_2D = ['Triangle', 'Rectangle', 'Pentagon', 'Hexagon', 'Circle', 'Ellipse', 'Trapezoid', 'Star', 'Arrow']
SHAPES_3D = ['Cube', 'Sphere', 'Cylinder', 'Cone', 'Truncated cone', 'Tetrahedron', 'Torus', 'Prism']


def make_shape(name, prism_sides=6):
    regular = {'Triangle': 3, 'Pentagon': 5, 'Hexagon': 6, 'Circle': 96}
    if name in regular:
        return regular_polygon(regular[name])
    if name == 'Ellipse':
        return regular_polygon(96, 1.25, 0.7)
    if name == 'Rectangle':
        return polygon([(-1, -.65), (1, -.65), (1, .65), (-1, .65)])
    if name == 'Trapezoid':
        return polygon([(-1, -.65), (1, -.65), (.6, .65), (-.6, .65)])
    if name == 'Star':
        a = np.linspace(0, 2*np.pi, 10, endpoint=False)+np.pi/2
        r = np.tile([1, .43], 5)
        return polygon(np.column_stack([r*np.cos(a), r*np.sin(a)]))
    if name == 'Arrow':
        return polygon([(-1, -.3), (.2, -.3), (.2, -.7), (1, 0), (.2, .7), (.2, .3), (-1, .3)])
    factories = {'Cube': cube, 'Sphere': sphere, 'Cylinder': lambda: frustum(top=1),
                 'Cone': lambda: frustum(top=0), 'Truncated cone': frustum,
                 'Tetrahedron': tetrahedron, 'Torus': torus, 'Prism': lambda: prism(prism_sides)}
    if name not in factories:
        raise ValueError(f'Unknown shape: {name}')
    return factories[name]()


def import_model(filename):
    """Load OBJ/PLY, bake scene transforms, retain normals/colors/UV if present.

    Import each mesh as one part so UV/material boundaries are not collapsed.
    All parts are centered/scaled together. Texture image selection is explicit
    in the GUI; source material images are not loaded automatically.
    """

    path = Path(filename).expanduser()
    if path.suffix.lower() not in ('.obj', '.ply'):
        raise ValueError('Choose an .obj or .ply mesh file.')
    if not path.is_file():
        raise FileNotFoundError(str(path))
    scene = trimesh.load(str(path), force='scene', process=False)
    meshes = []
    for node in scene.graph.nodes_geometry:
        transform, key = scene.graph[node]
        mesh = scene.geometry[key]
        if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
            continue
        mesh = mesh.copy(); mesh.apply_transform(transform)
        meshes.append(mesh)
    if not meshes:
        raise ValueError('The file contains no triangle mesh (point clouds are unsupported).')
    if sum(len(m.faces) for m in meshes) > 2_000_000:
        raise ValueError('Use a model with at most 2 million triangles.')
    all_bounds = np.asarray([m.bounds for m in meshes])
    lo, hi = all_bounds[:, 0].min(axis=0), all_bounds[:, 1].max(axis=0)
    center = (lo+hi)/2; factor = 2/max(float(np.max(hi-lo)), 1e-8)
    parts = []
    for mesh in meshes:
        positions = (mesh.vertices-center)*factor
        uv = getattr(mesh.visual, 'uv', None)
        colors = None
        if mesh.visual.kind in ('vertex', 'face'):
            # Expanding face colors prevents their interpolation across hard borders.
            if mesh.visual.kind == 'face':
                pos = positions[mesh.faces].reshape(-1, 3)
                normals = np.repeat(mesh.face_normals, 3, axis=0)
                cols = np.repeat(mesh.visual.face_colors[:, :3]/255, 3, axis=0)
                tex = uv[mesh.faces].reshape(-1, 2) if uv is not None else None
                parts.append(MeshData(pos, np.arange(len(pos)).reshape(-1, 3), normals, tex, cols))
                continue
            colors = mesh.visual.vertex_colors[:, :3]/255
        parts.append(MeshData(positions, mesh.faces, mesh.vertex_normals, uv, colors))
    return parts
