import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty
import os
from mathutils import Vector
from .. utils.registration import get_addon, get_prefs, get_path
from .. utils.ui import popup_message
from .. utils.asset import get_asset_library_reference, set_asset_library_reference, update_asset_catalogs
from .. utils.object import parent
from .. utils.math import average_locations
from .. items import create_assembly_asset_empty_location_items, create_assembly_asset_empty_collection_items

import time


decalmachine = None
meshmachine = None


class CreateAssemblyAsset(bpy.types.Operator):
    bl_idname = "machin3.create_assembly_asset"
    bl_label = "MACHIN3: Create Assembly Asset"
    bl_description = "Create Assembly Asset from the selected Objects"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Asset Name", default="AssemblyAsset")
    move: BoolProperty(name="Move instead of Copy", description="Move Objects into Asset Collection, instead of copying\nThis will unlink them from any existing collections", default=True)

    location: EnumProperty(name="Empty Location", items=create_assembly_asset_empty_location_items, description="Location of Asset's Empty", default='AVGFLOOR')
    emptycol: EnumProperty(name="Empty Collection", items=create_assembly_asset_empty_collection_items, description="Collections to put the the Asset's Empty in", default='SCENECOL')

    remove_decal_backups: BoolProperty(name="Remove Decal Backups", description="Remove DECALmachine's Decal Backups, if present", default=False)
    remove_stashes: BoolProperty(name="Remove Stashes", description="Remove MESHmachine's Stashes, if present", default=False)

    render_thumbnail: BoolProperty(name="Render Thumbnail", default=True)
    thumbnail_lens: FloatProperty(name="Thumbnail Lens", default=100)
    toggle_overlays: BoolProperty(name="Toggle Overlays", default=True)

    def update_hide_instance(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        # prevent enabling both at the same time
        if self.hide_instance and self.hide_collection:
            self.avoid_update = True
            self.hide_collection = False

    def update_hide_collection(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        # prevent enabling both at the same time
        if self.hide_collection and self.hide_instance:
            self.avoid_update = True
            self.hide_instance = False

    unlink_collection: BoolProperty(name="Unlink Collection", description="Unlink the Asset Collection\nUseful to clean up the scene, and optionally start using the Asset locally right away", default=True)
    hide_collection: BoolProperty(name="Hide Collection", default=True, description="Hide the Asset Collection\nUseful when you want to start using the Asset locally, while still having easy access to the individual objects", update=update_hide_collection)
    hide_instance: BoolProperty(name="Hide Instance", default=False, description="Hide the COllection Instance Empty\nUseful when you want to keep working on the Asset's objects", update=update_hide_instance)

    # hidden
    avoid_update: BoolProperty()

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def draw(self, context):
        global decalmachine, meshmachine

        layout = self.layout

        column = layout.column(align=True)
        column.prop(self, 'name')
        column.prop(context.window_manager, 'M3_asset_catalogs', text='Catalog')

        if decalmachine or meshmachine:
            column.separator()
            column.label(text="DECALmachine and MESHmachine" if decalmachine and meshmachine else "DECALmachine" if decalmachine else "MESHmachine")
            row = column.row(align=True)

            if decalmachine:
                row.prop(self, 'remove_decal_backups', toggle=True)

            if meshmachine:
                row.prop(self, 'remove_stashes', toggle=True)

        column.separator()
        column.label(text="Asset Object Collections")
        column.prop(self, 'move', toggle=True)

        column.separator()
        column.label(text="Asset Empty")
        row = column.row(align=True)
        row.prop(self, 'emptycol', expand=True)
        row = column.row(align=True)
        row.prop(self, 'location', expand=True)

        column.separator()
        column.label(text="Asset Collection")
        row = column.row(align=True)
        row.prop(self, 'unlink_collection', toggle=True)
        r = row.row(align=True)
        r.active = not self.unlink_collection
        r.prop(self, 'hide_collection', toggle=True)
        r.prop(self, 'hide_instance', toggle=True)


        column.separator()
        column.label(text="Asset Thumbnail")
        row = column.row(align=True)
        row.prop(self, 'render_thumbnail', text="Viewport Render", toggle=True)
        r = row.row(align=True)
        r.active = self.render_thumbnail
        r.prop(self, 'toggle_overlays', text="Toggle Overlays", toggle=True)
        r.prop(self, 'thumbnail_lens', text='Lens')

    def invoke(self, context, event):
        global decalmachine, meshmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        update_asset_catalogs(self, context)

        # return {'FINISHED'}
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        global decalmachine, meshmachine

        name = self.name.strip()

        # decalmachine = True
        # self.remove_decal_backups = True

        # meshmachine = True
        # self.remove_stashes = True

        if name:
            print(f"INFO: Creation Assembly Asset: {name}")

            # from the selection get all the objects to create the
            objects = self.get_assembly_asset_objects(context)

            # get location to place the instance collection empty in
            rootobjs, loc = self.get_empty_location(context, objects)

            if decalmachine and self.remove_decal_backups:
                self.delete_decal_backups(objects)

            if meshmachine and self.remove_stashes:
                self.delete_stashes(objects)

            # create the asset
            instance = self.create_asset_instance_collection(context, name, objects, rootobjs, loc)

            # switch to an asset browser workspac and set it to LOCAL
            self.adjust_workspace(context)

            # render the viewport
            if self.render_thumbnail:
                thumbpath = os.path.join(get_path(), 'resources', 'thumb.png')
                self.render_viewport(context, thumbpath)

                # with context.temp_override(id=instance):
                #     bpy.ops.ed.lib_id_generate_preview(filepath=thumbpath)

                # NOTE: this just doesn'twork in 4.0 beta, complains about wrong context
                # ####: I tried everything, passing in assetbrowser area, space_data, region and region_data, incl an entire context object with these four replaced
                # ####: I tried invoking a dedicated op like in HyperCursor with the assetbrowser area, non of it would work
                # ####: the second could have worked, but I then couldn't set the new asset as the active one
                # ####: I could do that just fine for all existing assets though using assetbrowser space_data.activate_asset_from_id() or whatever it is called
                # ####: but when creating said asset in the same go it wouldn't work
                # ####: so I'm no diectly writing to the preview buffer, which takes a couple of seconds and a lot of CPU, but works without any stupid context overrides

                # NOTE: it is now instant thx to the [:] syntax, wow!
                # ####: see https://blender.stackexchange.com/a/3678/33919

                # load the rendered image, as th render result's pixels (and size) can't be accessed
                thumb = bpy.data.images.load(filepath=thumbpath)

                # create the preview from the img object's pixels
                instance.preview_ensure()
                instance.preview.image_size = thumb.size
                instance.preview.image_pixels_float[:] = thumb.pixels  # CodeManX is a legend

                # remove the loade and rendered thumb, and remove the file from disk too
                bpy.data.images.remove(thumb)
                bpy.data.images.remove(bpy.data.images['Render Result'])
                os.unlink(thumbpath)

            return {'FINISHED'}

        else:
            popup_message("The chosen asset name can't be empty", title="Illegal Name")

            return {'CANCELLED'}


    # UTILS

    def get_assembly_asset_objects(self, context):
        '''
        from the import selection, collect all objects for this assemtly asset, including unselected objects referecenced by boolean and mirror mods
        '''

        sel = context.selected_objects
        objects = set()

        for obj in sel:
            objects.add(obj)

            if obj.parent and obj.parent not in sel:
                objects.add(obj.parent)

            booleans = [mod for mod in obj.modifiers if mod.type == 'BOOLEAN']

            for mod in booleans:
                if mod.object and mod.object not in sel:
                    objects.add(mod.object)

            mirrors = [mod for mod in obj.modifiers if mod.type == 'MIRROR']

            for mod in mirrors:
                if mod.mirror_object and mod.mirror_object not in sel:
                    objects.add(mod.mirror_object)

        for obj in context.visible_objects:
            if obj not in objects and obj.parent and obj.parent in objects:
                objects.add(obj)

        return objects

    def get_empty_location(self, context, objects):
        '''
        from collection objects, get root objects
        return root objecst and the averaged location of them
        '''

        # get the root objects of these objects
        rootobjs = [obj for obj in objects if not obj.parent]

        if self.location in ['AVG', 'AVGFLOOR']:
            loc = average_locations([obj.matrix_world.decompose()[0] for obj in rootobjs])

            if self.location == 'AVGFLOOR':
                loc[2] = 0

        else:
            loc = Vector((0, 0, 0))

        # draw_point(loc, color=(1, 1, 0) if self.location == 'AVGFLOOR' else (1, 1, 1) if self.location == 'AVG' else (0, 1, 0), modal=False)
        # context.area.tag_redraw()

        return rootobjs, loc

    def delete_decal_backups(self, objects):
        decals_with_backups = [obj for obj in objects if obj.DM.isdecal and obj.DM.decalbackup]

        for decal in decals_with_backups:
            print(f"WARNING: Removing {decal.name}'s backup")

            if decal.DM.decalbackup:
                bpy.data.meshes.remove(decal.DM.decalbackup.data, do_unlink=True)

    def delete_stashes(self, objects):
        objs_with_stashes = [obj for obj in objects if obj.MM.stashes]

        for obj in objs_with_stashes:
            print(f"WARNING: Removing {obj.name}'s {len(obj.MM.stashes)} stashes")

            for stash in obj.MM.stashes:
                stashobj = stash.obj

                if stashobj:
                    print(" *", stash.name, stashobj.name)
                    bpy.data.meshes.remove(stashobj.data, do_unlink=True)

            obj.MM.stashes.clear()

    def create_asset_instance_collection(self, context, name, objects, rootobjs, loc):

        # create new collection for asset and link it to the master collection
        mcol = context.scene.collection
        acol = bpy.data.collections.new(name)
        mcol.children.link(acol)

        # collect the collections, the asset objects are currently in
        cols = {col for obj in objects for col in obj.users_collection}

        # optionally move out asset objects from their current collections
        if self.move:
            for obj in objects:
                for col in obj.users_collection:
                    if col in cols:
                        col.objects.unlink(obj)

        # link the objects to the new asset collection
        for obj in objects:
            acol.objects.link(obj)

            if get_prefs().hide_wire_objects_when_creating_assembly_asset and obj.display_type in ['WIRE', 'BOUNDS']:
                obj.hide_set(True)

                # just hiding is not enough, when part of an instance collection, what matters is the hide_viewport prop
                obj.hide_viewport = True

        # create the asset's instance collection empty
        instance = bpy.data.objects.new(name, object_data=None)
        instance.instance_collection = acol
        instance.instance_type = 'COLLECTION'

        # link it to the master collection
        if self.emptycol == 'SCENECOL':
            mcol.objects.link(instance)

        # link it to the asset object's collection
        else:
            for col in cols:
                col.objects.link(instance)

        # move instance empty to chosen locatino, and offset the root objects to compensate
        instance.location = loc

        for obj in rootobjs:
            obj.location = obj.location - loc

        # mark instace as asset
        instance.asset_mark()

        # printd(self.catalogs)
        catalog = context.window_manager.M3_asset_catalogs

        if catalog and catalog != 'NONE':
            instance.asset_data.catalog_id = self.catalogs[catalog]['uuid']

            # simple name is read only for some reason
            # turns out, it's read-only
            # instance.asset_data.catalog_simple_name = self.catalogs[catalog]['simple_name']

        if self.unlink_collection:
            mcol.children.unlink(acol)

        else:
            if self.hide_collection:
                context.view_layer.layer_collection.children[acol.name].hide_viewport = True
                instance.select_set(True)
                context.view_layer.objects.active = instance

            elif self.hide_instance:
                instance.hide_set(True)

        return instance

    def adjust_workspace(self, context):
        asset_browser_workspace = get_prefs().preferred_assetbrowser_workspace_name

        # switch to the preferred asset browser workspace, if one is defined in the addon preferences
        if asset_browser_workspace:
            ws = bpy.data.workspaces.get(asset_browser_workspace)

            if ws and ws != context.workspace:
                print("INFO: Switching to preffered Asset Browser Workspace")
                bpy.ops.machin3.switch_workspace('INVOKE_DEFAULT', name=asset_browser_workspace)

                # then ensure is shows the LOCAL library
                # note, this is done separately here, because the context.workspace isn't updating to the new workspac after the switch op
                self.switch_asset_browser_to_LOCAL(ws)
                return

        # if an asset browser is present on the current workspace, ensure it's set to LOCAL
        ws = context.workspace

        self.switch_asset_browser_to_LOCAL(ws)

    def switch_asset_browser_to_LOCAL(self, workspace):
        for screen in workspace.screens:
            for area in screen.areas:
                if area.type == 'FILE_BROWSER' and area.ui_type == 'ASSETS':
                    for space in area.spaces:
                        if space.type == 'FILE_BROWSER':
                            if get_asset_library_reference(space.params) != 'LOCAL':
                                set_asset_library_reference(space.params, 'LOCAL')

                            # ensure the tool props are shown too, so you can set the thumbnail
                            space.show_region_tool_props = True

    def render_viewport(self, context, filepath):
        '''
        render asset thumb
        '''

        # fetch current settings
        resolution = (context.scene.render.resolution_x, context.scene.render.resolution_y)
        file_format = context.scene.render.image_settings.file_format
        lens = context.space_data.lens
        show_overlays = context.space_data.overlay.show_overlays

        # adjust for thumbnail rendering
        context.scene.render.resolution_x = 128
        context.scene.render.resolution_y = 128
        context.scene.render.image_settings.file_format = 'JPEG'

        context.space_data.lens = self.thumbnail_lens

        if show_overlays and self.toggle_overlays:
            context.space_data.overlay.show_overlays = False

        # render
        bpy.ops.render.opengl()


        # fetch the render result and save it
        thumb = bpy.data.images.get('Render Result')

        if thumb:
            thumb.save_render(filepath=filepath)

        # resstore original settings
        context.scene.render.resolution_x = resolution[0]
        context.scene.render.resolution_y = resolution[1]
        context.space_data.lens = lens

        context.scene.render.image_settings.file_format = file_format

        if show_overlays and self.toggle_overlays:
            context.space_data.overlay.show_overlays = True


class AssembleInstanceCollection(bpy.types.Operator):
    bl_idname = "machin3.assemble_instance_collection"
    bl_label = "MACHIN3: Assemle Instance Collection"
    bl_description = "Make Instance Collection objects accessible\nALT: Keep Empty as Root"
    bl_options = {'REGISTER'}

    keep_empty: BoolProperty(name="Keep Empty as Root", default=False)

    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active and active.type == 'EMPTY' and active.instance_collection and active.instance_type == 'COLLECTION'

    def invoke(self, context, event):
        self.keep_empty = event.alt
        return self.execute(context)

    def execute(self, context):
        global decalmachine, meshmachine

        if decalmachine is None:
            decalmachine = get_addon('DECALmachine')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        active = context.active_object

        instances = {active} | {obj for obj in context.selected_objects if obj.type == 'EMPTY' and obj.instance_collection}

        # linked instance collections need to be made local first
        if any((i.instance_collection.library for i in instances)):
            # print(" linked collection instance present")
            bpy.ops.object.make_local(type='ALL')

            # the op will leave them unselected thought
            for instance in instances:
                instance.select_set(True)

        for instance in instances:
            collection = instance.instance_collection

            # assembled instance collection
            root_children = self.assemble_instance_collection(context, instance, collection)

            if self.keep_empty:
                for child in root_children:
                    parent(child, instance)

                    instance.select_set(True)
                    context.view_layer.objects.active = instance
            else:
                bpy.data.objects.remove(instance, do_unlink=True)

        # sweep decal backups
        if decalmachine:
            decals = [obj for obj in context.scene.objects if obj.DM.isdecal]
            backups = [obj for obj in decals if obj.DM.isbackup]

            if decals:
                from DECALmachine.utils.collection import sort_into_collections

                for obj in decals:
                    sort_into_collections(context, obj, purge=False)

            if backups:
                # print("removing decal backups")
                bpy.ops.machin3.sweep_decal_backups()

        # sweep stashes
        if meshmachine:
            stashobjs = [obj for obj in context.scene.objects if obj.MM.isstashobj]

            if stashobjs:
                bpy.ops.machin3.sweep_stashes()

        # run a purge, because somehow for linked libraries, there will still be linked datablocks here, this gets rid of them
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        return {'FINISHED'}

    def assemble_instance_collection(self, context, instance, collection):
        '''
        assemble appended instance collection

        NOTE: we are using the blender duplicate op here, becaue it massively simplies object duplication
        ####: not only do we need to duplicate the collections objects, but we also need to update all references
        ####: to parents objects, modifier objects, and driver objets. the later seems particulary laborous
        ####: but the duplicate op takes care of that for us
        '''

        cols = [col for col in instance.users_collection]
        imx = instance.matrix_world

        # print()
        # print(collection.name, collection.users_dupli_group)

        # get the collections's children and root children
        children = [obj for obj in collection.objects]
        # print("children:", [obj.name for obj in children])

        bpy.ops.object.select_all(action='DESELECT')

        for obj in children:
            for col in cols:
                if obj.name not in col.objects:
                    col.objects.link(obj)
            obj.select_set(True)

            if get_prefs().hide_wire_objects_when_assembling_instance_collection and obj.display_type in ['WIRE', 'BOUNDS']:
                obj.hide_set(True)

                # make sure hide_viewport is (no longer) set, as it would prevent unhiding the objects
                obj.hide_viewport = False

        # for multi-user collections, duplicate the contents and unlink originals again
        if len(collection.users_dupli_group) > 1:
            # print("WARNING: multi user collection, duplicating contents")

            bpy.ops.object.duplicate()

            for obj in children:
                for col in cols:
                    col.objects.unlink(obj)

            children = [obj for obj in context.selected_objects]
            # print("new children:", [obj.name for obj in children])

            for obj in children:
                if obj.name in collection.objects:
                    # print(f"WARNING: Unlinking {obj.name} from its asset collection {collection.name}")
                    collection.objects.unlink(obj)

        root_children = [obj for obj in children if not obj.parent]
        # print("root children", [obj.name for obj in root_children])

        # offset the collection's root children and select them
        for obj in root_children:
            obj.matrix_world = imx @ obj.matrix_world

            obj.select_set(True)
            context.view_layer.objects.active = obj

        # turn instance collection object into normal empty
        # this then lowers the user count of the collection accordingly
        instance.instance_type = 'NONE'
        instance.instance_collection = None

        if len(collection.users_dupli_group) == 0:
            # print("removing collection", collection.name)
            bpy.data.collections.remove(collection)

        return root_children


class CollectAssets(bpy.types.Operator):
    bl_idname = "machin3.collect_assets"
    bl_label = "MACHIN3: Collect Assets"
    bl_description = "Collect Asssets from current folder"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            collectpath = context.scene.M3.asset_collect_path
            return collectpath and os.path.exists(collectpath)

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)
        column.prop(context.window_manager, 'M3_asset_catalogs', text='Catalog')

    def invoke(self, context, event):
        collectpath = context.scene.M3.asset_collect_path

        blendpath = bpy.data.filepath
        self.blendfiles = sorted([os.path.join(collectpath, f) for f in os.listdir(collectpath) if f.endswith('.blend') and f != os.path.basename(blendpath)])

        if self.blendfiles:
            update_asset_catalogs(self, context)
            return context.window_manager.invoke_props_dialog(self)
        else:
            popup_message("No blend files found in Folder!", title="Info")
            return {'CANCELLED'}

    def execute(self, context):
        mcol = context.scene.collection

        print()

        for path in self.blendfiles:
            materials = self.append_all(path, 'materials')

            for mat in materials:
                if mat:
                    print(f"Appended Material {mat.name} as asset")
                    mat.asset_mark()

                    catalog = context.window_manager.M3_asset_catalogs

                    if catalog and catalog != 'NONE':
                        mat.asset_data.catalog_id = self.catalogs[catalog]['uuid']
                        print(f" adding to catalog {catalog}")

                    dirname = os.path.dirname(path)
                    basename = os.path.basename(path).replace('.blend', '')

                    jpgpath = os.path.join(dirname, basename + '.jpg')
                    pngpath = os.path.join(dirname, basename + '.png')

                    if os.path.exists(jpgpath):
                        print(" using existing .jpg thumbnail")
                        with context.temp_override(id=mat):
                            bpy.ops.ed.lib_id_load_custom_preview(filepath=jpgpath)
                    elif os.path.exists(pngpath):
                        print(" using existing .png thumbnail")
                        with context.temp_override(id=mat):
                            bpy.ops.ed.lib_id_load_custom_preview(filepath=pngpath)
                    else:
                        print(" generating new preview")
                        with context.temp_override(id=mat):
                            bpy.ops.ed.lib_id_generate_preview()

                        time.sleep(0.1)

        return {'FINISHED'}

    def append_all(self, filepath, collection, link=False, relative=False):
        if os.path.exists(filepath):

            with bpy.data.libraries.load(filepath, link=link, relative=relative) as (data_from, data_to):

                for name in getattr(data_from, collection):
                    getattr(data_to, collection).append(name)

            return getattr(data_to, collection)

        else:
            print("The file %s does not exist" % (filepath))
