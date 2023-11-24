from threading import Lock

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from .shader import ShaderManager

GL_LINES = 0
GL_LINE_STRIP = 1
GL_LINE_LOOP = 2
GL_TRIANGLES = 5
GL_TRIANGLE_FAN = 6
GL_QUADS = 4


def check_version(major, minor, _):
    """
    Check blender version
    """

    if bpy.app.version[0] == major and bpy.app.version[1] == minor:
        return 0
    if bpy.app.version[0] > major:
        return 1
    if bpy.app.version[1] > minor:
        return 1
    return -1


def primitive_mode_is_line(mode):
    return mode in [GL_LINES, GL_LINE_STRIP, GL_LINE_LOOP]


def is_shader_supported(shader_name):
    try:
        gpu.shader.from_builtin(shader_name)
        return True
    except ValueError:
        return False


class InternalData:
    # pylint: disable=W0201
    __inst = None
    __lock = Lock()

    def __init__(self):
        raise NotImplementedError("Not allowed to call constructor")

    @classmethod
    def __internal_new(cls):
        inst = super().__new__(cls)
        inst.color = [1.0, 1.0, 1.0, 1.0]
        inst.line_width = 1.0
        inst.scissor = None

        return inst

    @classmethod
    def get_instance(cls):
        if not cls.__inst:
            with cls.__lock:
                if not cls.__inst:
                    cls.__inst = cls.__internal_new()

        return cls.__inst

    def init(self):
        self.clear()

    def set_prim_mode(self, mode):
        self.prim_mode = mode

    def set_dims(self, dims):
        self.dims = dims

    def add_vert(self, v):
        self.verts.append(v)

    def add_tex_coord(self, uv):
        self.tex_coords.append(uv)

    def set_color(self, c):
        self.color = c

    def set_line_width(self, width):
        self.line_width = width

    def set_tex(self, texture):
        self.tex = texture

    def set_scissor(self, scissor_box):
        self.scissor = scissor_box

    def clear(self):
        self.prim_mode = None
        self.verts = []
        self.dims = None
        self.tex_coords = []

    def get_verts(self):
        return self.verts

    def get_dims(self):
        return self.dims

    def get_prim_mode(self):
        return self.prim_mode

    def get_color(self):
        return self.color

    def get_line_width(self):
        return self.line_width

    def get_tex_coords(self):
        return self.tex_coords

    def get_tex(self):
        return self.tex

    def get_scissor(self):
        return self.scissor


# pylint: disable=C0103
def immLineWidth(width):
    inst = InternalData.get_instance()
    inst.set_line_width(width)


# pylint: disable=C0103
def immColor3f(r, g, b):
    inst = InternalData.get_instance()
    inst.set_color([r, g, b, 1.0])


# pylint: disable=C0103
def immColor4f(r, g, b, a):
    inst = InternalData.get_instance()
    inst.set_color([r, g, b, a])


# pylint: disable=C0103
def immRecti(x0, y0, x1, y1):
    immBegin(GL_QUADS)
    immVertex2f(x0, y0)
    immVertex2f(x0, y1)
    immVertex2f(x1, y1)
    immVertex2f(x1, y0)
    immEnd()


# pylint: disable=C0103
def immBegin(mode):
    inst = InternalData.get_instance()
    inst.init()
    inst.set_prim_mode(mode)


def _get_shader(dims, prim_mode, has_texture, scissor_box):
    # TODO: In future release, use built-in shader instead of custom shader.
    if prim_mode in [GL_LINES, GL_LINE_STRIP, GL_LINE_LOOP]:
        if dims == 2:
            if scissor_box is not None:
                return ShaderManager.get_shader(
                    'POLYLINE_UNIFORM_COLOR_SCISSOR')
            return gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        elif dims == 3:
            if scissor_box is not None:
                return ShaderManager.get_shader(
                    'POLYLINE_UNIFORM_COLOR_SCISSOR')
            else:
                if is_shader_supported('3D_POLYLINE_UNIFORM_COLOR'):
                    return gpu.shader.from_builtin('3D_POLYLINE_UNIFORM_COLOR')
                raise NotImplementedError(
                    "3D polyline is only supported for dims == 3")
        raise NotImplementedError(f"dims == {dims} is not supported")

    if dims == 2:
        if has_texture:
            if scissor_box is not None:
                return ShaderManager.get_shader('IMAGE_COLOR_SCISSOR')
            if hasattr(gpu.platform, "backend_type_get") and \
                    gpu.platform.backend_type_get() != 'OPENGL':
                return gpu.shader.from_builtin('IMAGE_COLOR')
            return ShaderManager.get_shader('IMAGE_COLOR')
        if scissor_box is not None:
            return ShaderManager.get_shader('UNIFORM_COLOR_SCISSOR')
        else:
            return gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    raise NotImplementedError(f"dims == {dims} is not supported")


# pylint: disable=C0103
def immEnd():
    inst = InternalData.get_instance()

    color = inst.get_color()
    coords = inst.get_verts()
    tex_coords = inst.get_tex_coords()
    scissor_box = inst.get_scissor()
    # TODO: Other than OpenGL backend, scissor is not supported.
    #       Temporary turn off when gpu.state.scissor_set is implemented.
    if hasattr(gpu.platform, "backend_type_get") and \
            gpu.platform.backend_type_get() != 'OPENGL':
        scissor_box = None

    has_texture = len(tex_coords) != 0
    prim_mode = inst.get_prim_mode()
    dims = inst.get_dims()

    # Get shader.
    shader = _get_shader(dims, prim_mode, has_texture, scissor_box)

    # Setup attributes.
    if len(tex_coords) == 0:
        data = {
            "pos": coords,
        }
    else:
        data = {
            "pos": coords,
            "texCoord": tex_coords
        }

    # Setup batch.
    if prim_mode == GL_LINES:
        indices = []
        for i in range(0, len(coords), 2):
            indices.append([i, i + 1])
        batch = batch_for_shader(shader, 'LINES', data, indices=indices)
    elif prim_mode == GL_LINE_STRIP:
        batch = batch_for_shader(shader, 'LINE_STRIP', data)
    elif prim_mode == GL_LINE_LOOP:
        data["pos"].append(data["pos"][0])
        batch = batch_for_shader(shader, 'LINE_STRIP', data)
    elif prim_mode == GL_TRIANGLES:
        indices = []
        for i in range(0, len(coords), 3):
            indices.append([i, i + 1, i + 2])
        batch = batch_for_shader(shader, 'TRIS', data, indices=indices)
    elif prim_mode == GL_TRIANGLE_FAN:
        indices = []
        for i in range(1, len(coords) - 1):
            indices.append([0, i, i + 1])
        batch = batch_for_shader(shader, 'TRIS', data, indices=indices)
    elif prim_mode == GL_QUADS:
        indices = []
        for i in range(0, len(coords), 4):
            indices.extend([[i, i + 1, i + 2], [i + 2, i + 3, i]])
        batch = batch_for_shader(shader, 'TRIS', data, indices=indices)
    else:
        raise NotImplementedError(
            f"Not supported primitive mode {prim_mode}")

    # Set parameters for shader.
    shader.bind()
    if prim_mode in [GL_LINES, GL_LINE_STRIP, GL_LINE_LOOP]:
        region = bpy.context.region
        projection_matrix = gpu.matrix.get_projection_matrix()
        model_view_matrix = gpu.matrix.get_model_view_matrix()
        mvp_matrix = projection_matrix @ model_view_matrix
        shader.uniform_float("ModelViewProjectionMatrix", mvp_matrix)
        shader.uniform_float("viewportSize", [region.width, region.height])
        shader.uniform_float("lineWidth", inst.get_line_width())
        shader.uniform_float("color", color)
        if scissor_box is not None:
            shader.uniform_float("scissor", scissor_box)
            shader.uniform_int("lineSmooth", 1)
    else:
        if dims == 2:
            if has_texture:
                shader.uniform_sampler("image", inst.get_tex())
            projection_matrix = gpu.matrix.get_projection_matrix()
            model_view_matrix = gpu.matrix.get_model_view_matrix()
            mvp_matrix = projection_matrix @ model_view_matrix
            shader.uniform_float("ModelViewProjectionMatrix", mvp_matrix)
            shader.uniform_float("color", color)
            if scissor_box is not None:
                shader.uniform_float("scissor", scissor_box)

    # Draw.
    batch.draw(shader)

    del batch
    inst.clear()


# pylint: disable=C0103
def immVertex2f(x, y):
    inst = InternalData.get_instance()
    inst.add_vert([x, y])
    inst.set_dims(2)


# pylint: disable=C0103
def immVertex3f(x, y, z):
    inst = InternalData.get_instance()
    inst.add_vert([x, y, z])
    inst.set_dims(3)


# pylint: disable=C0103
def immTexCoord2f(u, v):
    inst = InternalData.get_instance()
    inst.add_tex_coord([u, v])


# pylint: disable=C0103
def immSetTexture(texture):
    inst = InternalData.get_instance()
    inst.set_tex(texture)


# pylint: disable=C0103
def immSetScissor(scissor_box):
    inst = InternalData.get_instance()
    inst.set_scissor(scissor_box)
