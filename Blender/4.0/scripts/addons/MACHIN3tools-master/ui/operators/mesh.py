import bpy
from bpy.props import IntProperty, BoolProperty, EnumProperty
import bmesh
from math import radians
from ... utils.registration import get_addon
from ... utils.system import printd
from ... utils.bmesh import ensure_custom_data_layers
from ... items import shade_mode_items


hypercursor = None


class Shade(bpy.types.Operator):
    bl_idname = "machin3.shade"
    bl_label = "Shade"
    bl_description = "Set smooth shading in object and edit mode\nALT: Mark edges sharp if face angle > auto smooth angle"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(name="Shade Mode", items=shade_mode_items, default='SMOOTH')

    sharpen: BoolProperty(name="Set Sharps", default=False)
    avoid_sharpen_edge_bevels: BoolProperty(name="Avoid Sharpening HyperCursor's Edge Bevels", description="Avoid Sharpening Edges used for HyperCursor's Edge Bevels", default=True)

    clear: BoolProperty(name="Clear Sharps, BWeights, Creases and Seams", default=False)
    clear_sharps: BoolProperty(name="Clear Sharps, BWeights, Creases and Seams", default=True)
    clear_bweights: BoolProperty(name="Clear BWeights", default=True)
    clear_creases: BoolProperty(name="Clear Creases", default=True)
    clear_seams: BoolProperty(name="Clear Seams", default=True)

    include_children: BoolProperty(name="Include Children", default=False)
    include_boolean_objs: BoolProperty(name="Include Boolean Objects", default=False)

    @classmethod
    def description(cls, context, properties):
        desc = "Shade Smooth" if properties.mode == 'SMOOTH' else 'Smooth Flat'

        if properties.mode == 'SMOOTH':
            desc += "\nALT: Mark MESH object edges sharp if face angle > auto smooth angle"
        elif properties.mode == 'FLAT':
            desc += "\nALT: Clear MESH object sharps, bweights, creases and seams"

        desc += "\nSHIFT: Include Children"
        desc += "\nCTRL: Include Boolean Objects"
        return desc

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return [obj for obj in context.selected_objects if obj.type in ['MESH', 'CURVE']]
        elif context.mode == 'EDIT_MESH':
            return context.active_object

    def draw(self, context):
        global hypercursor

        layout = self.layout
        column = layout.column(align=True)

        if self.mode == 'SMOOTH':
            row = column.row(align=True)
            row.prop(self, 'sharpen', toggle=True)

            if self.sharpen and hypercursor:
                row.prop(self, 'avoid_sharpen_edge_bevels', text="Avoid Edge Bevels", toggle=True)

        elif self.mode == 'FLAT':
            column.prop(self, 'clear', text='Clear' if self.clear else 'Clear Sharps, BWeights, Creases or Seams', toggle=True)

            if self.clear:
                row = column.row(align=True)
                row.prop(self, 'clear_sharps', text='Sharps', toggle=True)
                row.prop(self, 'clear_bweights', text='BWeights', toggle=True)
                row.prop(self, 'clear_creases', text='Creases', toggle=True)
                row.prop(self, 'clear_seams', text='Seams', toggle=True)

        if context.mode == 'OBJECT':
            column.separator()

            row = column.row(align=True)
            row.prop(self, 'include_children', toggle=True)
            row.prop(self, 'include_boolean_objs', toggle=True)

    def invoke(self, context, event):
        if self.mode == 'SMOOTH':
            self.sharpen = event.alt

        elif self.mode == 'FLAT':
            self.clear = event.alt

            active = context.active_object

            if active:
                crease_subds = [mod for mod in active.modifiers if mod.type == 'SUBSURF' and mod.use_creases]

                if self.clear_creases and crease_subds:
                    self.clear_creases = False
                    print("INFO: SubD mod using Creases is present, disabling Crease Removal")

        self.include_boolean_objs = event.ctrl
        self.include_children = event.shift
        return self.execute(context)

    def execute(self, context):
        global hypercursor

        if hypercursor is None:
            hypercursor = get_addon('HyperCursor')[0]

        if context.mode == "OBJECT":
            view = context.space_data
            selected = [(obj, True, obj.data.use_auto_smooth if obj.type == 'MESH' else False) for obj in context.selected_objects if obj.data]

            children = [(ob, ob.visible_get(), ob.data.use_auto_smooth if ob.type == 'MESH' else False) for obj, _, _ in selected for ob in obj.children_recursive if obj.data and ob.name in context.view_layer.objects] if self.include_children else []
            boolean_objs = [(mod.object, mod.object.visible_get(), mod.object.data.use_auto_smooth if mod.object.type == 'MESH' else False) for obj, _, _ in selected for mod in obj.modifiers if mod.type == 'BOOLEAN' and mod.object and mod.object.data and mod.object.name in context.view_layer.objects] if self.include_boolean_objs else []
            more_objects = set(children + boolean_objs)

            # print()
            # print("selected:", [obj.name for obj, _, _ in selected])
            # print("children:", [obj.name for obj, _, _ in children])
            # print("boolean objs:", [obj.name for obj, _, _ in boolean_objs])
            # print("more objs:", [obj.name for obj, _, _ in more_objects])

            # return {'FINISHED'}

            # ensure children/boolean objects are visible and selected
            for obj, state, _ in more_objects:
                
                # ensure the obj is in local view
                if view.local_view and not obj.local_view_get(view):
                    obj.local_view_set(view, True)

                if not state:
                    obj.hide_set(False)
                obj.select_set(True)

            # shade everything smooth
            if self.mode == 'SMOOTH':
                bpy.ops.object.shade_smooth()

                # NOTE: the native smooth op will actually disable auto smooth if it is turned on, but we don't want that, we do this intentionally via ALT flat shading, if we want that
                # ####: so restore auto smooth now
                for obj, _, auto_smooth in selected:
                    if auto_smooth:
                        obj.data.use_auto_smooth = True

                for obj, _, auto_smooth in more_objects:
                    if auto_smooth:
                        obj.data.use_auto_smooth = True

            elif self.mode == 'FLAT':
                bpy.ops.object.shade_flat()

            # restore child/boolean object visibility states
            for obj, state, _ in more_objects:
                obj.hide_set(not state)

            # restore original selection
            bpy.ops.object.select_all(action='DESELECT')
            
            for obj, _, _ in selected:
                obj.select_set(True)

            # set sharps based on face angles + activate auto smooth + enable sharp overlays
            if self.mode == 'SMOOTH' and self.sharpen:
                for obj, _, _ in selected:
                    if obj.type == 'MESH':
                        self.set_sharps(context.mode, obj, hypercursor)

                for obj, _, _ in more_objects:
                    if obj.type == 'MESH':
                        self.set_sharps(context.mode, obj, hypercursor)

                context.space_data.overlay.show_edge_sharp = True

            elif self.mode == 'FLAT' and self.clear:
                for obj, _, _ in selected:
                    if obj.type == 'MESH':
                        self.clear_obj_sharps(obj)

                for obj, _, _ in more_objects:
                    if obj.type == 'MESH':
                        self.clear_obj_sharps(obj)

        elif context.mode == "EDIT_MESH":
            if self.mode == 'SMOOTH':
                if self.set_sharps:
                    self.set_sharps(context.mode, context.active_object, hypercursor)

                    context.space_data.overlay.show_edge_sharp = True
                else:
                    bpy.ops.mesh.faces_shade_smooth()

            elif self.mode == 'FLAT':
                if self.clear:
                    self.clear_mesh_sharps(context.active_object.data)
                else:
                    bpy.ops.mesh.faces_shade_flat()

        return {'FINISHED'}

    def set_sharps(self, mode, obj, hypercursor):
        obj.data.use_auto_smooth = True
        angle = obj.data.auto_smooth_angle

        if mode == 'OBJECT':
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            vglayer = bm.verts.layers.deform.verify()

        elif mode == 'EDIT_MESH':
            bm = bmesh.from_edit_mesh(obj.data)
            vglayer = bm.verts.layers.deform.verify()

            # smooth all faces like in object mode
            for f in bm.faces:
                f.smooth = True

        bm.normal_update()

        if hypercursor and self.avoid_sharpen_edge_bevels:
            edge_bevelled_edges = self.get_edge_bevelled_edges(obj, bm, vglayer)
        else:
            edge_bevelled_edges = []

        # get the edges to be sharpened
        sharpen = [e for e in bm.edges if e.index not in edge_bevelled_edges and len(e.link_faces) == 2 and e.calc_face_angle() > angle]

        for e in sharpen:
            e.smooth = False

        if mode == 'OBJECT':
            bm.to_mesh(obj.data)
            bm.free()

        elif mode == 'EDIT_MESH':
            bmesh.update_edit_mesh(obj.data)

    def get_edge_bevelled_edges(self, obj, bm, vglayer, debug=False):
        '''
        find the edges used in HyperCursor's Edge Bevel vertex groups
        '''
        
        # get all Edge Bevel vgroups as a dict of dicts {index: {'name': 'Name', 'verts': [], 'edges': []}}
        vgroups = {vg.index: {'name': vg.name,
                              'verts': [],
                              'edges': []} for vg in obj.vertex_groups if 'Edge Bevel' in vg.name}

        verts = [v for v in bm.verts]

        # find out what verts are in what group
        for v in verts:
            # print(v.index, v[self.vertex_group_layer].items())

            for vgindex, weight in v[vglayer].items():
                if vgindex in vgroups and weight == 1:
                    vgroups[vgindex]['verts'].append(v.index)

        # create list of all the edges that are used for edge bevels
        edge_bevelled_edges = []

        for e in bm.edges:
            # print(e.index, [v.index for v in e.verts])

            for vgindex, vgdata in vgroups.items():
                if all(v.index in vgdata['verts'] for v in e.verts):
                    edge_bevelled_edges.append(e.index)

                    # and just for debug purposes, update the dict as well
                    vgdata['edges'].append(e.index)

        if debug:
            print()
            printd(vgroups, 'vgroups')

        return edge_bevelled_edges

    def clear_obj_sharps(self, obj):
        obj.data.use_auto_smooth = False

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.normal_update()

        _, bw, cr = ensure_custom_data_layers(bm)

        for e in bm.edges:
            if self.clear_sharps:
                e.smooth = True

            if self.clear_bweights:
                e[bw] = 0

            if self.clear_creases:
                e[cr] = 0

            if self.clear_seams:
                e.seam = False

        bm.to_mesh(obj.data)
        bm.clear()

    def clear_mesh_sharps(self, mesh):
        mesh.use_auto_smooth = False

        bm = bmesh.from_edit_mesh(mesh)
        bm.normal_update()

        _, bw, cr = ensure_custom_data_layers(bm)

        # flatten all faces like in object mode
        for f in bm.faces:
            f.smooth = False

        for e in bm.edges:
            if self.clear_sharps:
                e.smooth = True

            if self.clear_bweights:
                e[bw] = 0

            if self.clear_creases:
                e[cr] = 0

            if self.clear_seams:
                e.seam = False

        bmesh.update_edit_mesh(mesh)


class ToggleAutoSmooth(bpy.types.Operator):
    bl_idname = "machin3.toggle_auto_smooth"
    bl_label = "Toggle Auto Smooth"
    bl_options = {'REGISTER', 'UNDO'}

    angle: IntProperty(name="Auto Smooth Angle")

    @classmethod
    def description(cls, context, properties):
        if properties.angle == 0:
            return "Toggle Auto Smooth"
        else:
            return "Auto Smooth Angle Preset: %d" % (properties.angle)

    def execute(self, context):
        active = context.active_object

        if active:
            sel = context.selected_objects

            if active not in sel:
                sel.append(active)

            autosmooth = not active.data.use_auto_smooth if self.angle == 0 else True

            for obj in [obj for obj in sel if obj.type == 'MESH']:
                obj.data.use_auto_smooth = autosmooth

                if self.angle:
                    obj.data.auto_smooth_angle = radians(self.angle)

        return {'FINISHED'}
