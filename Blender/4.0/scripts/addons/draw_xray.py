# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# Copyright (C) 2017 JOSECONSCO
# Created by JOSECONSCO
#DONE: Bad orthogonal drawing

bl_info = {"name": "Draw xray",
           "description": "Draw xray mesh",
           "author": "JoseConseco",
           "version": (3, 4),
           "blender": (3, 6, 0),
           "location": "3D View(s) -> Top Bar -> Viewport overlays",
           "warning": "",
           "doc_url": "https://youtu.be/srUthznXDi4",
           "tracker_url": "https://discord.gg/cxZDbqH",
           "category": "3D View"
           }

import bpy
import ctypes
import bmesh
import gpu
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from bpy.app.handlers import persistent
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import numpy as np
#DONE: fix the ortho - kind of done
#DONE: maybe apply shrink wrap as eval mesh-  verts co?
#WONTDO: in multi edited meshes
#DONE: snap to target/offset as bpy.types.Obj property - remake snappint for that
#DONE: fix no bmesh, when opening scene. Maybe disable xray on quit/load?
#DONE: fix blinking mirror mod


BATCH_FACES = None
EDGES_BATCH = None
VERTS_BATCH = None
OBJ_MW = None
OBJ_MW_NP = None
PAUSE_HANDLERS = False #to avoid recursion
LAST_ACTIVE_OBJ = None
CACHED_OPERATOR_ID = ''  # to avoid recursion
FORCE_UPDATE_XRAY = False # not need anymore?
TARGET_BVH_LIST = {}
# shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')


if bpy.app.version < (3, 5, 0):

    vertex_shader = '''
        uniform mat4 viewProjectionMatrix;
        uniform mat4 objMatrixWorld;
        uniform float bias_z;
        uniform vec3 camPos;

        in vec3 pos;
        in vec4 col;
        in vec3 nrm;

        out vec4 outPos;
        out vec4 color;
        out float oDot;
        void main()
        {
            color = col;
            vec4 pos4 = objMatrixWorld * vec4(pos, 1.0f);
            vec4 nrm4 = objMatrixWorld * vec4(nrm, 0.0);
            oDot = dot(normalize(nrm4.xyz), normalize(camPos-pos4.xyz));
            outPos = viewProjectionMatrix * pos4;
            outPos.z = outPos.z - bias_z/outPos.z; // counter w division for shift
            gl_Position = outPos;
        }
    '''

    fragment_shader = '''
        in vec4 color;
        in float oDot;
        out vec4 fragColor;
        void main()
        {
            vec4 out_color;
            if (oDot>0.0)
            {
                out_color = vec4(color.xyz * (0.3 + 0.7*oDot), color.w);
            }
            else
            {
                out_color = vec4(color.xyz * (0.7*oDot), 0.0);
            }
            fragColor = out_color;
        }
    '''

    shader = gpu.types.GPUShader(vertex_shader, fragment_shader)

else: # use new gpu for blender 3.5 and above

    # Shader that will offset faces more toward cam
    #############################################

    vert_out = gpu.types.GPUStageInterfaceInfo("my_draw_xray")
    vert_out.smooth('VEC4', "outPos")
    vert_out.smooth('VEC4', "color")
    vert_out.smooth('FLOAT', "oDot")

    shader_info = gpu.types.GPUShaderCreateInfo()
    shader_info.typedef_source(
                "struct CData {\n"
                "  mat4 ObjMatrixWorld;\n"
                "};\n"
            )

    shader_info.push_constant('MAT4', "viewProjectionMatrix")
    # shader_info.push_constant('MAT4', "objMatrixWorld") # cant be uniform (push_constant) due to uniform 128 size limit....
    # shader_info.uniform_buf(0, 'MAT4', 'objMatrixWorld')
    shader_info.uniform_buf(0, "CData", "ubo_vars")
    shader_info.push_constant('FLOAT', "bias_z")
    shader_info.push_constant('VEC3', "camPos")


    shader_info.vertex_in(0, 'VEC3', "pos")
    shader_info.vertex_in(1, 'VEC4', "col")
    shader_info.vertex_in(2, 'VEC3', "nrm")
    shader_info.vertex_out(vert_out)
    shader_info.fragment_out(0, 'VEC4', "FragColor")

    shader_info.vertex_source("""
    // uniform mat4 viewProjectionMatrix;
    // uniform mat4 objMatrixWorld;
    // uniform float bias_z;
    // uniform vec3 camPos;

    // in vec3 pos;
    // in vec4 col;
    // in vec3 nrm;

    // vec4 outPos; // XXX: was not out...
    // out vec4 color;
    // out float oDot;

    void main()
    {
        color = col;
        vec4 pos4 = ubo_vars.ObjMatrixWorld * vec4(pos, 1.0f);
        vec4 nrm4 = ubo_vars.ObjMatrixWorld * vec4(nrm, 0.0);
        oDot = dot(normalize(nrm4.xyz), normalize(camPos-pos4.xyz));
        outPos = viewProjectionMatrix * pos4;
        outPos.z = outPos.z - bias_z/outPos.z; // counter w division for shift
        gl_Position = outPos;
    }
    """)

    shader_info.fragment_source("""
    // in vec4 color;
    // in float oDot;
    // out vec4 FragColor;
    void main()
    {
        vec4 out_color;
        if (oDot>0.0)
        {
            out_color = vec4(color.xyz * (0.3 + 0.7*oDot), color.w);
        }
        else
        {
            out_color = vec4(color.xyz * (0.7*oDot), 0.0);
        }
        FragColor = out_color;
    }
    """)


    shader = gpu.shader.create_from_info(shader_info)
    del vert_out
    del shader_info

# end if


# ************************  workaround for uniform 128 size limit in gpu  ****************************************************
# from /mesh_snap_utilities_line/snap_context_l/mesh_drawing.py#L252
class _UBO_struct(ctypes.Structure):
    _pack_ = 16
    _fields_ = [
        ("ObjMatrixWorld", 4 * (4 * ctypes.c_float)),
    ]
UBO_data = _UBO_struct()
UBO = gpu.types.GPUUniformBuf(gpu.types.Buffer("UBYTE", ctypes.sizeof(UBO_data), UBO_data))

# END workaround  ****************************************************


def draw_callback_xray(self, context):
    active_obj = bpy.context.active_object
    if active_obj is None or not bpy.context.space_data.overlay.show_overlays:
        return

    xray_props = context.scene.xray_props
    obj_xprop = active_obj.xray_props
    if xray_props.use_draw_xray == False \
     or (xray_props.settings_mode == 'PER_OBJ' and not obj_xprop.enable_xray):
        return

    if active_obj.type == 'MESH' and active_obj.mode in xray_props.show_in_mode and BATCH_FACES:
        theme = bpy.context.preferences.themes['Default']
        g_vertex_size = theme.view_3d.vertex_size

        # for blender 3.5 and up only
        gpu.state.blend_set("ALPHA") # on=ALPHA # bgl.glEnable(bgl.GL_BLEND)
        gpu.state.line_width_set(3.0) # shader.uniform_float("lineWidth", 3.0)
        gpu.state.point_size_set(g_vertex_size + 1) # bgl.glPointSize(g_vertex_size + 1)
        gpu.state.face_culling_set("BACK") # bgl.glCullFace(bgl.GL_BACK)
        is_perspective = bpy.context.region_data.is_perspective
        if is_perspective:
            gpu.state.depth_test_set("LESS") # bgl.glEnable(bgl.GL_DEPTH_TEST)
        else: #hack cos I duno how fix bias in ortho
            gpu.state.depth_test_set("NONE") # bgl.glDisable(bgl.GL_DEPTH_TEST)

        extra_face_offset = 0.0
        if is_perspective:
            camera_pos = bpy.context.region_data.view_matrix.inverted().translation
            offset = xray_props.drawOffset/50
            extra_face_offset = offset / 10
        else:
            # cam_dir_z = Vector((view_mat[2][0], view_mat[2][1], view_mat[2][2]))
            qat = context.region_data.view_rotation
            cam_dir_z = qat @ Vector((0, 0, 1))  # rotate Z vector by quat
            camera_pos = cam_dir_z * 100
            offset = 0.0

        shader.bind()
        shader.uniform_float("viewProjectionMatrix", context.region_data.perspective_matrix)
        # shader.uniform_float("objMatrixWorld", OBJ_MW) # complains: not enough mem in 128 uniform limit. Consider using UBO

        shader.uniform_block("ubo_vars", UBO)

        # mw_buff = gpu.types.GPUUniformBuf(np.array(active_obj.matrix_world, dtype=np.float32).tobytes())
        # shader.uniform_block("objMatrixWorld", mw_buff) # complains: not enough mem in 128 uniform limit. Consider using UBO)
        shader.uniform_float("bias_z", offset if extra_face_offset == 0.0 else offset - extra_face_offset) # hack replaces GL_POLYGON_OFFSET_FILL
        shader.uniform_float("camPos", camera_pos)
        # with gpu.matrix.push_pop():
            # gpu.matrix.multiply_matrix(active_obj.matrix_world) # why it wont affect the shader?

        BATCH_FACES.draw(shader)

        shader.uniform_float("bias_z", offset) # case for faces and verts
        EDGES_BATCH.draw(shader)
        if bpy.context.tool_settings.mesh_select_mode[0]:
            VERTS_BATCH.draw(shader)
        # restore opengl defaults

        gpu.state.depth_test_set("NONE") # bgl.glDisable(bgl.GL_DEPTH_TEST)
        gpu.state.face_culling_set("NONE") # XXX: bgl.glDisable(bgl.GL_CULL_FACE)
        gpu.state.blend_set("NONE") # bgl.glDisable(bgl.GL_BLEND)
        # bgl.glPolygonMode(bgl.GL_FRONT_AND_BACK, bgl.GL_FILL)
        gpu.state.line_width_set(1.0) # shader.uniform_float("lineWidth", 3.0)
        gpu.state.point_size_set(1) # bgl.glPointSize(1)


def get_obj_mesh_bvht(obj, depsgraph, applyModifiers=True, world_space=True):
    # print(f'Updating BVHTree for {obj.name}')
    if applyModifiers:
        if world_space:
            # #? wont work eg with shrink wrap mod, but fast....
            # obj.data.transform(obj.matrix_world)
            # depsgraph.update() #fixes bad transformation baing applied to obj
            # bvh = BVHTree.FromObject(obj, depsgraph)  #? not required to get with mod: obj.evaluated_get(depsgraph)
            # obj.data.transform(obj.matrix_world.inverted())
            # return bvh

            #* better but slower - even 5-10 times (0.05 sec), wont work on non meshes (curves?)
            obj_eval = obj.evaluated_get(depsgraph)
            bm = bmesh.new()   # create an empty BMesh
            bm.from_mesh(obj_eval.to_mesh())   # with modifiers
            active_obj_mw = bpy.context.active_object.matrix_world # bring it into active obj (retopo obj) space...
            bm.transform(active_obj_mw.inverted() @ obj.matrix_world)
            bm.normal_update()
            bvh = BVHTree.FromBMesh(bm)  # ? not required to get with mod: obj.evaluated_get(depsgraph)
            bm.free()  # free and prevent further access
            obj_eval.to_mesh_clear()
            return bvh
        else:
            return BVHTree.FromObject(obj, depsgraph) #with modes
    else:
        if world_space:
            # 4 times slower than data.transform
            #bvh1 =  BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices], [p.vertices for p in obj.data.polygons])
            #bmesh - same time as data.transform
            obj.data.transform(obj.matrix_world)
            bvh = BVHTree.FromPolygons([v.co for v in obj.data.vertices], [p.vertices for p in obj.data.polygons])
            obj.data.transform(obj.matrix_world.inverted())
            return bvh
        else:
            return BVHTree.FromPolygons([v.co for v in obj.data.vertices], [p.vertices for p in obj.data.polygons])


class ScnDrawXrayProps(bpy.types.PropertyGroup):
    def DrawXrayUpdate(self,context):
        # if context.active_object and \
        #     (self.use_draw_xray == False \
        #     or (self.settings_mode == 'GLOBAL' and not context.scene.xray_props.enable_snapping)
        #     or (self.settings_mode == 'PER_OBJ' and not context.active_object.xray_props.enable_snapping)):
        #     apply_shrink_final()
        global PAUSE_HANDLERS
        PAUSE_HANDLERS = False
        handle_handlers_draw_xray()
        refresh_draw_buffers()
        if context.active_object and context.active_object.type == 'MESH':
            context.active_object.data.update_tag()

    def refresh_buff(self,context):
        refresh_draw_buffers()
        context.active_object.data.update_tag()


    def toggle_snapping(self,context):
        if self.snap_target and self.snap_target.type != 'MESH':
            self['snap_target'] = None
        if not self.enable_snapping:
            apply_shrink_final()
        # global FORCE_UPDATE_XRAY
        # FORCE_UPDATE_XRAY = True
        # check_obj_updated()
        context.active_object.data.update_tag()


    use_draw_xray: bpy.props.BoolProperty(name='Draw Xray', description='Draw Overlay On top of lowpoly object.\nComes with optional snapping feature (onliy in paid ver)' ,update=DrawXrayUpdate)
    settings_mode: bpy.props.EnumProperty(name='Settings Mode', description='Settings Mode',
                                          items=[('GLOBAL', 'Use Global Settings', 'Global Settings'), ('PER_OBJ', 'Unique (per object)', 'Unique Snap Settings for each unique Object')], default='GLOBAL')

    drawOffset: bpy.props.FloatProperty(name="Depth Bias", description="Moves rendering of mesh closer to camera (does not affect mesh geometry)",
                                        min=0.0001, soft_max=1.0, default=0.2, subtype='FACTOR', update=refresh_buff)
    polygon_opacity: bpy.props.FloatProperty(name="Face opacity", description="Face opacity", min=0.0, max=1.0, default=0.5, subtype='PERCENTAGE', update=refresh_buff)
    edgeOpacity: bpy.props.FloatProperty(name="Edge opacity", description="Edge opacity", min=0.0, max=1.0, default=0.5, subtype='PERCENTAGE', update=refresh_buff)
    face_color:  bpy.props.FloatVectorProperty(name="Face Color", subtype='COLOR', default=(0.1, 0.8, 0.0), min=0.0, max=1.0, description="color picker", update=refresh_buff)
    highlight_color:  bpy.props.FloatVectorProperty(name="Highlight Color", subtype='COLOR', default=(1.0, 0.8, 0.0), min=0.0, max=1.0, description="color picker", update=refresh_buff)

    draw_modifiers: bpy.props.BoolProperty(name="Draw Modifiers", description="Draws retopo mesh with modifiers", default=True, update=refresh_buff)
    enable_snapping: bpy.props.BoolProperty(name="Enable snapping", description="Enable global snapping, for all objects on scene", default=False, update=toggle_snapping)
    snap_offset: bpy.props.FloatProperty( name="Snap offset", description="Offset retopo mesh vertices above high-poly mesh surface.", default=0.01, soft_min=0.0, soft_max=0.1, update=toggle_snapping)
    snap_target: bpy.props.PointerProperty(name='Snap Target', description="Default snap target object for all objects.", type=bpy.types.Object, update=toggle_snapping)

    snap_event: bpy.props.EnumProperty(name='Snap Event', description='Snap Mode',
                                       items=[('ALL', 'Geometry update & Selection Change', 'Always snap geometry (including geo select events)'),
                                              ('GEO_UPDATE', 'Only on Geometry Update', 'Snap only on geometry update')], default='GEO_UPDATE')

    wrap_method: bpy.props.EnumProperty(name="Mode", description="Shrink wrap Mode", default="NEAREST_SURFACEPOINT",
                                              items=[('NEAREST_SURFACEPOINT', 'Nearest Surface point', ''),
                                                     ('PROJECT', 'Project', ''),
                                                     ('NEAREST_VERTEX', 'Nearest Vertex', ''),
                                                     ('TARGET_PROJECT', 'Target Normal Project', '')
                                                     ], update=toggle_snapping)
    wrap_mode: bpy.props.EnumProperty(name='Wrap Mode', description='Wrap Mode',
        items=[('ON_SURFACE', 'On Surface', 'On Surface'),
            ('INSIDE', 'Inside', 'Inside'),
            ('OUTSIDE', 'Outside', 'Outside'),
            ('OUTSIDE_SURFACE', 'Outside Surface', 'Outside Surface'),
            ('ABOVE_SURFACE', 'Above surface', 'Above_surface')],
        default='OUTSIDE_SURFACE', update=toggle_snapping)

    show_in_mode: bpy.props.EnumProperty(name='Show in Mode', description='Show in Mode',
                                         items=[('EDIT', 'Edit Mode', 'Edit Mode'),
                                                ('SCULPT', 'Sculpt Mode', 'Sculpt Mode'),
                                                ('PAINT', 'Paint Mode', 'Paint Mode'),
                                                ('OBJECT', 'Object Mode', 'Object Mode')]
                                                , options={'ENUM_FLAG'}, default={'EDIT'})


class ObjDrawXrayProps(bpy.types.PropertyGroup):
    def refresh_buff(self, context):
        refresh_draw_buffers()
        context.active_object.data.update_tag()

    def toggle_snapping(self, context):
        if self.snap_target and (self.snap_target.type != 'MESH' or self.snap_target == context.active_object):
            self['snap_target'] = None

        # global FORCE_UPDATE_XRAY
        # FORCE_UPDATE_XRAY = True
        # check_obj_updated()
        context.active_object.data.update_tag()

    enable_xray: bpy.props.BoolProperty(name='Draw Overlay', default=True)
    draw_modifiers: bpy.props.BoolProperty(name="Draw Modifiers", description="Draws retopo mesh with modifiers", default=True, update=refresh_buff)
    enable_snapping: bpy.props.BoolProperty(name="Enable snapping", description="Enable global snapping, for all objects on scene", default=False, update=toggle_snapping)
    snap_offset: bpy.props.FloatProperty( name="Snap offset", description="Offset retopo mesh vertices above high-poly mesh surface", default=0.01, soft_min=0.0, soft_max=0.1, update=toggle_snapping)
    snap_target: bpy.props.PointerProperty(name='Snap Target', description="Snap target mesh", type=bpy.types.Object, update=toggle_snapping)

    # NOTE: obsolete (only cuold be used for sculpt mode)?
    wrap_method: bpy.props.EnumProperty(name="Mode", description="Shrink wrap Mode", default="NEAREST_SURFACEPOINT",
                                        items=[('NEAREST_SURFACEPOINT', 'Nearest Surface point', ''),
                                               ('PROJECT', 'Project', ''),
                                               ('NEAREST_VERTEX', 'Nearest Vertex', ''),
                                               ('TARGET_PROJECT', 'Target Normal Project', '')
                                               ])
    wrap_mode: bpy.props.EnumProperty(name='Wrap Mode', description='Wrap Mode',
                                      items=[('ON_SURFACE', 'On Surface', 'On Surface'),
                                             ('INSIDE', 'Inside', 'Inside'),
                                             ('OUTSIDE', 'Outside', 'Outside'),
                                             ('OUTSIDE_SURFACE', 'Outside Surface', 'Outside Surface'),
                                             ('ABOVE_SURFACE', 'Above surface', 'Above_surface')],
                                      default='ABOVE_SURFACE')



def ShadingXrayPanel(self, context):
    if context.active_object and context.active_object.type == 'MESH':
        xray_props = context.scene.xray_props
        obj_xprop = context.active_object.xray_props

        box = self.layout.box()
        main_col = box.column()
        row = main_col.row(align=True)
        row.prop(xray_props, "use_draw_xray", icon='XRAY')
        if xray_props.use_draw_xray == True:
            row.prop(xray_props, "draw_modifiers", icon="MODIFIER", icon_only = True)

        if xray_props.use_draw_xray:
            col = main_col.column(align=True)
            row = col.row(align=True)
            row.prop(xray_props, "show_in_mode", expand=True)
            row = col.row(align=True)
            row.prop(xray_props, "settings_mode", expand=True)
            #* Overlay Drawing  Settings
            sub_box = main_col.box()
            sub_col = sub_box.column()
            if xray_props.settings_mode == 'PER_OBJ':
                row = sub_col.row(align=True)
                row.prop(obj_xprop, "enable_xray", icon='MOD_SOLIDIFY')
                row.prop(obj_xprop, "draw_modifiers", icon="MODIFIER", icon_only=True)

            row = sub_col.row(align=True)
            row.prop(xray_props, "drawOffset")
            row = sub_col.row(align=True)
            row.prop(xray_props, "polygon_opacity")
            row.prop(xray_props, "edgeOpacity")
            row = sub_col.row(align=True)
            row.label(text="Faces color")
            row.prop(xray_props, "face_color", text='')
            row = sub_col.row(align=True)
            row.label(text="Highlight color")
            row.prop(xray_props, "highlight_color", text='')

            # Snapping
            snap_props = xray_props if xray_props.settings_mode == 'GLOBAL' else obj_xprop
            sub_box = main_col.box()
            sub_col = sub_box.column()
            sub_box.enabled = False # False for version without snap
            # sub_col.label(text='Snapping supported only in paid version')
            sub_col.prop(snap_props, "enable_snapping", icon='SNAP_ON' if snap_props.enable_snapping else 'SNAP_OFF')
            col = sub_box.column()
            col.active = snap_props.enable_snapping
            row = col.row(align=True)
            row.prop_search(snap_props, "snap_target", context.scene, "objects")
            picker_op = row.operator(XRAY_OT_ObjectPicker.bl_idname, icon='EYEDROPPER', text='')
            picker_op.use_scn_prop = xray_props.settings_mode == 'GLOBAL'
            col.prop(snap_props, "snap_offset")
            row = col.row(align=True)
            row.prop(xray_props, "snap_event", icon='UNLOCKED' if xray_props.snap_event == 'ALL' else 'LOCKED')




class XRAY_OT_ObjectPicker(bpy.types.Operator):
    bl_idname = "xray.object_picker"
    bl_label = "Pick Object"
    bl_description = 'Pick Object under the cursor'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    use_scn_prop: bpy.props.BoolProperty(name='Scene prop', description='Pick scn.snap_target prop or obj.snap_target', default=True)

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        self.lmb_clicked = True
        self.obj = None
        context.window.cursor_modal_set('EYEDROPPER')
        context.window_manager.modal_handler_add(self)
        self.depsgraph = context.evaluated_depsgraph_get()
        return {"RUNNING_MODAL"}

    def scn_ray_cast(self, context, event):
        ''' using scn.ray_cast '''
        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        # hit, loc, norm, idx, obj, mat = context.scene.ray_cast(context.view_layer, ray_origin, view_vector, distance=1.0e+6) #old
        hit, loc, norm, idx, obj, mat = context.scene.ray_cast(self.depsgraph, ray_origin, view_vector, distance=1.0e+6)
        return obj

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.obj = self.scn_ray_cast(context, event)
            context.area.header_text_set(self.obj.name if self.obj else None)

        elif event.type == "MIDDLEMOUSE":
            return {'PASS_THROUGH'}

        elif event.type == "LEFTMOUSE":
            if self.obj and self.obj.type == 'MESH':
                if self.use_scn_prop:
                    context.scene.xray_props.snap_target = self.obj
                else:
                    context.active_object.xray_props.snap_target = self.obj
                self.report({'INFO'}, f'Picked {self.obj.name}')
            else:
                self.report({'WARNING'}, 'Pick mesh type of object')
            context.window.cursor_modal_restore()
            context.area.header_text_set(None)
            return {"FINISHED"}

        elif event.type in {"RIGHTMOUSE", "ESC"}:
            context.window.cursor_modal_restore()
            context.area.header_text_set(None)
            return {"CANCELLED"}

        return {"RUNNING_MODAL"}


handle_SpaceView3D = None

@persistent
def xray_scene_update(scene, depsgraph):
    check_obj_updated(depsgraph)


@persistent
def DrawXrayPost(scn):
    handle_handlers_draw_xray()

@persistent
def DrawXrayLoadDisable(scn):
    #print('Disabling xray on load handerl')
    bpy.context.scene.xray_props['enable_snapping'] = False  #
    bpy.context.scene.xray_props.use_draw_xray = False  # to avoid bm edit error


def handle_handlers_draw_xray():
    global handle_SpaceView3D
    xray_props = bpy.context.scene.xray_props
    if xray_props.use_draw_xray != False:
        if handle_SpaceView3D is None:
            args = (ScnDrawXrayProps, bpy.context)  # u can pass arbitrary class as first param  Instead of (self, context)
            handle_SpaceView3D = bpy.types.SpaceView3D.draw_handler_add(draw_callback_xray, args, 'WINDOW', 'POST_VIEW')

        if xray_scene_update not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(xray_scene_update)
    else:
        if handle_SpaceView3D is not None:
            bpy.types.SpaceView3D.draw_handler_remove(handle_SpaceView3D, 'WINDOW')
            handle_SpaceView3D = None

        if xray_scene_update in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(xray_scene_update)



VERTICES = None
INDICES = None
NORMALS = None

def refresh_draw_buffers(geo_update=True):
    active_obj = bpy.context.active_object
    if not active_obj:
        return
    xray_props = bpy.context.scene.xray_props
    obj_xprop = active_obj.xray_props
    if xray_props.use_draw_xray == False or (xray_props.settings_mode == 'PER_OBJ' and not obj_xprop.enable_xray):
        return
    active_obj.update_from_editmode() #to get correct highlights

    draw_mods = (xray_props.settings_mode == 'GLOBAL' and xray_props.draw_modifiers) or \
                (xray_props.settings_mode == 'PER_OBJ' and obj_xprop.enable_xray and obj_xprop.draw_modifiers)
    # if True:  # Polyquilt  fix but wont work - selection not updated if no modifiers, and  draw_modifiers == True
    if  draw_mods: # includes shapekesy
        depsgraph = bpy.context.evaluated_depsgraph_get() # WARNING: somehow using DEPSGRAPH here, causes blink of modifiers
        # depsgraph.update()  # to get disabled mods/ update selection highlight if draw mods_on,
        obj_eval = active_obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()
    else:
        mesh = active_obj.data

    theme = bpy.context.preferences.themes['Default']

    g_vertex_color = theme.view_3d.vertex
    # g_vertex_size = theme.view_3d.vertex_size
    g_wire_edit_color = theme.view_3d.wire_edit

    g_face_color = xray_props.face_color
    highlight_color = xray_props.highlight_color
    #print('Runinig buffer update')
    mesh.calc_loop_triangles()
    vert_count = len(mesh.vertices)
    global VERTICES, INDICES, NORMALS
    if geo_update:
        VERTICES = np.empty((vert_count, 3), 'f')
        INDICES = np.empty((len(mesh.loop_triangles), 3), 'i')
        NORMALS = np.empty((vert_count, 3), 'f')
        # mesh.transform(active_obj.matrix_world) # XXX: since 3.3 (and 3.2?) this causes len(mesh.vertices) to be 0 :/
        # mesh.update()  #? recalc normals - brokens see above
        mesh.vertices.foreach_get("co", np.reshape(VERTICES, vert_count * 3))
        mesh.vertices.foreach_get("normal", np.reshape(NORMALS, vert_count * 3))
        mesh.loop_triangles.foreach_get("vertices", np.reshape(INDICES, len(mesh.loop_triangles) * 3))


    face_col = [(g_face_color[0], g_face_color[1], g_face_color[2], xray_props.polygon_opacity/2) for _ in range(vert_count)]
    edge_col = [(g_wire_edit_color.r, g_wire_edit_color.g, g_wire_edit_color.b, xray_props.edgeOpacity*0.7) for _ in range(vert_count)]
    vert_opacity = min(xray_props.edgeOpacity+0.2, 1.0)
    vert_col = [(g_vertex_color.r, g_vertex_color.g, g_vertex_color.b, vert_opacity) for _ in range(vert_count)]
    for i,vert in enumerate(mesh.vertices):
        if vert.select:
            edge_col[i] = (highlight_color[0], highlight_color[1], highlight_color[2], xray_props.edgeOpacity*0.7)
            vert_col[i] = (highlight_color[0], highlight_color[1], highlight_color[2], vert_opacity)
            face_col[i] = (highlight_color[0], highlight_color[1], highlight_color[2], xray_props.polygon_opacity/2)

    global BATCH_FACES, EDGES_BATCH, VERTS_BATCH


    ob_mat = active_obj.matrix_world.transposed() # why trans?

    UBO_data.ObjMatrixWorld[0] = ob_mat[0][:]
    UBO_data.ObjMatrixWorld[1] = ob_mat[1][:]
    UBO_data.ObjMatrixWorld[2] = ob_mat[2][:]
    UBO_data.ObjMatrixWorld[3] = ob_mat[3][:]
    UBO.update(gpu.types.Buffer( "UBYTE", ctypes.sizeof(UBO_data), UBO_data))


    # mw_array = np.array(active_obj.matrix_world, 'f').transpose()  # into 4x4 matrix
    # # duplicate mw_array * vert_count times
    # mw_array = np.tile(mw_array,(vert_count,1)).reshape([-1,16]) # into vert_count*[*16]   # reshape([-1,4,4])   into  4x4 matrix
    # # OBJ_MW_NP = mw_array


    BATCH_FACES = batch_for_shader(shader, 'TRIS', {"pos": VERTICES, "col": face_col, 'nrm': NORMALS}, indices=INDICES,)
    EDGES_BATCH = batch_for_shader(shader, 'LINES', {"pos": VERTICES, "col": edge_col, 'nrm': NORMALS}, indices=mesh.edge_keys)
    VERTS_BATCH = batch_for_shader(shader, 'POINTS', {"pos": VERTICES, "col": vert_col, 'nrm': NORMALS})

    if draw_mods and len(active_obj.modifiers) > 0:
        obj_eval.to_mesh_clear()
    # else:
    #     mesh.transform(active_obj.matrix_world.inverted())



def check_obj_updated(depsgraph):
    active_obj = bpy.context.active_object
    if not active_obj:
        return
    global PAUSE_HANDLERS, FORCE_UPDATE_XRAY, TARGET_BVH_LIST, LAST_ACTIVE_OBJ
    if PAUSE_HANDLERS:
        return
    PAUSE_HANDLERS = True
    xray_props = bpy.context.scene.xray_props

    if xray_props.use_draw_xray:
        # TAB -  (fires geo_update, and tranfsorm_update)  - clear bvh cache, update later
        if bpy.context.mode == 'OBJECT' and TARGET_BVH_LIST: # when obj moved in OBJECT mode, we reset whole cache for all objs (since its calculated in active obj space - which chaged now)
            if hasattr(depsgraph, 'updates'):
                for update in depsgraph.updates:
                    # print((f'ID {update.id}, geom {update.is_updated_geometry}, transform: {update.is_updated_transform}, is_eval: {update.id.is_evaluated}'))
                    if type(update.id) == bpy.types.Object and update.id.type == 'MESH' and (update.is_updated_geometry or update.is_updated_transform):
                        # print('Clear whole cache!')
                        TARGET_BVH_LIST.clear()
                        break

        active_obj = bpy.context.active_object
        if LAST_ACTIVE_OBJ != active_obj.name and active_obj.type == 'MESH':
            LAST_ACTIVE_OBJ = active_obj.name
            refresh_draw_buffers(True)
        if active_obj and active_obj.type == 'MESH' and active_obj.mode in ('EDIT', 'SCULPT'):
            if hasattr(depsgraph, 'updates'):
                for update in depsgraph.updates:
                    # print((f'ID {update.id}, geom {update.is_updated_geometry}, transform: {update.is_updated_transform}, is_eval: {update.id.is_evaluated}'))
                    if update.id.name == active_obj.name:
                        geo_update=update.is_updated_geometry
                        if (update.is_updated_geometry or active_obj.mode == 'SCULPT') or xray_props.snap_event == 'ALL' and active_obj.mode in ('EDIT', 'SCULPT'): # or update.is_updated_transform):
                            write_shrink_using_bm(depsgraph)
                            geo_update = True
                        refresh_draw_buffers(geo_update) # out of if - to update on selection chagne
                        PAUSE_HANDLERS = False
                        return
    PAUSE_HANDLERS = False

def apply_shrink_final():
    return
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        return
    snap_mod = [mod for mod in obj.modifiers if mod.name == 'shrink_xray']
    if snap_mod:
        back_mode = obj.mode
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.modifier_apply(modifier=snap_mod[0].name)
        if back_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=back_mode)


def write_shrink_using_bm(depsgraph):
    # Determine if the modifier needs to be applied.
    context = bpy.context
    xray_props = context.scene.xray_props

    active_object = context.active_object
    xray_props_obj = active_object.xray_props
    if (xray_props.settings_mode == 'GLOBAL' and not xray_props.enable_snapping) or \
        (xray_props.settings_mode == 'PER_OBJ' and not xray_props_obj.enable_snapping):
        return

    target = None
    if xray_props.settings_mode == 'GLOBAL':  # use global snapping is local snapping is disabbled
        if xray_props.snap_target and  context.scene.objects.get(xray_props.snap_target.name) and xray_props.snap_target.name != active_object.name:
            target = xray_props.snap_target
            offset = xray_props.snap_offset
    elif xray_props.settings_mode == 'PER_OBJ': # use local obj snapping first if exist
        if xray_props_obj.snap_target and context.scene.objects.get(xray_props_obj.snap_target.name) and xray_props_obj.snap_target.name != active_object.name:
            target = xray_props_obj.snap_target
            offset = xray_props_obj.snap_offset

    if not target:  # no snapping was defined so just skip
        return

    # TODO: update in deps update loop?
    global TARGET_BVH_LIST
    target_bvh = TARGET_BVH_LIST.get(target.name)
    if not target_bvh:
        if not target_bvh:
            print('target_bvh not found. Updating')
        else:
            print('Targed was tagged for update. Updating')
        target_bvh = get_obj_mesh_bvht(target, depsgraph, applyModifiers=True, world_space=True)
        TARGET_BVH_LIST[target.name] = target_bvh

    #shrink wrap moves center verts slightly off center. Deal with it below
    mirror_mod = [mod for mod in active_object.modifiers if mod.type == 'MIRROR' and mod.mirror_object == None and mod.use_axis[0]]
    offset_norm = offset / active_object.scale.length
    if active_object.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(active_object.data)
        sel_verts = [v for v in bm.verts if v.select]
        if mirror_mod:
            for b_vert in sel_verts:
                snap_co, normal, idx, dist = target_bvh.find_nearest(b_vert.co)
                b_vert.co = snap_co + normal * offset_norm # scale by active obj.scale ?
                if abs(b_vert.co.x) < 2*mirror_mod[0].merge_threshold: #snap to center
                    b_vert.co.x = 0
        else:
            for b_vert in sel_verts:
                snap_co, normal, idx, dist = target_bvh.find_nearest(b_vert.co)
                b_vert.co = snap_co + normal * offset_norm
        bmesh.update_edit_mesh(active_object.data)
    elif active_object.mode == 'SCULPT':
        print("SCULPT MODE Xray snapping not implied")
        pass
        # mod_verts_np = np.empty((len(active_object.data.vertices), 3), 'f')
        # mesh_with_mod.vertices.foreach_get("co", np.reshape(mod_verts_np, len(mesh_with_mod.vertices) * 3))
        # if mirror_mod:
        #     mod = mirror_mod[0]
        #     mod_verts_np[np.abs(mod_verts_np[:, 0]) < 2*mod.merge_threshold, 0] = 0
        # active_object.data.vertices.foreach_set('co', mod_verts_np.ravel())
        # active_object.data.update()

def shrink_transfer_old(active_obj):
    '''Old way - using shrinkwrap modifier'''
    #transfer 'shrink_xray' mod to bm verts
    disabled_mods = []
    # print('Disabling mods')
    for mod in active_obj.modifiers:
        if mod.name != 'shrink_xray' and mod.show_viewport:
            mod.show_viewport = False
            disabled_mods.append(mod)

    # depsgraph = bpy.context.evaluated_depsgraph_get() #to force addon to see disabled mods
    # depsgraph = DEPSGRAPH
    depsgraph.update() #to get disabled mods
    obj_eval = active_obj.evaluated_get(depsgraph)
    active_obj.update_from_editmode()
    mesh_with_mod = obj_eval.to_mesh()

    if active_obj.mode == 'EDIT': #when adding geo, use bm, to get updated vertcount
        bm = bmesh.from_edit_mesh(active_obj.data)
        edit_v_count = len(bm.verts)
    else:
        edit_v_count = len(active_obj.data.vertices)

    if len(mesh_with_mod.vertices) != edit_v_count:
        #print(f'Eval mesh has different vert count. Eval count is: {len(mesh_with_mod.vertices)},  mesh coutn is: {edit_v_count}')
        obj_eval.to_mesh_clear()
        # print('enabling mods')
        for mod in disabled_mods:
            mod.show_viewport = True
        return

    #shrink wrap moves center verts slightly off center. Deal with it below
    mirror_mod = [mod for mod in active_obj.modifiers if mod.type == 'MIRROR' and mod.mirror_object == None and mod.use_axis[0]]
    if active_obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(active_obj.data)
        if mirror_mod:
            for b_vert, eval_v in zip(bm.verts, mesh_with_mod.vertices):
                b_vert.co = eval_v.co
                if abs(eval_v.co.x) < 2*mirror_mod[0].merge_threshold: #snap to center
                    b_vert.co.x = 0
        else:
            for b_vert, eval_v in zip(bm.verts, mesh_with_mod.vertices):
                b_vert.co = eval_v.co
        bmesh.update_edit_mesh(active_obj.data)
    elif active_obj.mode == 'SCULPT':
        mod_verts_np = np.empty((len(active_obj.data.vertices), 3), 'f')
        mesh_with_mod.vertices.foreach_get("co", np.reshape(mod_verts_np, len(mesh_with_mod.vertices) * 3))
        if mirror_mod:
            mod = mirror_mod[0]
            mod_verts_np[np.abs(mod_verts_np[:, 0]) < 2*mod.merge_threshold, 0] = 0
        active_obj.data.vertices.foreach_set('co', mod_verts_np.ravel())
        active_obj.data.update()

    obj_eval.to_mesh_clear()
    # print('enabling mods')
    for mod in disabled_mods:
        mod.show_viewport = True

def write_shrink_mod_old():
    '''Old modifier way - kind of cool for sculpt mode support...'''
    # Determine if the modifier needs to be applied.
    xray_props = bpy.context.scene.xray_props

    bm = bmesh.from_edit_mesh(bpy.context.active_object.data)
    sel_verts = [v for v in bm.verts if v.select]
    print(sel_verts)

    active_object = bpy.context.active_object
    obj_xray_props = active_object.xray_props
    if xray_props.use_draw_xray == False \
        or (xray_props.settings_mode == 'GLOBAL' and not xray_props.enable_snapping)  \
        or (xray_props.settings_mode == 'PER_OBJ' and not obj_xray_props.enable_snapping):
        apply_shrink_final()  # if exist apply shrink
        return
    current_oper = hash(bpy.context.active_operator)
    global CACHED_OPERATOR_ID
    #print(f'Currrent oper: {current_oper}')
    #print(f'cached oper as id: {CACHED_OPERATOR_ID}')
    if (current_oper and current_oper != CACHED_OPERATOR_ID) or FORCE_UPDATE_XRAY:
        CACHED_OPERATOR_ID = current_oper
        #print('write shrink mod to mesh')
        target = None
        if xray_props.settings_mode == 'GLOBAL':  # use global snapping is local snapping is disabbled
            if xray_props.snap_target and xray_props.snap_target.name in bpy.context.scene.objects.keys() and xray_props.snap_target.name != active_object.name:
                target = xray_props.snap_target
                offset = xray_props.snap_offset
                wrap_mode = xray_props.wrap_mode
                wrap_method = xray_props.wrap_method

        elif xray_props.settings_mode == 'PER_OBJ':
            # use local obj snapping first if exist
            if obj_xray_props.snap_target and obj_xray_props.snap_target.name in bpy.context.scene.objects.keys() and obj_xray_props.snap_target.name != active_object.name:
                target = obj_xray_props.snap_target
                offset = obj_xray_props.snap_offset
                wrap_mode = obj_xray_props.wrap_mode
                wrap_method = obj_xray_props.wrap_method

        if not target:  # no snapping was defined so just skip
            apply_shrink_final()  # if exist apply shrink
            return

        snap_mod = [mod for mod in active_object.modifiers if mod.name == 'shrink_xray']
        if not snap_mod:
            wrap_method = wrap_method
            modifier = active_object.modifiers.new(name="shrink_xray", type='SHRINKWRAP')
            modifier.show_expanded = False
            modifier.show_viewport = True
            modifier.show_in_editmode = True
            modifier.show_on_cage = True
            modifier.use_negative_direction = True
            modifier.wrap_method = wrap_method
            modifier.wrap_mode = wrap_mode
            modifier.use_negative_direction = True
            modifier.use_positive_direction = True

            while active_object.modifiers[0] != modifier:
                bpy.ops.object.modifier_move_up(modifier=modifier.name)
        else:
            modifier = snap_mod[0]
        if target != modifier.target:
            modifier.target = target
        if offset != modifier.offset:
            modifier.offset = offset

        shrink_transfer_old(active_object) #below will crash so this
        # modifier_apply - crashes it seems
        # back_mode = active_object.mode
        # bpy.ops.object.mode_set(mode='OBJECT')
        # bpy.ops.object.modifier_apply(modifier=modifier.name)
        # bpy.ops.object.mode_set(mode=back_mode)
        # global DEPSGRAPH
        # DEPSGRAPH = bpy.context.evaluated_depsgraph_get()
        # refresh_draw_buffers()



def register():
    bpy.utils.register_class(ScnDrawXrayProps)
    bpy.utils.register_class(XRAY_OT_ObjectPicker)
    bpy.utils.register_class(ObjDrawXrayProps)
    bpy.types.Scene.xray_props = bpy.props.PointerProperty(type=ScnDrawXrayProps)
    bpy.types.Object.xray_props = bpy.props.PointerProperty(type=ObjDrawXrayProps)
    bpy.types.VIEW3D_PT_overlay.append(ShadingXrayPanel)
    bpy.app.handlers.load_post.append(DrawXrayLoadDisable)



def unregister():
    global handle_SpaceView3D
    bpy.types.VIEW3D_PT_overlay.remove(ShadingXrayPanel)
    if handle_SpaceView3D is not None:
        bpy.types.SpaceView3D.draw_handler_remove(handle_SpaceView3D, 'WINDOW')
        handle_SpaceView3D = None

    if xray_scene_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(xray_scene_update)

    bpy.app.handlers.load_post.remove(DrawXrayLoadDisable)

    #line below trigger prop.update=DrawXrayUpdate from xray_props property group
    bpy.context.scene.xray_props.use_draw_xray = False  #! TO hide draw xray on F8 reload - place alway after removing halders (or crash)
    del bpy.types.Scene.xray_props
    del bpy.types.Object.xray_props
    bpy.utils.unregister_class(ScnDrawXrayProps)
    bpy.utils.unregister_class(XRAY_OT_ObjectPicker)
    bpy.utils.unregister_class(ObjDrawXrayProps)


if __name__ == "__main__":
    register()
