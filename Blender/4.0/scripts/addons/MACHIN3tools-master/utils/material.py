import bpy
from mathutils import Vector
from . registration import get_addon
from . math import get_sca_matrix
from . mesh import get_bbox


decalmachine = None

def get_last_node(mat):
    if mat.use_nodes:
        tree = mat.node_tree
        output = tree.nodes.get("Material Output")
        if output:
            surf = output.inputs.get("Surface")
            if surf:
                if surf.links:
                    return surf.links[0].from_node


def lighten_color(color, amount):
    def remap(value, new_low):
        old_range = (1 - 0)
        new_range = (1 - new_low)
        return (((value - 0) * new_range) / old_range) + new_low

    return tuple(remap(c, amount) for c in color)


def adjust_bevel_shader(context, debug=False):
    '''
    go over all visible objects, to find all materials used by them
    for objects without any material a "white bevel" material is created, if use_bevel_shader is True
    for each of these materiasl try to find a "Bevel" node
        if use_bevel_shader is True, and none can be found check if the last node has a normal input without any links
            if so hook up a new bevel node

    if use_bevel_shader is True
        adjust the sample and radius values according to the m3 props
    if use_bevel_shader is False
        if white bevel material exists
            remove it 
        if it doesn't:
            remove the bevel node in the current mat, if it exists
    '''

    debug = True
    debug = False

    m3 = context.scene.M3

    if debug:
        print("\nadjusting bevel shader")
        print("use bevel:", m3.use_bevel_shader)

    visible_objs = [obj for obj in context.visible_objects if obj.data and getattr(obj.data, 'materials', False) is not False and not any([obj.type == 'GPENCIL', obj.display_type in ['WIRE', 'BOUNDS'], obj.hide_render])]
    # print([obj.name for obj in visible_objs])

    white_bevel = bpy.data.materials.get('white bevel')
    white_bevel_objs = []

    visible_mats = {white_bevel} if white_bevel else set()

    if debug:
        print("white bevel mat:", white_bevel)

    if debug:
        print("\nvisible objects")

    for obj in visible_objs:
        mats = [mat for mat in obj.data.materials if mat]

        # clear material stack if there are only empty slots
        if obj.data.materials and not mats:
            obj.data.materials.clear()

        if debug:
            print(obj.name, [mat.name for mat in mats])

        # create white bevel mat, if it doesnt exist yet, then add it to any object without materials
        if m3.use_bevel_shader and not mats:
            if not white_bevel:
                if debug:
                    print(" creating new white bevel material")

                white_bevel = bpy.data.materials.new('white bevel')
                white_bevel.use_nodes = True

            if debug:
                print(" assigning white bevel material")

            obj.data.materials.append(white_bevel)
            mats.append(white_bevel)

        if obj.data.materials[0] == white_bevel:
            white_bevel_objs.append(obj)
        
        # collect all visible materials in a set
        visible_mats.update(mats)
        
        # set dimensions prop
        if m3.use_bevel_shader:

            # set dimensions factor based on max dim
            if m3.bevel_shader_use_dimensions:

                # get dimensions from non-evaluated mesh(as mirror mods massivele change the dims!)
                if obj.type == 'MESH':
                    # print(obj.name)

                    # get mesh dimensios as vector
                    dims = Vector(get_bbox(obj.data)[2])

                    # get scalemx
                    scalemx = get_sca_matrix(obj.matrix_world.to_scale())
                    
                    # get the maxdims by getting the length of the scalemx @ dis vector
                    maxdim = (scalemx @ dims).length
                    # print(maxdim)
                
                # fall back to obj.dims for non-mesh objects
                else:
                    maxdim = max(obj.dimensions)

                if debug:
                    print(" setting bevel dimensions to:", maxdim)

                obj.M3.bevel_shader_dimensions_mod = maxdim

            # re-set dimensions factor to 1
            else:
                if debug:
                    print(" re-setting bevel dimensions")

                obj.M3.bevel_shader_dimensions_mod = 1

            # this seems to be required, or toggling m3.bevel_shader_use_dimenions won't update the shader effect, unless you toggle in and out of obect mode
            obj.update_tag()

    # print("\nvisible mats:", [mat.name for mat in visible_mats])

    if debug:
        print("\nvisible materials")

    for mat in visible_mats:
        if debug:
            print(mat.name)

        tree = mat.node_tree

        bevel = tree.nodes.get('Bevel')
        math = tree.nodes.get('Bevel Shader Radius Math')
        math2 = tree.nodes.get('Bevel Shader Radius Math2')
        global_radius = tree.nodes.get('Bevel Shader Global Radius')
        obj_modulation = tree.nodes.get('Bevel Shader Object Radius Modulation')
        dim_modulation = tree.nodes.get('Bevel Shader Dimensions Modulation')

        if debug:
            print(" bevel:", bevel)
            print(" math:", math)
            print(" math2:", math2)
            print(" global_radius:", global_radius)
            print(" obj_modulation:", obj_modulation)
            print(" dim_modulation:", dim_modulation)

        # try to create bevel node
        if not bevel:
            if debug:
                print("\n no bevel node found")

            last_node = get_last_node(mat)

            if last_node:
                if debug:
                    print("  found last node", last_node.name)

                normal_input = last_node.inputs.get('Normal')

                if normal_input and not normal_input.links:
                    if debug:
                        print("   has a normal input without links, creating bevel node")

                    bevel = tree.nodes.new('ShaderNodeBevel')
                    bevel.location.x = last_node.location.x - 250

                    # for a newly created bevel mat, blender will return dimensions of 0 for the principled shader for some reason, so correct for that
                    y_dim = last_node.dimensions.y
                    if y_dim == 0:
                        y_dim = 660

                    bevel.location.y = last_node.location.y - y_dim + bevel.height

                    # link it to the normal output
                    tree.links.new(bevel.outputs[0], normal_input)

                    # create first math node
                    if not math:
                        if debug:
                            print("   creating multiply node")

                        math = tree.nodes.new('ShaderNodeMath')
                        math.name = "Bevel Shader Radius Math"
                        math.operation = 'MULTIPLY'

                        math.location = bevel.location
                        math.location.x = bevel.location.x - 200

                        tree.links.new(math.outputs[0], bevel.inputs[0])

                    # create second math node
                    if not math2:
                        if debug:
                            print("   creating 2nd multiply node")

                        math2 = tree.nodes.new('ShaderNodeMath')
                        math2.name = "Bevel Shader Radius Math"
                        math2.operation = 'MULTIPLY'

                        math2.location = math.location
                        math2.location.x = math.location.x - 200

                        tree.links.new(math2.outputs[0], math.inputs[0])

                    # create global radius value node
                    if not global_radius:
                        if debug:
                            print("   creating global radius node")

                        global_radius = tree.nodes.new('ShaderNodeValue')
                        global_radius.name = "Bevel Shader Global Radius"
                        global_radius.label = "Global Radius"

                        global_radius.location = math2.location
                        global_radius.location.x = math2.location.x - 200
                        global_radius.location.y = math2.location.y

                        tree.links.new(global_radius.outputs[0], math2.inputs[0])
                    
                    # create per-object radius modulation node
                    if not obj_modulation:
                        if debug:
                            print("   creating obj modulation node")

                        obj_modulation = tree.nodes.new('ShaderNodeAttribute')
                        obj_modulation.name = "Bevel Shader Object Radius Modulation"
                        obj_modulation.label = "Obj Radius Modulation"

                        obj_modulation.attribute_type = 'OBJECT'
                        obj_modulation.attribute_name = 'M3.bevel_shader_radius_mod'

                        obj_modulation.location = global_radius.location
                        obj_modulation.location.y = global_radius.location.y - 100

                        tree.links.new(obj_modulation.outputs[2], math2.inputs[1])

                    # create obj-dimensions radius modulation node
                    if not dim_modulation:
                        if debug:
                            print("   creating dimensions modulation node")

                        dim_modulation = tree.nodes.new('ShaderNodeAttribute')
                        dim_modulation.name = "Bevel Shader Dimensions Radius Modulation"
                        dim_modulation.label = "Dimensions Radius Modulation"

                        dim_modulation.attribute_type = 'OBJECT'
                        dim_modulation.attribute_name = 'M3.bevel_shader_dimensions_mod'

                        dim_modulation.location = math2.location
                        dim_modulation.location.y = math2.location.y - 175

                        tree.links.new(dim_modulation.outputs[2], math.inputs[1])

                # couldn't find a normal input, moving on to the next material
                else:
                    continue

            # couldn't find last node, moving on to the next material
            else:
                continue

        # set bevel node props
        if m3.use_bevel_shader:
            samples = bevel.samples
            radius = global_radius.outputs[0].default_value

            if samples != m3.bevel_shader_samples:
                if debug:
                    print(" setting bevel samples to:", m3.bevel_shader_samples)

                bevel.samples = m3.bevel_shader_samples

            if radius != m3.bevel_shader_radius:
                if debug:
                    print(" setting bevel radius to:", m3.bevel_shader_radius)
                
                # set the radius on the bevel node itself, even if it's overwritten by the input from the math node
                bevel.inputs[0].default_value = m3.bevel_shader_radius

                # then set it on the global radius value node
                global_radius.outputs[0].default_value = m3.bevel_shader_radius

        # remove bevel nodes and white bevel mat
        else:
            if mat == white_bevel:
                if debug:
                    print(" removing white bevel material")

                bpy.data.materials.remove(mat, do_unlink=True)
                
                for obj in white_bevel_objs:
                    obj.data.materials.clear()
                    print("  clearing material slots on", obj.name)

            else:
                if bevel:
                    if debug:
                        print(" removing bevel node")

                    tree.nodes.remove(bevel)

                if math:
                    if debug:
                        print(" removing math node")

                    tree.nodes.remove(math)

                if global_radius:
                    if debug:
                        print(" removing global radius node")

                    tree.nodes.remove(global_radius)

                if obj_modulation:
                    if debug:
                        print(" removing obj modulation node")

                    tree.nodes.remove(obj_modulation)

                if dim_modulation:
                    if debug:
                        print(" removing dim modulation node")

                    tree.nodes.remove(dim_modulation)


