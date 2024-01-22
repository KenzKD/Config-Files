import bpy
from mathutils import Vector, Matrix, Quaternion
from math import sin, cos, pi
import gpu
from gpu_extras.batch import batch_for_shader
from gpu_extras.presets import draw_circle_2d
import blf
from . wm import get_last_operators
from . registration import get_prefs, get_addon
from . ui import require_header_offset, get_zoom_factor
from . tools import get_active_tool
from .. colors import red, green, blue, black, white


# UTILS

def get_builtin_shader_name(name, prefix='3D'):
    '''
    see https://projects.blender.org/blender/blender/commit/9a8fd2f1ddb491892297315a4f76b6ed2b0c1b94
    '''
    
    if bpy.app.version >= (4, 0, 0):
        return name
    else:
        return f"{prefix}_{name}"


# BASIC

def draw_point(co, mx=Matrix(), color=(1, 1, 1), size=6, alpha=1, xray=True, modal=True, screen=False):
    def draw():
        shader = gpu.shader.from_builtin(get_builtin_shader_name('UNIFORM_COLOR'))
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.point_size_set(size)

        batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co]})
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_points(coords, indices=None, mx=Matrix(), color=(1, 1, 1), size=6, alpha=1, xray=True, modal=True, screen=False):
    def draw():
        shader = gpu.shader.from_builtin(get_builtin_shader_name('UNIFORM_COLOR'))
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.point_size_set(size)

        if indices:
            if mx != Matrix():
                batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co for co in coords]}, indices=indices)
            else:
                batch = batch_for_shader(shader, 'POINTS', {"pos": coords}, indices=indices)

        else:
            if mx != Matrix():
                batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co for co in coords]})
            else:
                batch = batch_for_shader(shader, 'POINTS', {"pos": coords})

        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_line(coords, indices=None, mx=Matrix(), color=(1, 1, 1), alpha=1, width=1, xray=True, modal=True, screen=False):
    '''
    takes coordinates and draws a single line
    can optionally take an indices argument to specify how it should be drawn
    '''

    def draw():
        nonlocal indices

        if indices is None:
            indices = [(i, i + 1) for i in range(0, len(coords)) if i < len(coords) - 1]
            # TODO: simplify

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_lines(coords, indices=None, mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, xray=True, modal=True, screen=False):
    '''
    takes an even amount of coordinates and draws half as many 2-point lines
    '''

    def draw():
        nonlocal indices

        if not indices:
            indices = [(i, i + 1) for i in range(0, len(coords), 2)]
            # TODO: simplifiy?

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_vector(vector, origin=Vector((0, 0, 0)), mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, fade=False, normal=False, xray=True, modal=True, screen=False):
    '''
    takes a vector and an optional origin and draws a single line representing it, fading from the origin to the tip!
    '''
    
    def draw():

        if normal:
            coords = [mx @ origin, mx @ origin + get_world_space_normal(vector, mx)]
        else:
            coords = [mx @ origin, mx @ origin + mx.to_3x3() @ vector]

        colors = ((*color, alpha), (*color, alpha / 10 if fade else alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": coords, "color": colors})
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_vectors(vectors, origins, mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, fade=False, normal=False, xray=True, modal=True, screen=False):
    '''
    takes a list of vectors and origins and draws a line for each pair, fading from the origin to the tip!
    '''

    def draw():
        coords = []
        colors = []

        for v, o in zip(vectors, origins):
            coords.append(mx @ o)

            if normal:
                coords.append(mx @ o + get_world_space_normal(v, mx))
            else:
                coords.append(mx @ o + mx.to_3x3() @ v)

            colors.extend([(*color, alpha), (*color, alpha / 10 if fade else alpha)])

        indices = [(i, i + 1) for i in range(0, len(coords), 2)]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": coords, "color": colors})
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


# ADVANCED

def draw_circle(loc=Vector(), rot=Quaternion(), radius=100, segments='AUTO', width=1, color=(1, 1, 1), alpha=1, xray=True, modal=True, screen=False):
    '''
    draw a circle
    no need to pass in a rotation if you draw in 2d space of course
    and if you skip in in 3d, then the circle will be simply workd z aligned
    '''

    def draw():
        nonlocal segments

        # simply use the raduis as the segment count, this seems to work remarkably well, ensure a minimum of 16 though
        if segments == 'AUTO':
            segments = max(int(radius), 16)

        # even when passed in, ensure it's at least 16
        else:
            segments = max(segments, 16)

        # create the indices to create a cyclic line
        indices = [(i, i + 1) if i < segments - 1 else (i, 0) for i in range(segments)]

        # get the coords of a circle facing upwards, so all z coords will be 0
        coords = []

        for i in range(segments):

            # get the angle for each segment
            theta = 2 * pi * i / segments

            # then the x and y coords
            x = loc.x + radius * cos(theta)
            y = loc.y + radius * sin(theta)

            # collect the coords
            coords.append(Vector((x, y, 0)))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [rot @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_cross_3d(co, mx=Matrix(), color=(1, 1, 1), width=1, length=1, alpha=1, xray=True, modal=True):
    '''
    draws a 3d cross at passed in location with length
    used to draw a mirror empty (together with a 2d circle)
    '''

    def draw():

        x = Vector((1, 0, 0))
        y = Vector((0, 1, 0))
        z = Vector((0, 0, 1))

        coords = [(co - x) * length, (co + x) * length,
                  (co - y) * length, (co + y) * length,
                  (co - z) * length, (co + z) * length]

        indices = [(0, 1), (2, 3), (4, 5)]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_tris(coords, indices=None, mx=Matrix(), color=(1, 1, 1), alpha=1, xray=True, modal=True):
    ''''
    draw triangles, like those from mesh.calc_loop_triangles
    '''

    def draw():
        # nonlocal indices

        # if not indices:
            # indices = [(i, i + 1) for i in range(0, len(coords), 2)]

        shader = gpu.shader.from_builtin(get_builtin_shader_name('UNIFORM_COLOR'))
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')

        if mx != Matrix():
            batch = batch_for_shader(shader, 'TRIS', {"pos": [mx @ co for co in coords]}, indices=indices)

        else:
            batch = batch_for_shader(shader, 'TRIS', {"pos": coords}, indices=indices)

        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_mesh_wire(batch, color=(1, 1, 1), width=1, alpha=1, xray=True, modal=True):
    '''
    takes tupple of (coords, indices) and draws a line for each edge index
    '''

    def draw():
        nonlocal batch
        coords, indices = batch

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        b = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
        b.draw(shader)

        del shader
        del b

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


def draw_bbox(bbox, mx=Matrix(), color=(1, 1, 1), corners=0, width=1, alpha=1, xray=True, modal=True):
    '''
    draw bbox conrners, useful to highlight objects without drawing the wire
    pass in a corners value > 0 to draw only the corners, not the entire bbox
    '''

    def draw():
        if corners:
            length = corners

            coords = [bbox[0], bbox[0] + (bbox[1] - bbox[0]) * length, bbox[0] + (bbox[3] - bbox[0]) * length, bbox[0] + (bbox[4] - bbox[0]) * length,
                      bbox[1], bbox[1] + (bbox[0] - bbox[1]) * length, bbox[1] + (bbox[2] - bbox[1]) * length, bbox[1] + (bbox[5] - bbox[1]) * length,
                      bbox[2], bbox[2] + (bbox[1] - bbox[2]) * length, bbox[2] + (bbox[3] - bbox[2]) * length, bbox[2] + (bbox[6] - bbox[2]) * length,
                      bbox[3], bbox[3] + (bbox[0] - bbox[3]) * length, bbox[3] + (bbox[2] - bbox[3]) * length, bbox[3] + (bbox[7] - bbox[3]) * length,
                      bbox[4], bbox[4] + (bbox[0] - bbox[4]) * length, bbox[4] + (bbox[5] - bbox[4]) * length, bbox[4] + (bbox[7] - bbox[4]) * length,
                      bbox[5], bbox[5] + (bbox[1] - bbox[5]) * length, bbox[5] + (bbox[4] - bbox[5]) * length, bbox[5] + (bbox[6] - bbox[5]) * length,
                      bbox[6], bbox[6] + (bbox[2] - bbox[6]) * length, bbox[6] + (bbox[5] - bbox[6]) * length, bbox[6] + (bbox[7] - bbox[6]) * length,
                      bbox[7], bbox[7] + (bbox[3] - bbox[7]) * length, bbox[7] + (bbox[4] - bbox[7]) * length, bbox[7] + (bbox[6] - bbox[7]) * length]

            indices = [(0, 1), (0, 2), (0, 3),
                       (4, 5), (4, 6), (4, 7),
                       (8, 9), (8, 10), (8, 11),
                       (12, 13), (12, 14), (12, 15),
                       (16, 17), (16, 18), (16, 19),
                       (20, 21), (20, 22), (20, 23),
                       (24, 25), (24, 26), (24, 27),
                       (28, 29), (28, 30), (28, 31)]


        else:
            coords = bbox
            indices = [(0, 1), (1, 2), (2, 3), (3, 0),
                       (4, 5), (5, 6), (6, 7), (7, 4),
                       (0, 4), (1, 5), (2, 6), (3, 7)]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')


# HUD

def draw_init(self, event):
    self.font_id = 1
    self.offset = 0


def update_HUD_location(self, event, offsetx=20, offsety=20):
    '''
    previously, this was done in draw_init
    however, due to a Blender issue this has some issues when tools are called from keymaps, not from the menu
    see https://blenderartists.org/t/meshmachine/1102529/703
    '''

    # if get_prefs().modal_hud_follow_mouse:
    self.HUD_x = event.mouse_x - self.region_offset_x + offsetx
    self.HUD_y = event.mouse_y - self.region_offset_y + offsety


def draw_label(context, title='', coords=None, offset=0, center=True, size=12, color=(1, 1, 1), alpha=1):

    # with no coords passed in, just center it on the screen
    if not coords:
        region = context.region
        width = region.width / 2
        height = region.height / 2
    else:
        width, height = coords

    scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

    font = 1
    fontsize = int(size * scale)

    blf.size(font, fontsize)
    blf.color(font, *color, alpha)

    if center:
        dims = blf.dimensions(font, title)
        blf.position(font, width - (dims[0] / 2), height - (offset * scale), 1)

    else:
        blf.position(font, width, height - (offset * scale), 1)

    blf.draw(font, title)

    return blf.dimensions(font, title)


# LAYOUT

def draw_split_row(self, layout, prop='prop', text='', label='Label', factor=0.2, align=True, toggle=True, expand=True, info=None, warning=None):
    '''
    draw a split row for addon preferences, where the first split is the prop, and the second is a separate label
    '''

    row = layout.row(align=align)
    split = row.split(factor=factor, align=align)
    
    text = text if text else str(getattr(self, prop)) if getattr(self, prop) in [True, False] else ''
    split.prop(self, prop, text=text, toggle=toggle, expand=expand)

    if label:
        split.label(text=label)

    if info:
        split.label(text=info, icon='INFO')

    if warning:
        split.label(text=warning, icon='ERROR')

    return row


# AXES

hypercursor = None

def draw_axes_HUD(context, objects):
    global hypercursor
    
    if hypercursor is None:
        hypercursor = get_addon('HyperCursor')[0]

    if context.space_data.overlay.show_overlays:
        m3 = context.scene.M3

        size = m3.draw_axes_size
        alpha = m3.draw_axes_alpha

        screenspace = m3.draw_axes_screenspace
        scale = context.preferences.system.ui_scale

        show_cursor = context.space_data.overlay.show_cursor
        show_hyper_cursor = hypercursor and get_active_tool(context).idname in ['machin3.tool_hyper_cursor', 'machin3.tool_hyper_cursor_simple'] and context.scene.HC.show_gizmos

        axes = [(Vector((1, 0, 0)), red), (Vector((0, 1, 0)), green), (Vector((0, 0, 1)), blue)]

        for axis, color in axes:
            coords = []

            # draw object(s)
            for obj in objects:

                # CURSOR

                if obj == 'CURSOR':

                    # only show the cursor axes when the hyper cursor gizmo isn't shown
                    if not show_hyper_cursor:
                        mx = context.scene.cursor.matrix
                        rot = mx.to_quaternion()
                        origin = mx.to_translation()

                        factor = get_zoom_factor(context, origin, scale=300, ignore_obj_scale=True) if screenspace else 1

                        if show_cursor and screenspace:
                            coords.append(origin + (rot @ axis).normalized() * 0.1 * scale * factor * 0.8)
                            coords.append(origin + (rot @ axis).normalized() * 0.1 * scale * factor * 1.2)

                        else:
                            coords.append(origin + (rot @ axis).normalized() * size * scale * factor * 0.9)
                            coords.append(origin + (rot @ axis).normalized() * size * scale * factor)

                            coords.append(origin + (rot @ axis).normalized() * size * scale * factor * 0.1)
                            coords.append(origin + (rot @ axis).normalized() * size * scale * factor * 0.7)

                # OBJECT

                elif str(obj) != '<bpy_struct, Object invalid>':
                    mx = obj.matrix_world
                    rot = mx.to_quaternion()
                    origin = mx.to_translation()

                    factor = get_zoom_factor(context, origin, scale=300, ignore_obj_scale=True) if screenspace else 1

                    coords.append(origin + (rot @ axis).normalized() * size * scale * factor * 0.1)
                    coords.append(origin + (rot @ axis).normalized() * size * scale * factor)

                    """
                    # debuging stash + stashtargtmx for object origin changes
                    for stash in obj.MM.stashes:
                        if s tash.obj:
                            smx = sta sh.obj.MM.stashmx
                            sorigin = smx.decompose()[0]

                            coords.append(sorigin + smx.to_3x3() @ axis * size * 0.1)
                            coords.append(sorigin + smx.to_3x3() @ axis * size)


                            stmx = stash.obj.MM.stashtargetmx
                            storigin = stmx.decompose()[0]

                            coords.append(storigin + stmx.to_3x3() @ axis * size * 0.1)
                            coords.append(storigin + stmx.to_3x3() @ axis * size)
                    """

            if coords:
                indices = [(i, i + 1) for i in range(0, len(coords), 2)]

                gpu.state.depth_test_set('NONE')
                gpu.state.blend_set('ALPHA')

                shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
                shader.uniform_float("color", (*color, alpha))
                shader.uniform_float("lineWidth", 2)
                shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
                shader.bind()

                batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
                batch.draw(shader)


# REGION FRAMES

def draw_focus_HUD(context, color=(1, 1, 1), alpha=1, width=2):
    if context.space_data.overlay.show_overlays:
        region = context.region
        view = context.space_data

        # only draw when actually in local view, this prevents it being drawn when switing workspace, which doesn't sync local view
        if view.local_view:

            # draw border

            coords = [(width, width), (region.width - width, width), (region.width - width, region.height - width), (width, region.height - width)]
            indices =[(0, 1), (1, 2), (2, 3), (3, 0)]

            shader = gpu.shader.from_builtin(get_builtin_shader_name('UNIFORM_COLOR', '2D'))
            shader.bind()
            shader.uniform_float("color", (*color, alpha / 4))

            gpu.state.depth_test_set('NONE')
            gpu.state.blend_set('ALPHA' if (alpha / 4) < 1 else 'NONE')
            gpu.state.line_width_set(width)

            batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
            batch.draw(shader)

            # draw title

            scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale
            offset = 4

            # add additional offset if necessary
            if require_header_offset(context, top=True):
                offset += int(25)

            title = "Focus Level: %d" % len(context.scene.M3.focus_history)

            stashes = True if context.active_object and getattr(context.active_object, 'MM', False) and getattr(context.active_object.MM, 'stashes') else False
            center = (region.width / 2) + (scale * 100) if stashes else region.width / 2

            font = 1
            fontsize = int(12 * scale)

            dims = blf.dimensions(font, title)

            blf.size(font, fontsize)
            blf.color(font, *color, alpha)
            blf.position(font, center - (dims[0] / 2), region.height - offset - fontsize, 0)

            blf.draw(font, title)


def draw_surface_slide_HUD(context, color=(1, 1, 1), alpha=1, width=2):
    if context.space_data.overlay.show_overlays:
        region = context.region

        scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale
        offset = 0

        if require_header_offset(context, top=False):
            offset += int(20)

        title = "Surface Sliding"

        font = 1
        fontsize = int(12 * scale)

        blf.size(font, fontsize)
        blf.color(font, *color, alpha)
        blf.position(font, (region.width / 2) - int(60 * scale), 0 + offset + int(fontsize), 0)

        blf.draw(font, title)


# SCREENCAST

def draw_screen_cast_HUD(context):
    p = get_prefs()
    operators = get_last_operators(context, debug=False)[-p.screencast_operator_count:]

    font = 0
    scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

    # initiate the horizontal offset based on the presence of the tools bar
    tools = [r for r in context.area.regions if r.type == 'TOOLS']
    offset_x = tools[0].width if tools else 0

    # then add some more depending on wether the addon prefix is used
    offset_x += (7 if p.screencast_show_addon else 15) * scale

    # initiate the vertical offset based on the height of the redo panel, use a 50px base offset
    redo = [r for r in context.area.regions if r.type == 'HUD' and r.y]
    bottom_header = [r for r in context.area.regions if r.type == 'HEADER' and r.alignment == 'BOTTOM']
    bottom_tool_header = [r for r in context.area.regions if r.type == 'TOOL_HEADER' and r.alignment == 'BOTTOM']

    offset_y = 20 * scale

    if redo:
        offset_y += redo[0].height

    if bottom_header:
        offset_y += bottom_header[0].height

    if bottom_tool_header:
        offset_y += bottom_tool_header[0].height


    # emphasize the last op
    emphasize = 1.25

    # get addon prefix offset, based on widest possiblestring 'MM', and based on empasized last op's size
    if p.screencast_show_addon:
        blf.size(font, round(p.screencast_fontsize * scale * emphasize))
        addon_offset_x = blf.dimensions(font, 'MM')[0]
    else:
        addon_offset_x = 0

    y = 0
    hgap = 10

    for idx, (addon, label, idname, prop) in enumerate(reversed(operators)):
        size = round(p.screencast_fontsize * scale * (emphasize if idx == 0 else 1))
        vgap = round(size / 2)

        color = green if idname.startswith('machin3.') and p.screencast_highlight_machin3 else white
        alpha = (len(operators) - idx) / len(operators)

        # enable shadowing for the last op and idname
        if idx == 0:
            blf.enable(font, blf.SHADOW)

            blf.shadow_offset(font, 3, -3)
            blf.shadow(font, 5, *black, 1.0)


        # label

        text = f"{label}: {prop}" if prop else label

        x = offset_x + addon_offset_x
        y = offset_y if idx == 0 else y + (blf.dimensions(font, text)[1] + vgap)

        blf.size(font, size)
        blf.color(font, *color, alpha)
        blf.position(font, x, y, 0)

        blf.draw(font, text)


        # idname

        if p.screencast_show_idname:
            x += blf.dimensions(font, text)[0] + hgap

            blf.size(font, size - 2)
            blf.color(font, *color, alpha * 0.3)
            blf.position(font, x, y, 0)

            blf.draw(font, f"{idname}")

            # reset size
            blf.size(font, size)


        # diable shadowing, we don't want to use it for the addon prefix or for the other ops
        if idx == 0:
            blf.disable(font, blf.SHADOW)


        # addon prefix

        if addon and p.screencast_show_addon:
            blf.size(font, size)

            x = offset_x + addon_offset_x - blf.dimensions(font, addon)[0] - (hgap / 2)

            blf.color(font, *white, alpha * 0.3)
            blf.position(font, x, y, 0)

            blf.draw(font, addon)

        if idx == 0:
            y += blf.dimensions(font, text)[1]
