import bpy
from bpy.props import BoolProperty
import bmesh
from mathutils import Vector
import os
from .. utils.raycast import cast_obj_ray_from_mouse, cast_bvh_ray_from_mouse
from .. utils.draw import draw_label, update_HUD_location, draw_init
from .. utils.registration import get_prefs
from .. utils.system import printd
from .. utils.ui import init_cursor, init_status, finish_status
from .. utils.asset import get_asset_details_from_space
from .. items import alt, ctrl
from .. colors import white, yellow, green, red


def draw_material_pick_status(op):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text=f"Material Picker")

        if op.assign_from_assetbrowser:
            row.label(text="Assign Material from Asset Browsr to Object under Mouse")

        else:
            row.label(text="", icon='MOUSE_LMB')
            
            if op.assign:
                row.label(text="Pick Material and Assign it to Selected Objects")

            else:
                row.label(text="Pick Material and Finish")

        row.label(text="", icon='MOUSE_MMB')
        row.label(text="Viewport")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

        row.label(text="", icon='EVENT_SPACEKEY')
        row.label(text="Finish")

        row.separator(factor=10)

        row.label(text="", icon='EVENT_ALT')
        row.label(text=f"Assign Material: {op.assign}")

        if op.asset_browser:
            row.label(text="", icon='EVENT_CTRL')
            row.label(text=f"Assign Material from Asset Browser: {op.assign_from_assetbrowser}")

    return draw


class MaterialPicker(bpy.types.Operator):
    bl_idname = "machin3.material_picker"
    bl_label = "MACHIN3: Material Picker"
    bl_description = "Pick a Material from the 3D View\nALT: Assign it to the Selection too"
    bl_options = {'REGISTER', 'UNDO'}

    # hidden
    passthrough = None

    @classmethod
    def poll(cls, context):
        if context.mode in ['OBJECT', 'EDIT_MESH']:
            return context.area.type == 'VIEW_3D'

    def draw_HUD(self, context):
        draw_init(self, None)

        title, color = ("Assign from Asset Browser ", green) if self.assign_from_assetbrowser else ("Assign", yellow) if self.assign else ("Pick", white)
        dims = draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), color=color, center=False)

        if self.assign_from_assetbrowser:

            if self.asset['error']:
                self.offset += 18
                draw_label(context, title=self.asset['error'], coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=red, alpha=1)

            else:
                draw_label(context, title=self.asset['import_type'], coords=Vector((self.HUD_x + dims[0], self.HUD_y)), center=False, color=white, alpha=0.5)

                self.offset += 18

                title = f"{self.asset['library']} • {self.asset['blend_name']} • "
                dims = draw_label(context, title=title, coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)

                title = f"{self.asset['material_name']}"
                draw_label(context, title=title, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=white)

        else:
            self.offset += 18

            color = red if self.pick_material_name == 'None' else white

            dims = draw_label(context, title='Material ', coords=Vector((self.HUD_x, self.HUD_y)), offset=self.offset, center=False, color=white, alpha=0.5)
            draw_label(context, title=self.pick_material_name, coords=Vector((self.HUD_x + dims[0], self.HUD_y)), offset=self.offset, center=False, color=color, alpha=1)

    def modal(self, context, event):
        context.area.tag_redraw()

        self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.mouse_pos_window = Vector((event.mouse_x, event.mouse_y))

        area_under_mouse = self.get_area_under_mouse(self.mouse_pos_window)
        # print("area under mouse:", area_under_mouse)

        # restore mouse eyedropper mouse cursor, and fetch the selected asset from the asset browser
        if self.passthrough and area_under_mouse != 'ASSET_BROWSER':
            self.passthrough = False
            context.window.cursor_set("EYEDROPPER")

            # fetch selected asset from asset browser
            self.asset = self.get_selected_asset(context, debug=False)

            # if self.asset:
                # printd(self.asset)


        # PASSTROUGH to ASSET BROWSER

        if area_under_mouse == 'ASSET_BROWSER':
            self.passthrough = True
            return {'PASS_THROUGH'}


        # VIEW3D

        elif area_under_mouse == 'VIEW_3D':

            # MOD KEYS

            self.assign = event.alt

            if 'ASSET_BROWSER' in self.areas:
                self.assign_from_assetbrowser = event.ctrl

                if self.assign_from_assetbrowser:
                    self.assign = False

            if event.type in [*alt, *ctrl]:
                if event.value == 'PRESS':
                    context.window.cursor_set("PAINT_CROSS")


                elif event.value == 'RELEASE':
                    context.window.cursor_set("EYEDROPPER")
                
                # force statusbar update
                if context.visible_objects:
                    context.visible_objects[0].select_set(context.visible_objects[0].select_get())


            # MOUSEMOVE

            if event.type == 'MOUSEMOVE':
                update_HUD_location(self, event)

                # fetch material via raycast in pick and assign modes, but not when assigning from the asset browser
                if not self.assign_from_assetbrowser:
                    hitobj, matindex = self.get_material_hit(context, self.mouse_pos, debug=False)

                    # try to fetch the material from the hit and stroe its name on the op
                    mat, self.pick_material_name = self.get_material_from_hit(hitobj, matindex)


            # FINISH

            elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':

                hitobj, matindex = self.get_material_hit(context, self.mouse_pos, debug=False)

                if hitobj:

                    # ASSIGN from ASSETBROWSER

                    if self.assign_from_assetbrowser:

                        # Import Material from ASSETBROWSER and assign it to the picked object at matindex or to the selected faces in edit mode

                        if not self.asset['error']:

                            # import material from assetbrowser, except when its in the scene already
                            mat = self.get_material_from_assetbrowser(context)

                            # object mode - apply material at the matindex of the hitobject, and keep the modal going, as you may want to apply the material to other parts or objects
                            if context.mode == 'OBJECT':
                                # print(" applying to obj", hitobj.name, "at index", matindex)

                                if hitobj.material_slots:
                                    hitobj.material_slots[matindex].material = mat
                                else:
                                    hitobj.data.materials.append(mat)

                            # edit mode - assign the material to active's face selection in edit mode, and FINISH
                            elif context.mode == 'EDIT_MESH':
                                self.assign_material_in_editmode(context, mat)

                                self.finish(context)
                                return {'FINISHED'}


                    # ASSIGN - assign the picked material to the selection of objects, and FINISH

                    elif self.assign:
                        mat, matname = self.get_material_from_hit(hitobj, matindex)

                        if mat:

                            # in object mode, assign the picked material to all objects in the selection at the active_material index
                            if context.mode == 'OBJECT':

                                sel = [obj for obj in context.selected_objects if obj != hitobj and obj.type == 'MESH']

                                for obj in sel:
                                    if not obj.material_slots:
                                        obj.data.materials.append(mat)

                                    else:
                                        obj.material_slots[obj.active_material_index].material = mat

                            # in edit mode assign the picked material to the face selection, and we can simply reuse the function used by asset browser assigning here
                            elif context.mode == 'EDIT_MESH':
                                self.assign_material_in_editmode(context, mat)

                        self.finish(context)

                        return {'FINISHED'}


                    # PICK - make the hitobject and its material (slot) active, and FINISH

                    else:

                        # if you are in edit mode and pick from an object that isnt in edit mode, you should take that one into edit mode
                        # if you don't then changing the active pops the current object out of edit mode, which seems odd
                        iseditmode = context.mode == 'EDIT_MESH'

                        if context.active_object != hitobj:
                            context.view_layer.objects.active = hitobj

                            if iseditmode:
                                bpy.ops.object.mode_set(mode='EDIT')
                            
                        # make the material slot on  the hitobject active, if you arn't assigning from the asset browser
                        hitobj.active_material_index = matindex

                        self.finish(context)
                        return {'FINISHED'}


            # FINISH with SPACE

            elif event.type == 'SPACE':
                self.finish(context)
                return {'FINISHED'}


            # NAV PASSTHROUGH

            elif event.type == 'MIDDLEMOUSE':
                return {'PASS_THROUGH'}


            # CANCEL

            elif event.type in ['RIGHTMOUSE', 'ESC']:
                self.finish(context)
                return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')

        context.window.cursor_set("DEFAULT")

        # reset statusbar
        finish_status(self)

        if context.visible_objects:
            context.visible_objects[0].select_set(context.visible_objects[0].select_get())

    def invoke(self, context, event):

        # init
        self.assign = False 
        self.assign_from_assetbrowser = False 
        self.pick_material_name = "None"

        # get the depsgraph
        self.dg = context.evaluated_depsgraph_get()

        # init mouse cursor
        init_cursor(self, event)
        context.window.cursor_set("EYEDROPPER")

        # check the active screen and fetch all areas and their position/dimenension
        self.areas, self.asset_browser = self.get_areas(context)

        # then fetch the selected asset
        self.asset = self.get_selected_asset(context, debug=False)

        # int statusbar
        init_status(self, context, func=draw_material_pick_status(self))

        if context.visible_objects:
            context.visible_objects[0].select_set(context.visible_objects[0].select_get())

        # handlers
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (context, ), 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    
    # UTILS

    def get_areas(self, context):
        '''
        check the active screen and fetch all areas and their position/dimenension
        '''

        areas = {}
        asset_browser = None

        for area in context.screen.areas:
            if area.type == 'FILE_BROWSER' and area.ui_type == 'ASSETS':
                area_type = 'ASSET_BROWSER'
                asset_browser = area.spaces.active

            else:
                area_type = area.type

            # print("     x:", area.x)
            # print("     y:", area.y)
            # print(" width:", area.width)
            # print("height:", area.height)

            areas[area_type] = {'x': (area.x, area.x + area.width),
                                'y': (area.y, area.y + area.height)}

        return areas, asset_browser

    def get_area_under_mouse(self, mouse_pos):
        '''
        return name of area, under ther mouse
        '''

        for areaname, coords in self.areas.items():
            if coords['x'][0] <= mouse_pos.x <= coords['x'][1]:
                # print(" in x of", areaname)

                if coords['y'][0] <= mouse_pos.y <= coords['y'][1]:
                    # print(" in y of", areaname, "too")
                    return areaname

    def get_selected_asset(self, context, debug=False):
        '''
        from the asset browser, fetch the selected asset
        '''

        if self.asset_browser:
            libname, libpath, filename, import_type = get_asset_details_from_space(context, self.asset_browser, debug=debug)

            if libpath:
                # NOTE: the filename (path) will look different on Windows and Linux, it will mix \\ and / on Windows, lol

                # Linux
                # path: Insets.blend/Object/Cross
                # split path: ['Insets.blend', 'Cross']

                # Windows
                # path: Insets.blend\Object/Assembly Asset
                # split path: ['Insets.blend\\Object/Cross']

                # so replace that shit
                path = filename.replace('\\', '/')

                # is it actually a material asset?
                if '/Material/' in path:

                    # split relative path into blend path and materialname
                    blendname, matname = path.split('/Material/')
                    # print("blendname:", blendname)
                    # print("matname:", matname)

                    # check if the blend path actually exists, if you switch libraries without making a new selection, it's possible to have get a libpath and blend file that don't match
                    if os.path.exists(os.path.join(libpath, blendname)):

                        directory = os.path.join(libpath, blendname, 'Material')
                        # print("directory:", directory)

                        asset = {'error': None,
                                 'import_type': import_type.title().replace('_', ' '),
                                 'library': libname,
                                 'directory': directory,
                                 'blend_name': blendname.replace('.blend', ''),
                                 'material_name': matname}


                    else:
                        msg = f".blend file does not exist: {os.path.join(libpath, blendname)}"
                        # print("WARNING:", msg)
                        asset = {'error': msg}


                else:
                    msg = "No material selected in asset browser!"
                    # print("WARNING:", msg)
                    asset = {'error': msg}

            else:
                msg = "LOCAL or unsupported library chosen!"
                # print("WARNING:", msg)
                asset = {'error': msg}

        else:
            msg = "There is no asset browser in this workspace"
            # print("WARNING:", msg)
            asset = {'error': msg}


        if debug:
            printd(asset)

        return asset

    def get_material_hit(self, context, mousepos, debug=False):
        '''
        cat ray in object or edit mode and return the hit object and material index
        '''

        if debug:
            print("\nmaterial hitting at", mousepos)
        
        if context.mode == 'OBJECT':
            hitobj, hitobj_eval, _, _, hitindex, _ = cast_obj_ray_from_mouse(self.mouse_pos, depsgraph=self.dg, debug=False)

        elif context.mode == 'EDIT_MESH':
            # hitobj, _, _, hitindex, _, _ = cast_bvh_ray_from_mouse(self.mousepos, candidates=[obj for obj in context.visible_objects if obj.mode == 'EDIT'], debug=False)
            hitobj, _, _, hitindex, _, _ = cast_bvh_ray_from_mouse(self.mouse_pos, candidates=[obj for obj in context.visible_objects], debug=False)

        if hitobj:

            if context.mode == 'OBJECT':
                matindex = hitobj_eval.data.polygons[hitindex].material_index
            elif context.mode == 'EDIT_MESH':
                matindex = hitobj.data.polygons[hitindex].material_index

            if debug:
                print(" hit object:", hitobj.name, "material index:", matindex)

            # NOTE: safe-guard against crazy big material indices, which can happen as a result of (live?) booleans
            matindex = min(matindex, len(hitobj.material_slots) - 1)

            return hitobj, matindex

        if debug:
            print(" nothing hit")
        return None, None

    def get_material_from_hit(self, obj, index):
        '''
        from the passed in object and material index, return the material, if there is ona at the stack index
        return None, if either argument is None or there is no material are the passed in index
        '''

        if obj and index is not None:
            if obj.material_slots and obj.material_slots[index].material:
                mat = obj.material_slots[index].material
                return mat, mat.name
        return None, 'None'

    def get_material_from_assetbrowser(self, context):
        import_type = self.asset['import_type']
        directory = self.asset['directory']
        filename = self.asset['material_name']

        # print("\nassset browser material import")
        mat = bpy.data.materials.get(filename)

        # only append/link if a material of that name doesn't exist already
        if not mat:
            # print(" import type:", import_type)
            # print(" directory:", directory)
            # print(" filename:", filename)

            # cant append/link in edit mode, gotta switch to object mode
            iseditmode = context.mode == 'EDIT_MESH'

            if iseditmode:
                bpy.ops.object.mode_set(mode='OBJECT')

            if 'Append' in import_type:
                reuse_local_id= 'Reuse' in import_type
                bpy.ops.wm.append(directory=directory, filename=filename, do_reuse_local_id=reuse_local_id)

            else:
                bpy.ops.wm.link(directory=directory, filename=filename)

            # switch back
            if iseditmode:
                bpy.ops.object.mode_set(mode='EDIT')

            # fetch the imported material so it can be assigned
            mat = bpy.data.materials.get(filename)
            # print(" imported material:", mat)

            # disable fake user
            if mat.use_fake_user:
                mat.use_fake_user = False

        return mat


    # ASSIGN

    def assign_material_in_editmode(self, context, mat):
        '''
        apply material to face selection of active object
        '''

        active = context.active_object

        if active.material_slots:
            bm = bmesh.from_edit_mesh(active.data)
            bm.normal_update()

            faces = [f for f in bm.faces if f.select]

            # only proceed if there is a face selection
            if faces:
                mat_indices = set(f.material_index for f in faces)

                # chech if the material is already assigned to that material
                if len(mat_indices) == 1:
                    index = mat_indices.pop()
                    mat_at_index = active.material_slots[index].material

                    # not doing anything, the material is already assigned, so just ensure the index is active
                    if mat_at_index == mat:
                        active.active_material_index = index
                        return

                # check if the material is in the stack already, if so take the existing index
                if mat.name in active.data.materials:
                    index = list(active.data.materials).index(mat)

                # get the index for the new material
                else:
                    index = len(active.material_slots)

                for f in faces:
                    f.material_index = index

                bmesh.update_edit_mesh(active.data)

                # run this too, otherwise the material picker won't recoginze the new material unless you finish and toggle modes
                active.update_from_editmode()

                # append the material if it isn't in the stack yet
                if mat.name not in active.data.materials:
                    active.data.materials.append(mat)

                # make the new index active
                active.active_material_index = index

        # without any material slots, just append the material, to create the first slot
        else:
            active.data.materials.append(mat)
