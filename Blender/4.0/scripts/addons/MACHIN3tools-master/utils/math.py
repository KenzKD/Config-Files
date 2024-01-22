from mathutils import Matrix, Vector
from mathutils.geometry import intersect_line_plane
from math import log10, floor


# VALUE

def dynamic_format(value, decimal_offset=0):
    '''
    see https://stackoverflow.com/questions/8011017/python-find-first-non-zero-digit-after-decimal-point
    and https://stackoverflow.com/questions/658763/how-to-suppress-scientific-notation-when-printing-float-values

    decimal offset adds additional decimal places

    return formated string
    '''
    if round(value, 6) == 0:
        return '0'

    l10 = log10(abs(value))
    f = floor(abs(l10))

    if l10 < 0:
        precision = f + 1 + decimal_offset

    else:
        precision = decimal_offset
    return f"{'-' if value < 0 else ''}{abs(value):.{precision}f}"


# VECTOR

def get_center_between_points(point1, point2, center=0.5):
    return point1 + (point2 - point1) * center


def get_center_between_verts(vert1, vert2, center=0.5):
    return get_center_between_points(vert1.co, vert2.co, center=center)


def get_edge_normal(edge):
    return average_normals([f.normal for f in edge.link_faces])


def get_face_center(face, method='MEDIAN_WEIGHTED'):
    if method == 'BOUNDS':
        return face.calc_center_bounds()
    elif method == 'MEDIAN':
        return face.calc_center_median()
    elif method == 'MEDIAN_WEIGHTED':
        return face.calc_center_median_weighted()


def average_locations(locationslist, size=3):
    avg = Vector.Fill(size)

    for n in locationslist:
        avg += n

    return avg / len(locationslist)


def average_normals(normalslist):
    avg = Vector()

    for n in normalslist:
        avg += n

    return avg.normalized()


def get_world_space_normal(normal, mx):
    '''
    this creates a correct world space normal, even for non-uniformely scaled objects

    NOTE: not completely sure why, but it needs this quat + 3x3 combination
    doing 3x3 two times won't work
    '''
    # scamx = get_sca_matrix(mx.to_scale())
    # return (mx.to_quaternion().to_matrix() @ scamx.to_3x3().inverted_safe() @ normal).normalized()

    # this also works, see https://blenderartists.org/t/getting-plane-normal-for-distance-point-to-plane-function/1328061/3?u=machin3
    # and https://www.scratchapixel.com/lessons/mathematics-physics-for-computer-graphics/geometry/transforming-normals
    return (mx.inverted_safe().transposed().to_3x3() @ normal).normalized()


# MATRIX

def flatten_matrix(mx):
    dimension = len(mx)
    return [mx[j][i] for i in range(dimension) for j in range(dimension)]


def compare_matrix(mx1, mx2, precision=4):
    '''
    matrix comparison by rounding the individual values
    this is used for comparing cursor matrices,
    which if changed used set_cursor has the tendenciy to have float precission issues prevent proper comparison
    '''

    round1 = [round(i, precision) for i in flatten_matrix(mx1)]
    round2 = [round(i, precision) for i in flatten_matrix(mx2)]
    return round1 == round2


def get_loc_matrix(location):
    return Matrix.Translation(location)


def get_rot_matrix(rotation):
    return rotation.to_matrix().to_4x4()


def get_sca_matrix(scale):
    scale_mx = Matrix()
    for i in range(3):
        scale_mx[i][i] = scale[i]
    return scale_mx


def create_rotation_matrix_from_vertex(obj, vert):
    '''
    create world space rotation matrix from vertex
    supports loose vertices too
    '''
    mx = obj.matrix_world

    # get the vertex normal in world space
    normal = mx.to_3x3() @ vert.normal

    # get binormal from longest linked edge
    if vert.link_edges:
        longest_edge = max([e for e in vert.link_edges], key=lambda x: x.calc_length())
        binormal = (mx.to_3x3() @ (longest_edge.other_vert(vert).co - vert.co)).normalized()

        # the tangent is a simple cross product
        tangent = binormal.cross(normal).normalized()

        # recalculate the binormal, because it's not guarantieed the previous one is 90 degrees to the normal
        binormal = normal.cross(tangent).normalized()

    # without linked faces get a binormal from the objects up vector
    else:
        objup = (mx.to_3x3() @ Vector((0, 0, 1))).normalized()

        # use the x axis if the edge is already pointing in z
        dot = normal.dot(objup)
        if abs(round(dot, 6)) == 1:
            objup = (mx.to_3x3() @ Vector((1, 0, 0))).normalized()

        tangent = normal.cross(objup).normalized()
        binormal = normal.cross(tangent).normalized()

    # we want the normal, tangent and binormal to become Z, X and Y, in that order
    # see http://renderdan.blogspot.com/2006/05/rotation-matrix-from-axis-vectors.html
    rot = Matrix()
    rot[0].xyz = tangent
    rot[1].xyz = binormal
    rot[2].xyz = normal

    # transpose, because blender is column major
    return rot.transposed()


# def create_rotation_matrix_from_edge(obj, edge):
#     '''
#     create world space rotation matrix from edge
#     supports loose edges too
#     '''
#     mx = obj.matrix_world
#
#     # call the direction, the binormal, we want this to be the y axis at the end
#     binormal = (mx.to_3x3() @ (edge.verts[1].co - edge.verts[0].co)).normalized()
#
#     # get normal from linked faces
#     if edge.link_faces:
#         normal = (mx.to_3x3() @ get_edge_normal(edge)).normalized()
#         tangent = binormal.cross(normal).normalized()
#
#         # recalculate the normal, that's because the one calculated from the neighbouring faces may not actually be perpendicular to the binormal, if the faces are not planar
#         normal = tangent.cross(binormal).normalized()
#
#     # without linked faces get a normal from the objects up vector
#     else:
#         objup = (mx.to_3x3() @ Vector((0, 0, 1))).normalized()
#
#         # use the x axis if the edge is already pointing in z
#         dot = binormal.dot(objup)
#         if abs(round(dot, 6)) == 1:
#             objup = (mx.to_3x3() @ Vector((1, 0, 0))).normalized()
#
#         tangent = (binormal.cross(objup)).normalized()
#         normal = tangent.cross(binormal)
#
#     # we want the normal, tangent and binormal to become Z, X and Y, in that order
#     rotmx = Matrix()
#     rotmx[0].xyz = tangent
#     rotmx[1].xyz = binormal
#     rotmx[2].xyz = normal
#
#     # transpose, because blender is column major
#     return rotmx.transposed()


def create_rotation_matrix_from_edge(context, mx, edge):
    '''
    create world space rotation matrix from edge
    supports loose edges too
    '''

    # call the direction, the binormal, we want this to be the y axis at the end
    binormal = (mx.to_3x3() @ (edge.verts[1].co - edge.verts[0].co)).normalized()

    # align it with view up, because we do it for faces too now
    view_up = context.space_data.region_3d.view_rotation @ Vector((0, 1, 0))
    binormal_dot = binormal.dot(view_up)

    # if the binormal is pointin in the opposite was as the view up dir, negate it
    if binormal_dot < 0:
        binormal.negate()

    # get normal from linked faces
    if edge.link_faces:
        # normal = (mx.to_3x3() @ get_edge_normal(edge)).normalized()
        # normal = get_world_space_normal(get_edge_normal(edge), mx).normalized()
        normal = average_normals([get_world_space_normal(f.normal, mx) for f in edge.link_faces]).normalized()

        tangent = binormal.cross(normal).normalized()

        # recalculate the normal, that's because the one calculated from the neighbouring faces may not actually be perpendicular to the binormal, if the faces are not planar
        normal = tangent.cross(binormal).normalized()


    # without linked faces get a normal from the objects up vector
    else:
        objup = (mx.to_3x3() @ Vector((0, 0, 1))).normalized()

        # use the x axis if the edge is already pointing in z
        dot = binormal.dot(objup)
        if abs(round(dot, 6)) == 1:
            objup = (mx.to_3x3() @ Vector((1, 0, 0))).normalized()

        tangent = (binormal.cross(objup)).normalized()
        normal = tangent.cross(binormal)

    # we want the normal, tangent and binormal to become Z, X and Y, in that order
    rotmx = Matrix()
    rotmx.col[0].xyz = tangent
    rotmx.col[1].xyz = binormal
    rotmx.col[2].xyz = normal
    return rotmx

# def create_rotation_matrix_from_face(mx, face):
#     '''
#     create world space rotation matrix from face
#     '''
#
#     # get the face normal in world space
#     normal = (mx.to_3x3() @ face.normal).normalized()
#
#     # tangent = (mx.to_3x3() @ face.calc_tangent_edge()).normalized()
#     tangent = (mx.to_3x3() @ face.calc_tangent_edge_pair()).normalized()
#
#     # the binormal is a simple cross product
#     binormal = normal.cross(tangent)
#
#     # we want the normal, tangent and binormal to become Z, X and Y, in that order
#     rot = Matrix()
#     rot[0].xyz = tangent
#     rot[1].xyz = binormal
#     rot[2].xyz = normal
#
#     # transpose, because blender is column major
#     return rot.transposed()


def create_rotation_matrix_from_face(context, mx, face, edge_pair=True, cylinder_threshold=0.01, align_binormal_with_view=True):
    '''
    create world space rotation matrix from face
    '''

    # get the face normal in world space
    # normal = (mx.to_3x3() @ face.normal).normalized()
    normal = get_world_space_normal(face.normal, mx)
    binormal = None
    face_center = face.calc_center_median()

    # find out if the face is a circle, and so likely a cylinder cap
    circle = False

    if len(face.verts) > 4:
        edge_lengths = [e.calc_length() for e in face.edges]
        center_distances = [(v.co - face_center).length for v in face.verts]

        avg_edge_length = sum(edge_lengths) / len(face.edges)
        avg_center_distance = sum(center_distances) / len(face.verts)

        edges_are_same_length = all([abs(l - avg_edge_length) < avg_edge_length * cylinder_threshold for l in edge_lengths])
        verts_have_same_center_distance = all([abs(d - avg_center_distance) < avg_center_distance * cylinder_threshold for d in center_distances])

        if edges_are_same_length and verts_have_same_center_distance:
            circle = True

    # if the face is a circle, try aliging the binormal with one of the object axes, preferably the y axis
    if circle:
        for axis in [Vector((0, 1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1))]:

            # project axis on face
            i = intersect_line_plane(face_center + axis, face_center + axis + face.normal, face_center, face.normal)

            if i:
                projected = i - face_center

                # ensure the vector has any length, and if it has it's our binormal
                if round(projected.length, 6):
                    binormal = (mx.to_3x3() @ projected).normalized()
                    break

    # get the binormal from the two longest longest disconnected edges, or the single longest edge
    if not binormal:
        # NOTE: it turns out you shouldn't use the get_world_space_normal() method here! it will produce a binormal that's not orthogonal to the normal on non-uniformaly scaled objects! 
        # ####: it seems like these are not normals, but just vectors!
        # ####: see 262_cursor_does_not_snap_to_this_face_correctly_DM_gets_it_wrong_too!_applied.blend  

        binormal = (mx.to_3x3() @ face.calc_tangent_edge_pair()).normalized() if edge_pair else (mx.to_3x3() @ face.calc_tangent_edge()).normalized()
        # binormal = get_world_space_normal(face.calc_tangent_edge_pair(), mx).normalized() if edge_pair else get_world_space_normal(face.calc_tangent_edge(), mx).normalized()

    # the tangent is a simple cross product
    tangent = binormal.cross(normal).normalized()

    # NOTE: Blender natively aligns the binormal with the view up vector, so let's do the same, for consistencie's sake
    # so find out if binormal or tangent is more aligned with the view_up vector
    if align_binormal_with_view:
        view_up = context.space_data.region_3d.view_rotation @ Vector((0, 1, 0))

        tangent_dot = tangent.dot(view_up)
        binormal_dot = binormal.dot(view_up)

        # switch binormal with tangent, if tangent is more aligned with the view up dir
        if abs(tangent_dot) >= abs(binormal_dot):
            binormal, tangent = tangent, -binormal
            binormal_dot = tangent_dot

        # if the binormal is pointing in the opposite way as the view up dir, negate it (and the tangent)
        if binormal_dot < 0:
            binormal, tangent = -binormal, -tangent

    """
    # ensure everything is as orthogonal as possible
    # NOTE: but it still seems to make no difference in CJ's array building issue
    print()
    print(f"{tangent.length:.20f}")
    print(f"{binormal.length:.20f}")
    print(f"{normal.length:.20f}")

    tangent_dot = normal.dot(tangent)
    binormal_dot = normal.dot(binormal)

    print()
    print(f"{tangent_dot:.20f}")
    print(f"{binormal_dot:.20f}")

    # recalc binormal or tangent
    if abs(tangent_dot) < abs(binormal_dot):
        binormal = normal.cross(tangent)
        print("fixed binormal ortho")

    else:
        tangent = binormal.cross(normal)
        print("fixed tangent ortho")

    tangent_dot = normal.dot(tangent)
    binormal_dot = normal.dot(binormal)

    print()
    print(f"{tangent_dot:.20f}")
    print(f"{binormal_dot:.20f}")

    # we want the normal, tangent and binormal to become Z, X and Y, in that order
    rot = Matrix()
    rot.col[0].xyz = tangent.normalized()
    rot.col[1].xyz = binormal.normalized()
    rot.col[2].xyz = normal.normalized()
    """

    # we want the normal, tangent and binormal to become Z, X and Y, in that order
    rot = Matrix()
    rot.col[0].xyz = tangent
    rot.col[1].xyz = binormal
    rot.col[2].xyz = normal

    return rot



def create_rotation_difference_matrix(v1, v2):
    q = v1.rotation_difference(v2)
    return q.to_matrix().to_4x4()


def create_selection_bbox(coords):
    minx = min(coords, key=lambda x: x[0])
    maxx = max(coords, key=lambda x: x[0])

    miny = min(coords, key=lambda x: x[1])
    maxy = max(coords, key=lambda x: x[1])

    minz = min(coords, key=lambda x: x[2])
    maxz = max(coords, key=lambda x: x[2])

    midx = get_center_between_points(minx, maxx)
    midy = get_center_between_points(miny, maxy)
    midz = get_center_between_points(minz, maxz)

    mid = Vector((midx[0], midy[1], midz[2]))

    bbox = [Vector((minx.x, miny.y, minz.z)), Vector((maxx.x, miny.y, minz.z)),
            Vector((maxx.x, maxy.y, minz.z)), Vector((minx.x, maxy.y, minz.z)),
            Vector((minx.x, miny.y, maxz.z)), Vector((maxx.x, miny.y, maxz.z)),
            Vector((maxx.x, maxy.y, maxz.z)), Vector((minx.x, maxy.y, maxz.z))]

    return bbox, mid


def get_right_and_up_axes(context, mx):
    r3d = context.space_data.region_3d

    # get view right (and up) vectors in 3d space
    view_right = r3d.view_rotation @ Vector((1, 0, 0))
    view_up = r3d.view_rotation @ Vector((0, 1, 0))

    # get the right and up axes depending on the matrix that was passed in (object's local space, world space, etc)
    axes_right = []
    axes_up = []

    for idx, axis in enumerate([Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]):
        dot = view_right.dot(mx.to_3x3() @ axis)
        axes_right.append((dot, idx))

        dot = view_up.dot(mx.to_3x3() @ axis)
        axes_up.append((dot, idx))

    axis_right = max(axes_right, key=lambda x: abs(x[0]))
    axis_up = max(axes_up, key=lambda x: abs(x[0]))

    # determine flip
    flip_right = True if axis_right[0] < 0 else False
    flip_up = True if axis_up[0] < 0 else False

    return axis_right[1], axis_up[1], flip_right, flip_up
