from pathlib import Path
import numpy as np
import pytest
from assignment.geometry import (SHAPES_2D, SHAPES_3D, make_shape, surface,
                                 evaluate_surface, import_model, cross2)
from assignment.scene import bond_matrix, bohr_atom, molecule, ELEMENTS

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', SHAPES_2D+SHAPES_3D)
def test_mesh_is_valid_and_normals_face_outward(name):
    m = make_shape(name)
    triangles = m.positions[m.indices]
    normals = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    assert np.all(np.linalg.norm(normals, axis=1) > 1e-9)
    mean_vertex_normals = m.normals[m.indices].mean(axis=1)
    assert np.all(np.einsum('ij,ij->i', normals, mean_vertex_normals) > 0)
    np.testing.assert_allclose(np.linalg.norm(m.normals, axis=1), 1, atol=1e-5)
    assert np.all(m.uvs >= -1e-6) and np.all(m.uvs <= 1+1e-6)


@pytest.mark.parametrize('name', ['Star', 'Arrow'])
def test_concave_polygon_has_correct_area(name):
    m = make_shape(name)
    p = m.positions[:, :2]
    polygon_area = abs(sum(cross2(p[i], p[(i+1)%len(p)]) for i in range(len(p))))/2
    triangles = p[m.indices]
    triangle_area = sum(abs(cross2(t[1]-t[0], t[2]-t[0]))/2 for t in triangles)
    assert triangle_area == pytest.approx(polygon_area)
    assert len(m.indices) == len(p)-2


def test_surface_grid_and_normals():
    m = surface('0.5*(x**2-y**2)', 2., 16)
    assert len(m.positions) == 16*16
    assert len(m.indices) == 2*15*15
    assert np.all(m.normals[:, 2] > 0)
    np.testing.assert_allclose(m.positions[:, 2], .5*(m.positions[:, 0]**2-m.positions[:, 1]**2), atol=1e-6)


@pytest.mark.parametrize('expression', ['0', 'sin(x)*cos(y)', 'sqrt(x**2+y**2)', 'clip(x,-1,1)', 'exp(-x**2)'])
def test_allowed_surface_expressions(expression):
    assert np.isfinite(surface(expression).positions).all()


@pytest.mark.parametrize('expression', [
    "__import__('os').system('echo no')", 'x.__class__', 'x[0]',
    '(lambda: 0)()', '[x for x in y]', '2**1000', '1/0', 'sqrt(-1)', 'x^2',
])
def test_bad_surface_expressions_rejected(expression):
    with pytest.raises((ValueError, SyntaxError, ZeroDivisionError)):
        surface(expression)


@pytest.mark.parametrize('a,b', [((0,0,0),(0,2,0)), ((0,0,0),(0,-2,0)),
                              ((-1,.2,3),(4,-1,2)), ((0,0,0),(0,0,2))])
def test_bond_maps_both_endpoints(a, b):
    m = bond_matrix(a, b)
    np.testing.assert_allclose((m@np.array([0,-.5,0,1]))[:3], a, atol=1e-6)
    np.testing.assert_allclose((m@np.array([0,.5,0,1]))[:3], b, atol=1e-6)
    assert np.linalg.det(m[:3, :3]) > 0


@pytest.mark.parametrize('index', range(len(ELEMENTS)))
def test_bohr_shells_electron_counts_and_animation(index):
    obj = bohr_atom(index)
    shell_counts = ELEMENTS[index][2]
    assert sum(shell_counts) == index+1
    shells = obj.root.children[1:]
    assert len(shells) == len(shell_counts)
    for shell, count in zip(shells, shell_counts):
        assert sum(n.name == 'Electron' for n in shell.children) == count
    before = list(obj.root.walk(time=0))
    after = list(obj.root.walk(time=1))
    assert not np.allclose(before[-1][1], after[-1][1])
    obj.animate = False; obj.tick(1)
    assert obj.time == 0


@pytest.mark.parametrize('name,atoms,bonds', [('H2O',3,2),('CO2',3,4),('CH4',5,4)])
def test_molecule_parts_and_live_bonds(name, atoms, bonds):
    obj = molecule(name)
    assert len(obj.root.children) == atoms+bonds
    assert sum(n.name == 'Bond' for n in obj.root.children) == bonds
    for _, matrix in obj.root.walk(time=1.2):
        assert np.isfinite(matrix).all()
        assert np.linalg.det(matrix[:3, :3]) > 0


@pytest.mark.parametrize('filename', ['sample.obj', 'sample.ply'])
def test_import_fixture(filename):
    parts = import_model(ROOT/'assets'/filename)
    assert len(parts) >= 1
    p = np.concatenate([m.positions for m in parts])
    assert np.max(p)-np.min(p) <= 2.0001
    assert sum(len(m.indices) for m in parts) >= 4


def test_import_scene_bakes_transforms_and_keeps_parts(tmp_path):
    # An OBJ with two groups sharing the same local coordinate convention.
    path = tmp_path/'two.obj'
    path.write_text('o left\nv -3 0 0\nv -2 0 0\nv -3 1 0\nf 1 2 3\n'
                    'o right\nv 2 0 0\nv 3 0 0\nv 3 1 0\nf 4 5 6\n')
    parts = import_model(path)
    assert sum(len(m.indices) for m in parts) == 2
    p = np.concatenate([m.positions for m in parts])
    assert p[:,0].min() == pytest.approx(-1)
    assert p[:,0].max() == pytest.approx(1)
