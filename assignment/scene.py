"""Scene graph, object transforms and teaching-scale atom/molecule assemblies."""
from dataclasses import dataclass, field
import numpy as np
from cglibs.cglibs.transform import identity, translate, rotate, scale
from cglibs.cglibs.shading import PHONG, FLAT
from .geometry import sphere, frustum, torus, MeshData


@dataclass
class Node:
    name: str
    mesh: MeshData = None
    color: tuple = (0.30, 0.66, 0.95)
    local: np.ndarray = field(default_factory=identity)
    children: list = field(default_factory=list)
    update_fn: object = None
    unlit: bool = False
    visible: bool = True

    def add(self, *nodes):
        self.children.extend(nodes)
        return self

    def walk(self, parent=None, time=0.0):
        if not self.visible:
            return
        if self.update_fn is not None:
            self.local = self.update_fn(time)
        world = (identity() if parent is None else parent) @ self.local
        if self.mesh is not None:
            yield self, world
        for child in self.children:
            yield from child.walk(world, time)


@dataclass
class SceneObject:
    name: str
    root: Node
    position: list = field(default_factory=lambda: [0., 0., 0.])
    rotation: list = field(default_factory=lambda: [0., 0., 0.])
    scaling: list = field(default_factory=lambda: [1., 1., 1.])
    mode: int = FLAT
    color: list = field(default_factory=lambda: [0.30, 0.66, 0.95])
    vertex_colors: bool = False
    preserve_part_colors: bool = False
    visible: bool = True
    animate: bool = False
    speed: float = 1.0
    time: float = 0.0
    shininess: float = 40.0
    texture: object = None
    texture_path: str = ''
    kind: str = 'shape'

    def matrix(self):
        # Column-vector convention: local scale, then rotations, then translation.
        rx, ry, rz = self.rotation
        return (translate(self.position) @ rotate((0, 0, 1), rz)
                @ rotate((0, 1, 0), ry) @ rotate((1, 0, 0), rx) @ scale(self.scaling))

    def tick(self, dt):
        if self.animate:
            self.time += dt*self.speed


def shape_object(name, mesh):
    return SceneObject(name, Node(name, mesh))


def bond_matrix(a, b, radius=0.09):
    """Map a unit-height Y-axis cylinder from endpoints (0,-.5,0),(0,.5,0) to a,b."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    d = b-a; length = np.linalg.norm(d)
    if length < 1e-9:
        raise ValueError('A bond needs two distinct endpoints.')
    y = d/length
    helper = np.array((0, 0, 1)) if abs(y[2]) < .95 else np.array((1, 0, 0))
    x = np.cross(y, helper); x /= np.linalg.norm(x)
    z = np.cross(x, y)
    m = identity(); m[:3, :3] = np.column_stack([x*radius, y*length, z*radius])
    m[:3, 3] = (a+b)/2
    return m


ELEMENTS = [
    ('Hydrogen', 'H', (1,)), ('Helium', 'He', (2,)),
    ('Lithium', 'Li', (2, 1)), ('Beryllium', 'Be', (2, 2)),
    ('Boron', 'B', (2, 3)), ('Carbon', 'C', (2, 4)),
    ('Nitrogen', 'N', (2, 5)), ('Oxygen', 'O', (2, 6)),
    ('Fluorine', 'F', (2, 7)), ('Neon', 'Ne', (2, 8)),
    ('Sodium', 'Na', (2, 8, 1)), ('Magnesium', 'Mg', (2, 8, 2)),
    ('Aluminium', 'Al', (2, 8, 3)), ('Silicon', 'Si', (2, 8, 4)),
    ('Phosphorus', 'P', (2, 8, 5)), ('Sulfur', 'S', (2, 8, 6)),
    ('Chlorine', 'Cl', (2, 8, 7)), ('Argon', 'Ar', (2, 8, 8)),
]


def bohr_atom(element_index=7):
    name, symbol, shells = ELEMENTS[element_index]
    ball = sphere(segments=24, rings=12)
    root = Node(name)
    root.add(Node('Nucleus', ball, (0.98, .27, .35), scale(.32)))
    for shell, count in enumerate(shells):
        radius = .95 + shell*.60
        shell_node = Node(f'Shell {shell+1}')
        # Torus starts in XZ; rotate it into XY. All shells are concentric circles.
        shell_node.add(Node('Orbit guide', torus(radius, .009, 96, 6),
                            (.28, .48, .67), rotate((1, 0, 0), 90), unlit=True))
        for electron in range(count):
            phase = 2*np.pi*electron/count
            omega = 1.1/(shell+1)
            def motion(t, r=radius, p=phase, w=omega):
                a = p+w*t
                return translate(r*np.cos(a), r*np.sin(a), 0) @ scale(.085)
            shell_node.add(Node('Electron', ball, (.20, .83, 1), update_fn=motion))
        root.add(shell_node)
    return SceneObject(f'{symbol} atom ({sum(shells)} electrons)', root,
                       preserve_part_colors=True, vertex_colors=False, animate=True, kind='atom')


ATOM_COLORS = {'H': (.94, .96, 1), 'O': (.92, .09, .12), 'C': (.10, .11, .13), 'N': (.16, .35, .95)}
ATOM_RADII = {'H': .25, 'O': .42, 'C': .40, 'N': .40}
MOLECULES = ['H2O', 'CO2', 'CH4']


def molecule(name='H2O'):
    if name == 'H2O':
        half_angle = np.radians(104.5/2)
        dx, dy = 1.1*np.sin(half_angle), 1.1*np.cos(half_angle)
        atoms = [('O', (0, 0, 0)), ('H', (-dx, dy, 0)), ('H', (dx, dy, 0))]
        bonds = [(0, 1, 1), (0, 2, 1)]
    elif name == 'CO2':
        atoms = [('C', (0, 0, 0)), ('O', (-1.35, 0, 0)), ('O', (1.35, 0, 0))]
        bonds = [(0, 1, 2), (0, 2, 2)]
    elif name == 'CH4':
        atoms = [('C', (0, 0, 0))] + [('H', tuple(1.25*np.array(v)/np.sqrt(3)))
                    for v in [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]]
        bonds = [(0, i, 1) for i in range(1, 5)]
    else:
        raise ValueError(f'Unknown molecule: {name}')
    root = Node(name, update_fn=lambda t: rotate((0, 1, 0), 20*t))
    ball = sphere(segments=32, rings=16)
    stick = frustum(1, 1, 1, 20)
    positions = [np.array(p, dtype=float) for _, p in atoms]
    # Symmetric stretch is illustrative animation, not a simulated normal mode.
    def point(i, t):
        return positions[i]*(1+.035*np.sin(3*t))
    for i, (element, _) in enumerate(atoms):
        def motion(t, idx=i, r=ATOM_RADII[element]):
            return translate(point(idx, t)) @ scale(r)
        root.add(Node(f'{element}{i}', ball, ATOM_COLORS[element], update_fn=motion))
    for a, b, order in bonds:
        offsets = [0] if order == 1 else [-.105, .105]
        for offset in offsets:
            def motion(t, i=a, j=b, o=offset):
                # CO2 lies on X; Y offsets make both cylinders in each double bond visible.
                delta = np.array((0, o, 0))
                return bond_matrix(point(i, t)+delta, point(j, t)+delta, .065 if order == 2 else .085)
            root.add(Node('Bond', stick, (.56, .61, .69), update_fn=motion))
    return SceneObject(name, root, preserve_part_colors=True, vertex_colors=False, kind='molecule')
