"""ImGui panels plus the existing GLFW/Trackball approach.

The left panel creates objects; the right panel edits the selected object.
Mouse drags started over the canvas control the camera, never the GUI.
"""
from pathlib import Path
import math
import glfw
import imgui
import numpy as np
import OpenGL.GL as GL
from imgui.integrations.glfw import GlfwRenderer
from cglibs.cglibs.viewer import TrackballViewer
from cglibs.cglibs.transform import Trackball, perspective, ortho
from cglibs.cglibs.shading import MODES, FLAT, GOURAUD, PHONG, TEXTURE, WIREFRAME, INTERP
from .geometry import SHAPES_2D, SHAPES_3D, make_shape, surface, import_model
from .scene import SceneObject, Node, shape_object, ELEMENTS, MOLECULES, bohr_atom, molecule
from .rendering import Renderer, Texture, ROOT


def choose_file(kind):
    """Optional native chooser. Path fields remain usable without Tk installed."""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk(); root.withdraw()
    try:
        root.attributes('-topmost', True)
        types = [('3D meshes', '*.obj *.ply')] if kind == 'model' else [('Images', '*.png *.jpg *.jpeg *.bmp *.tif *.tiff')]
        return filedialog.askopenfilename(parent=root, title=f'Choose {kind}', filetypes=types+[('All files', '*.*')])
    finally:
        root.destroy()


class AssignmentApp(TrackballViewer):
    LEFT = 300
    RIGHT = 300

    def __init__(self, visible=True):
        super().__init__(visible=visible)
        glfw.set_window_size_limits(self.win, 1040, 680, glfw.DONT_CARE, glfw.DONT_CARE)
        self.gui_context = imgui.create_context()
        imgui.get_io().ini_file_name = None
        imgui.style_colors_dark()
        style = imgui.get_style(); style.window_rounding = 5; style.frame_rounding = 4
        # We own callbacks and forward the keyboard/scroll events to ImGui.
        self.gui = GlfwRenderer(self.win, attach_callbacks=False)
        glfw.set_char_callback(self.win, self.gui.char_callback)
        self.renderer = Renderer()
        self.objects = []
        self.selected = -1
        self.shape_index = 0
        self.prism_sides = 6
        self.expression = 'sin(x)*cos(y)'
        self.extent = 2.0; self.resolution = 50
        self.model_path = str(ROOT/'assets/sample.obj')
        self.texture_path = str(ROOT/'assets/checker.png')
        self.element_index = 7; self.molecule_index = 0
        self.status = 'Ready. Add a shape, atom or molecule.'
        self.is_error = False
        self.orthographic = False
        self.background = [.055, .070, .095]
        self.drag_button = None
        self.scroll_pending = 0.
        self.previous_buttons = [False, False]
        self.add_object(shape_object('Cube', make_shape('Cube')))

    def attempt(self, action):
        try:
            action()
            self.is_error = False
        except Exception as exc:
            self.status = f'{type(exc).__name__}: {exc}'
            self.is_error = True
            print(self.status)

    @property
    def active(self):
        return self.objects[self.selected] if 0 <= self.selected < len(self.objects) else None

    def add_object(self, obj):
        # Slightly offset added objects to make overlap easier to recognize.
        obj.position[0] = (len(self.objects) % 3)*.7
        self.objects.append(obj)
        self.selected = len(self.objects)-1
        self.status = f'Added {obj.name}. Use the object list to select it.'
        self.focus_selected()

    def remove_selected(self):
        if self.active is None:
            return
        obj = self.objects.pop(self.selected)
        if obj.texture:
            obj.texture.close()
        self.selected = min(self.selected, len(self.objects)-1)
        self.renderer.collect_unused(self.objects)
        self.status = f'Removed {obj.name}.'

    def clear_scene(self):
        for obj in self.objects:
            if obj.texture:
                obj.texture.close()
        self.objects.clear(); self.selected = -1
        self.renderer.collect_unused(self.objects)
        self.status = 'Scene cleared.'

    def focus_selected(self):
        obj = self.active
        self.trackball = Trackball(distance=8)
        self.focus = np.zeros(3)
        if obj:
            points = []
            for node, world in obj.root.walk(obj.matrix(), obj.time):
                # Bounds from transformed vertices also handle nonuniform scaling.
                p = node.mesh.positions @ world[:3, :3].T + world[:3, 3]
                points.extend([p.min(axis=0), p.max(axis=0)])
            if points:
                lo, hi = np.min(points, axis=0), np.max(points, axis=0)
                self.focus = (lo+hi)/2
                radius = max(np.linalg.norm(hi-lo)/2, .2)
                width, height = glfw.get_window_size(self.win)
                aspect = max((width-self.LEFT-self.RIGHT)/max(height-25, 1), .1)
                half_angle = min(math.radians(35)/2, math.atan(math.tan(math.radians(35)/2)*aspect))
                self.trackball.distance = radius/max(math.sin(half_angle), .01)*1.1

    def on_key(self, window, key, scancode, action, mods):
        if not hasattr(self, 'gui'):
            return
        self.gui.keyboard_callback(window, key, scancode, action, mods)
        if imgui.get_io().want_capture_keyboard or action != glfw.PRESS:
            return
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, True)
        elif key == glfw.KEY_HOME:
            self.focus_selected()
        elif key == glfw.KEY_DELETE:
            self.remove_selected()
        elif self.active:
            modes = {glfw.KEY_F: FLAT, glfw.KEY_G: GOURAUD, glfw.KEY_P: PHONG,
                     glfw.KEY_T: TEXTURE, glfw.KEY_W: WIREFRAME, glfw.KEY_I: INTERP}
            if key in modes:
                self.active.mode = modes[key]
            elif key == glfw.KEY_SPACE:
                self.active.animate = not self.active.animate

    def on_mouse_move(self, window, x, y):
        # Read positions once per frame AFTER ImGui has determined input capture.
        pass

    def on_scroll(self, window, dx, dy):
        if hasattr(self, 'gui'):
            self.gui.scroll_callback(window, dx, dy)
            self.scroll_pending += dy

    def canvas_input(self):
        io = imgui.get_io()
        width, height = glfw.get_window_size(self.win)
        x, y = glfw.get_cursor_pos(self.win)
        inside = self.LEFT <= x < width-self.RIGHT and 25 <= y < height
        current = (x-self.LEFT, height-y)
        buttons = [glfw.get_mouse_button(self.win, k) == glfw.PRESS for k in (glfw.MOUSE_BUTTON_LEFT, glfw.MOUSE_BUTTON_RIGHT)]
        for k, down in enumerate(buttons):
            if down and not self.previous_buttons[k] and inside and not io.want_capture_mouse:
                self.drag_button = k
                self.mouse = current
        if self.drag_button is not None:
            if not buttons[self.drag_button]:
                self.drag_button = None
            elif self.mouse is not None and inside and not io.want_capture_mouse:
                if self.drag_button == 0:
                    self.trackball.drag(self.mouse, current, (width-self.LEFT-self.RIGHT, height-25))
                else:
                    self.trackball.pan(self.mouse, current)
        self.mouse = current
        self.previous_buttons = buttons
        if inside and not io.want_capture_mouse and self.scroll_pending:
            self.trackball.distance = float(np.clip(self.trackball.distance*math.exp(-.12*self.scroll_pending), .2, 100000))
        self.scroll_pending = 0.

    def load_model(self):
        parts = import_model(self.model_path)
        name = Path(self.model_path).name
        root = Node(name)
        root.add(*(Node(f'Part {i+1}', mesh) for i, mesh in enumerate(parts)))
        self.add_object(SceneObject(name, root, kind='import'))
        self.status = f'Loaded {name}.'

    def load_texture(self):
        obj = self.active
        if obj is None:
            raise ValueError('Select an object first.')
        texture = Texture(Path(self.texture_path).expanduser())
        if obj.texture:
            obj.texture.close()
        obj.texture = texture; obj.texture_path = self.texture_path; obj.mode = TEXTURE
        self.status = f'Texture loaded on {obj.name}.'

    def browse(self, kind):
        try:
            path = choose_file(kind)
            if path:
                if kind == 'model':
                    self.model_path = path
                else:
                    self.texture_path = path
        except Exception as exc:
            raise RuntimeError('File chooser unavailable. Paste a full path into the text field. '+str(exc)) from exc

    def menu_bar(self):
        if imgui.begin_main_menu_bar():
            if imgui.begin_menu('Scene', True):
                if imgui.menu_item('Clear scene')[0]:
                    self.clear_scene()
                if imgui.menu_item('Focus selected', 'Home')[0]:
                    self.focus_selected()
                if imgui.menu_item('Exit', 'Esc')[0]:
                    glfw.set_window_should_close(self.win, True)
                imgui.end_menu()
            if imgui.begin_menu('View', True):
                clicked, _ = imgui.menu_item('Orthographic projection', None, self.orthographic)
                if clicked:
                    self.orthographic = not self.orthographic
                if imgui.menu_item('Front view')[0]:
                    self.focus_selected()
                imgui.end_menu()
            imgui.text('  CG ASSIGNMENT 1  |  Shapes / Atoms / Molecules')
            imgui.end_main_menu_bar()

    def creation_panel(self):
        width, height = glfw.get_window_size(self.win)
        imgui.set_next_window_position(0, 25)
        imgui.set_next_window_size(self.LEFT, height-25)
        flags = imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_COLLAPSE
        imgui.begin('Create and scene', flags=flags)
        if imgui.collapsing_header('Basic shapes', flags=imgui.TREE_NODE_DEFAULT_OPEN)[0]:
            choices = SHAPES_2D+SHAPES_3D
            _, self.shape_index = imgui.combo('Shape', self.shape_index, choices)
            if choices[self.shape_index] == 'Prism':
                _, self.prism_sides = imgui.slider_int('Sides', self.prism_sides, 3, 12)
            if imgui.button('Add shape', -1, 0):
                self.attempt(lambda: self.add_object(shape_object(choices[self.shape_index], make_shape(choices[self.shape_index], self.prism_sides))))
        if imgui.collapsing_header('Function surface z = f(x,y)')[0]:
            _, self.expression = imgui.input_text('f(x,y)', self.expression, 320)
            _, self.extent = imgui.slider_float('Domain +/-', self.extent, .1, 10)
            _, self.resolution = imgui.slider_int('Grid', self.resolution, 4, 150)
            imgui.text_wrapped('Example: sin(x)*cos(y) or 0.2*(x**2-y**2). Use ** for powers.')
            if imgui.button('Add surface', -1, 0):
                self.attempt(lambda: self.add_object(shape_object('z = '+self.expression, surface(self.expression, self.extent, self.resolution))))
        if imgui.collapsing_header('Import OBJ / PLY')[0]:
            _, self.model_path = imgui.input_text('Model path', self.model_path, 2048)
            if imgui.button('Browse model'):
                self.attempt(lambda: self.browse('model'))
            imgui.same_line()
            if imgui.button('Import'):
                self.attempt(self.load_model)
            imgui.text_wrapped('Models are centered and scaled to fit. Missing UVs use planar projection.')
        if imgui.collapsing_header('Atoms and molecules', flags=imgui.TREE_NODE_DEFAULT_OPEN)[0]:
            _, self.element_index = imgui.combo('Element', self.element_index, [f'{s} - {n}' for n, s, _ in ELEMENTS])
            if imgui.button('Add Bohr atom', -1, 0):
                self.attempt(lambda: self.add_object(bohr_atom(self.element_index)))
            _, self.molecule_index = imgui.combo('Molecule', self.molecule_index, MOLECULES)
            if imgui.button('Add molecule', -1, 0):
                self.attempt(lambda: self.add_object(molecule(MOLECULES[self.molecule_index])))
            imgui.text_wrapped('O = red, H = white, C = dark gray. Teaching models; sizes and motion are illustrative.')
        imgui.separator()
        imgui.text(f'Scene objects ({len(self.objects)})')
        imgui.begin_child('Object list', 0, 135, border=True)
        for i, obj in enumerate(self.objects):
            clicked, _ = imgui.selectable(f'{i+1}. {obj.name}##object{i}', i == self.selected)
            if clicked:
                self.selected = i
        imgui.end_child()
        if imgui.button('Remove selected'):
            self.remove_selected()
        imgui.same_line()
        if imgui.button('Clear all'):
            self.clear_scene()
        imgui.separator()
        imgui.text_colored('Status', *( (1., .45, .4) if self.is_error else (.4, .8, .65)))
        imgui.text_wrapped(self.status)
        imgui.end()

    def inspector_panel(self):
        width, height = glfw.get_window_size(self.win)
        imgui.set_next_window_position(width-self.RIGHT, 25)
        imgui.set_next_window_size(self.RIGHT, height-25)
        flags = imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_COLLAPSE
        imgui.begin('Object and view controls', flags=flags)
        obj = self.active
        if obj:
            imgui.text_wrapped(f'Selected: {obj.name}')
            _, obj.visible = imgui.checkbox('Visible', obj.visible)
            _, obj.mode = imgui.combo('Render mode', obj.mode, MODES)
            _, color = imgui.color_edit3('Object color', *obj.color)
            obj.color = list(color)
            if obj.kind in ('atom', 'molecule'):
                _, obj.preserve_part_colors = imgui.checkbox('Keep element colors', obj.preserve_part_colors)
            _, obj.shininess = imgui.slider_float('Shininess', obj.shininess, 2, 128)
            if imgui.collapsing_header('Transform', flags=imgui.TREE_NODE_DEFAULT_OPEN)[0]:
                _, values = imgui.drag_float3('Position', *obj.position, change_speed=.02)
                obj.position = list(values)
                _, values = imgui.slider_float3('Rotation', *obj.rotation, min_value=-180, max_value=180)
                obj.rotation = list(values)
                _, values = imgui.slider_float3('Scale', *obj.scaling, min_value=.05, max_value=4.)
                obj.scaling = list(values)
                if imgui.button('Reset transform'):
                    obj.position = [0., 0., 0.]; obj.rotation = [0., 0., 0.]; obj.scaling = [1., 1., 1.]
                imgui.same_line()
                if imgui.button('Focus'):
                    self.focus_selected()
            if imgui.collapsing_header('Texture image')[0]:
                _, self.texture_path = imgui.input_text('Image path', self.texture_path, 2048)
                if imgui.button('Browse image'):
                    self.attempt(lambda: self.browse('image'))
                imgui.same_line()
                if imgui.button('Apply texture'):
                    self.attempt(self.load_texture)
                imgui.text_wrapped('Current: '+(obj.texture_path or 'Built-in checker'))
            if obj.kind in ('atom', 'molecule'):
                _, obj.animate = imgui.checkbox('Animate', obj.animate)
                _, obj.speed = imgui.slider_float('Speed', obj.speed, .1, 4.)
                if imgui.button('Reset animation'):
                    obj.time = 0.
                if obj.kind == 'atom':
                    orbit_nodes = [n for shell in obj.root.children for n in shell.children if n.name == 'Orbit guide']
                    if orbit_nodes:
                        changed, show = imgui.checkbox('Show orbital paths', orbit_nodes[0].visible)
                        if changed:
                            for node in orbit_nodes:
                                node.visible = show
            if imgui.collapsing_header('Mesh statistics')[0]:
                nodes = list(obj.root.walk(obj.matrix(), obj.time))
                imgui.text(f'Drawable parts: {len(nodes)}')
                imgui.text(f'Triangles: {sum(len(n.mesh.indices) for n, _ in nodes):,}')
        else:
            imgui.text_wrapped('Add or select an object to edit its properties.')
        imgui.separator()
        if imgui.collapsing_header('Camera and lighting', flags=imgui.TREE_NODE_DEFAULT_OPEN)[0]:
            _, self.orthographic = imgui.checkbox('Orthographic', self.orthographic)
            _, self.renderer.ambient = imgui.slider_float('Ambient', self.renderer.ambient, 0., 1.)
            _, light = imgui.slider_float3('Light XYZ', *self.renderer.light, min_value=-10, max_value=10)
            self.renderer.light = list(light)
            _, background = imgui.color_edit3('Background', *self.background)
            self.background = list(background)
        imgui.separator()
        imgui.text_wrapped('Canvas: left drag = orbit; right drag = pan; wheel = zoom. Transform sliders move the selected object.')
        imgui.text_wrapped('F flat | G Gouraud | P Phong | T texture | W wireframe | I colors')
        imgui.text_wrapped('Home focus | Delete remove | Space animate | Esc quit')
        imgui.end()

    def draw_frame(self, dt):
        self.gui.process_inputs()
        imgui.new_frame()
        self.menu_bar(); self.creation_panel(); self.inspector_panel()
        self.canvas_input()
        for obj in self.objects:
            obj.tick(min(dt, .1))
        fw, fh = glfw.get_framebuffer_size(self.win)
        ww, wh = glfw.get_window_size(self.win)
        if fw == 0 or fh == 0:
            imgui.render()
            return
        GL.glViewport(0, 0, fw, fh)
        GL.glClearColor(*self.background, 1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        sx, sy = fw/max(ww, 1), fh/max(wh, 1)
        canvas_width = max(1, round((ww-self.LEFT-self.RIGHT)*sx))
        canvas_height = max(1, round((wh-25)*sy))
        GL.glViewport(round(self.LEFT*sx), 0, canvas_width, canvas_height)
        aspect = canvas_width/canvas_height
        distance = self.trackball.distance
        near, far = max(.001, distance*.001), max(100., distance*100)
        if self.orthographic:
            half = distance*math.tan(math.radians(35)/2)
            projection = ortho(-half*aspect, half*aspect, -half, half, near, far)
        else:
            projection = perspective(35, aspect, near, far)
        from cglibs.cglibs.transform import translate
        view = self.trackball.view_matrix() @ translate(-self.focus)
        self.renderer.draw(self.objects, projection, view)
        GL.glViewport(0, 0, fw, fh)
        imgui.render()
        self.gui.render(imgui.get_draw_data())

    def run(self, max_frames=0):
        last = glfw.get_time(); frame = 0
        while not glfw.window_should_close(self.win):
            glfw.poll_events()
            now = glfw.get_time()
            self.draw_frame(now-last); last = now
            glfw.swap_buffers(self.win)
            frame += 1
            if max_frames and frame >= max_frames:
                break

    def close(self):
        self.clear_scene()
        self.renderer.close()
        self.gui.shutdown()
        imgui.destroy_context(self.gui_context)
        glfw.destroy_window(self.win)
