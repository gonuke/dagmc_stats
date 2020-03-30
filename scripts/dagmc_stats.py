# set the path to find the current installation of pyMOAB
import sys
import numpy as np

sys.path.append(
    '/opt/tljh/user/lib/moab/lib/python3.6/site-packages/pymoab-5.1.0-py3.6-linux-x86_64.egg')
from pymoab.rng import Range
from pymoab import core, types


def get_dagmc_tags(my_core):
    """
    Get a dictionary with the important tags for DAGMC geometries
    
    inputs
    ------
    my_core : a MOAB Core instance
    
    outputs
    -------
    dagmc_tags : a dictionary of relevant tags
    """

    dagmc_tags = {}

    dagmc_tags['geom_dim'] = my_core.tag_get_handle('GEOM_DIMENSION', size=1, tag_type=types.MB_TYPE_INTEGER,   
                                                    storage_type=types.MB_TAG_SPARSE, create_if_missing=True)  # geometric dimension

    dagmc_tags['category'] = my_core.tag_get_handle('CATEGORY', size=32, tag_type=types.MB_TYPE_OPAQUE,  
                                                    storage_type=types.MB_TAG_SPARSE, create_if_missing=True)  # the category

    dagmc_tags['global_id'] = my_core.tag_get_handle('GLOBAL_ID', size=1, tag_type=types.MB_TYPE_INTEGER,  

                                                     storage_type=types.MB_TAG_SPARSE, create_if_missing=True)  # id

    return dagmc_tags


def get_native_ranges(my_core, meshset, entity_types):
    """
    Get a dictionary with MOAB ranges for each of the requested entity types
    
    inputs
    ------
    my_core : a MOAB Core instance
    meshset : a MOAB meshset to query for the ranges of entities
    entity_types : a list of valid pyMOAB types to be retrieved
    
    outputs
    -------
    native_ranges : a dictionary with one entry for each entity type that is a
                    Range of handles to that type
    """

    native_ranges = {}
    for entity_type in entity_types:
        native_ranges[entity_type] = my_core.get_entities_by_type(
            meshset, entity_type)
    return native_ranges


def get_entityset_ranges(my_core, meshset, geom_dim):
    """
    Get a dictionary with MOAB Ranges that are specific to the types.MBENTITYSET
    type
    
    inputs
    ------
    my_core : a MOAB Core instance
    meshset : the root meshset for the file
    geom_dim : the tag that specifically denotes the dimesion of the entity
    
    outputs
    -------
    entityset_ranges : a dictionary with one entry for each entityset type, 
                       and the value is the range of entities that corrospond to each
                       type
    """
    
    entityset_ranges = {}
    entityset_types = ['Nodes', 'Curves', 'Surfaces', 'Volumes']
    for dimension, set_type in enumerate(entityset_types):
        entityset_ranges[set_type] = my_core.get_entities_by_type_and_tag(meshset, types.MBENTITYSET, geom_dim,
                                                                          [dimension])
    return entityset_ranges


def get_triangles_per_vertex(my_core, native_ranges):
    """
    This function will return data about the number of triangles on each
    vertex in a file
    
    inputs
    ------
    my_core : a MOAB Core instance
    native_ranges : a dictionary containing ranges for each native type in the file (VERTEX, TRIANGLE, ENTITYSET)
    
    outputs
    -------
    t_p_v_data : a list of the number of triangles each vertex touches
    """

    t_p_v_data = []
    tri_dimension = 2
    for vertex in native_ranges[types.MBVERTEX]:
        t_p_v_data.append(my_core.get_adjacencies(vertex, tri_dimension).size())
    return np.array(t_p_v_data)
  
  
def get_triangles_per_surface(my_core, entity_ranges):
    """
    This function will return data about the number of triangles on each
    surface in a file
    
    inputs
    ------
    my_core : a MOAB Core instance
    entity_ranges : a dictionary containing ranges for each type in the file 
                    (VOLUME, SURFACE, CURVE, VERTEX, TRIANGLE, ENTITYSET)
    
    outputs
    -------
    t_p_s : a dictionary containing the entityhandle of the surface,
            and the number of triangles each surface contains.
            i.e {surface entityhandle : triangles it contains}
    """

    t_p_s = {}
    for surface in entity_ranges['Surfaces']:
        t_p_s[surface] = my_core.get_entities_by_type(
                                 surface, types.MBTRI).size()
    return t_p_s

  
def get_surfaces_per_volume(my_core, entityset_ranges):
    """
    Get the number of surfaces that each volume in a given file contains
    
    inputs
    ------
    my_core : a MOAB core instance
    entity_ranges : a dictionary of the entityset ranges of each tag in a file
    
    outputs
    -------
    s_p_v : a dictionary containing the volume entityhandle
            and the number of surfaces each volume in the file contains
            i.e. {volume entityhandle:surfaces it contains}
    """

    s_p_v = {}
    for volumeset in entityset_ranges['Volumes']:
        s_p_v[volumeset] = my_core.get_child_meshsets(volumeset).size()
    return s_p_v


def get_tris(my_core, meshset, geom_dim):
    """
    Get triangles of a volume if geom_dim is 3
    Get triangles of a surface if geom_dim is 2
    Else get all the triangles

    inputs
    ------
    my_core : a MOAB core instance
    meshset : the root meshset for the file
    geom_dim : a MOAB Tag that holds the dimension of an entity.

    outputs
    -------
    tris : a list of triangle entities
    """

    # get triangles of a volume
    if my_core.tag_get_data(geom_dim, meshset)[0][0] == 3:
        entities = my_core.create_meshset()
        for surface in my_core.get_child_meshsets(meshset):
            my_core.add_entities(entities, my_core.get_entities_by_type(surface, types.MBTRI))
        tris = my_core.get_entities_by_type(entities, types.MBTRI)
    # get triangles of a surface
    elif my_core.tag_get_data(geom_dim, meshset)[0][0] == 2:
        entities = my_core.create_meshset()
        my_core.add_entities(entities, my_core.get_entities_by_type(meshset, types.MBTRI))
        tris = my_core.get_entities_by_type(entities, types.MBTRI)
    else:
    # get all the triangles
        tris = my_core.get_entities_by_type(meshset, types.MBTRI)
    return tris


def get_tri_side_length(my_core, tri):
    """
    Get side lengths of triangle

    inputs
    ------
    my_core : a MOAB Core instance
    tri : triangle entity

    outputs
    -------
    side_lengths : a list of side lengths of triangle
    """

    side_lengths = []
    s = 0
    coord_list = []

    verts = list(my_core.get_adjacencies(tri, 0))

    for vert in verts:
        coords = my_core.get_coords(vert)
        coord_list.append(coords)

    for side in range(3):
        side_lengths.append(np.linalg.norm(coord_list[side]-coord_list[side-2]))
        # The indices of coord_list includes the "-2" because this way each side will be matched up with both
        # other sides of the triangle (IDs: (Side 0, Side 1), (Side 1, Side 2), (Side 2, Side 0))
    return side_lengths


def get_triangle_aspect_ratio(my_core, meshset, geom_dim):
    """
    Get the triangle aspect ratio (according to the equation: (abc)/(8(s-a)(s-b)(s-c)), where s = .5(a+b+c).)

    inputs
    ------
    my_core : a MOAB Core instance
    meshset : a meshset containing a certain part of the mesh
    geom_dim : a MOAB Tag that holds the dimension of an entity.

    outputs
    -------
    t_a_r : (list) the triangle aspect ratios for triangles in the meshset
    """

    tris = get_tris(my_core, meshset, geom_dim)
    t_a_r = []

    for tri in tris:
        side_lengths = get_tri_side_length(my_core, tri)
        s = .5*(sum(side_lengths))
        top = np.prod(side_lengths)
        bottom = 8*np.prod(s-side_lengths)
        t_a_r.append(top/bottom)

    return t_a_r


def get_area_triangle(my_core, meshset, geom_dim):	
    """
    Get the triangle area (according to the Heron's formula: 
    sqrt(s(s - a)(s - b)(s - c)), where s = (a + b + c)/2)

    inputs
    ------
    my_core : a MOAB Core instance
    meshset : a meshset containing a certain part of the mesh
    geom_dim : a MOAB Tag that holds the dimension of an entity.
    
    outputs
    -------
    area : (list) the triangle areas in the meshset
    """

    area = []
    tris = get_tris(my_core, meshset, geom_dim)

    for tri in tris:
        side_lengths = get_tri_side_length(my_core, tri)
        # sqrt(s(s - a)(s - b)(s - c)), where s = (a + b + c)/2
        s = sum(side_lengths)/2
        s = np.sqrt(s * np.prod(s - side_lengths))
        area.append(s)

    return area


def get_coarseness(my_core, meshset, entity_ranges, geom_dim):
    """
    Get the coarseness of area. Coarseness is calculated by dividing 
    surface area of a surface by number of triangles in that surface.

    inputs
    ------
    my_core : a MOAB Core instance
    meshset : a meshset containing a certain part of the mesh
    entity_ranges : the surface entities
    geom_dim : a MOAB Tag that holds the dimension of an entity.

    outputs
    -------
    coarseness : (list) the coarseness for surfaces in the meshset.
    """

    coarseness = []
    
    for surface in entity_ranges:
        surf_area = get_area_triangle(my_core, surface, geom_dim)
        coarseness.append(len(surf_area)/sum(surf_area))

    return coarseness
