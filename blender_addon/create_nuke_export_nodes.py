"""Functions to create compositor node setups to export render layers for compositing in Nuke

"""

import os
import bpy


def turn_on_aovs(scene, view_layer_name):
    """Enable all the AOVs that we will be exporting for the given view layer"""
    view_layer = scene.view_layers[view_layer_name]
    view_layer.use_pass_cryptomatte_object = True
    view_layer.use_pass_cryptomatte_material = True
    view_layer.use_pass_cryptomatte_asset = True
    view_layer.use_pass_glossy_direct = True
    view_layer.use_pass_glossy_indirect = True
    view_layer.use_pass_glossy_color = True
    view_layer.use_pass_diffuse_direct = True
    view_layer.use_pass_diffuse_indirect = True
    view_layer.use_pass_diffuse_color = True
    view_layer.use_pass_z = True
    view_layer.use_pass_mist = True
    view_layer.use_pass_transmission_direct = True
    view_layer.use_pass_transmission_indirect = True
    view_layer.use_pass_transmission_color = True
    view_layer.use_pass_emit = True
    view_layer.use_pass_environment = True
    view_layer.use_pass_shadow = True
    view_layer.use_pass_position = True
    view_layer.use_pass_normal = True

def create_file_output_node(scene, base_path, view_layer_name):
    """Create a file output node to export the image (i.e. not data) layers
    
    These layers can be compressed with DWAA compression.
    """
    file_output_node = scene.node_tree.nodes.new("CompositorNodeOutputFile")
    
    file_output_node.file_slots.clear()
    file_output_node.file_slots.new("rgba")  # 0
    file_output_node.file_slots.new("alpha") # 1
    file_output_node.file_slots.new("depth") # 2
    file_output_node.file_slots.new("mist") # 3
    file_output_node.file_slots.new("diffuse_direct") # 4
    file_output_node.file_slots.new("diffuse_indirect") # 5
    file_output_node.file_slots.new("diffuse_color") # 6
    file_output_node.file_slots.new("gloss_direct") # 7
    file_output_node.file_slots.new("gloss_indirect") # 8
    file_output_node.file_slots.new("gloss_color") # 9
    file_output_node.file_slots.new("transmission_direct") # 10
    file_output_node.file_slots.new("transmission_indirect") # 11
    file_output_node.file_slots.new("transmission_color") # 12
    file_output_node.file_slots.new("emission") # 13
    file_output_node.file_slots.new("environment") # 14
    file_output_node.file_slots.new("shadow") # 15
     
    file_output_node.file_slots[0].path = "rgba"

    file_output_node.format.file_format = "OPEN_EXR_MULTILAYER"
    file_output_node.format.color_depth = "32"
    file_output_node.format.exr_codec = "DWAA"
    file_output_node.format.color_management = "OVERRIDE"
    file_output_node.format.linear_colorspace_settings.name = "Linear"
    
    file_output_node.base_path = base_path

    # Setup custom attributes for the render manager
    file_output_node["nuke_view_layer_name"] = view_layer_name
    file_output_node["nuke_node_type"] = "image"
    
    return file_output_node
    
def create_data_output_node(scene, base_path, view_layer_name):
    """Create a file output node to export the data (i.e. non-image data) layers
    
    These layers must be compressed with a lossless compression algo.
    """

    data_output_node = scene.node_tree.nodes.new("CompositorNodeOutputFile")
    
    
    data_output_node.file_slots.clear()
    data_output_node.file_slots.new("position") # 0
    data_output_node.file_slots.new("normal") # 1
    data_output_node.file_slots.new("CryptoObject") # 2
    data_output_node.file_slots.new("CryptoObject00") # 3
    data_output_node.file_slots.new("CryptoObject01") # 4
    data_output_node.file_slots.new("CryptoObject02") # 5

    data_output_node.format.file_format = "OPEN_EXR_MULTILAYER"
    data_output_node.format.color_depth = "32"
    data_output_node.format.exr_codec = "ZIP"
    data_output_node.format.color_management = "OVERRIDE"
    data_output_node.format.linear_colorspace_settings.name = "Linear"
    
    data_output_node.base_path = base_path

    # Setup custom attributes for the render manager
    data_output_node["nuke_view_layer_name"] = view_layer_name
    data_output_node["nuke_node_type"] = "data"
    
    return data_output_node

def create_multi_exposure_group(scene):
    """Create a group that allows the exposure of multiple channels to be controlled at once
    
    When using physically-accurate lighting values, we typically have to turn down the camera
    exposure, but this is not reflected in all the exported layers, leading to them being far
    too hot. Correcting this avoid adding extra grade nodes to the compositor
    
    """
    try:
        return bpy.data.node_groups["RJK_MultiExposure"]
    except KeyError:
        pass
    
    group = bpy.data.node_groups.new("RJK_MultiExposure", "CompositorNodeTree")
        
    group_in = group.nodes.new("NodeGroupInput")
    group_in.location = (-200,0)
        
    group.inputs.new("NodeSocketFloat", "Exposure")
    group.inputs.new("NodeSocketColor", "rgba")
    group.inputs.new("NodeSocketColor", "diffuse_direct")
    group.inputs.new("NodeSocketColor", "diffuse_indirect")
    group.inputs.new("NodeSocketColor", "diffuse_color")
    group.inputs.new("NodeSocketColor", "gloss_direct")
    group.inputs.new("NodeSocketColor", "gloss_indirect")
    group.inputs.new("NodeSocketColor", "gloss_color")
    group.inputs.new("NodeSocketColor", "transmission_direct")
    group.inputs.new("NodeSocketColor", "transmission_indirect")
    group.inputs.new("NodeSocketColor", "transmission_color")
    group.inputs.new("NodeSocketColor", "emission")
    group.inputs.new("NodeSocketColor", "environment")
    group.inputs.new("NodeSocketColor", "shadow")
       
    group_out = group.nodes.new("NodeGroupOutput")
    group_out.location = (1000,0)
       
    group.outputs.new("NodeSocketColor", "rgba")
    group.outputs.new("NodeSocketColor", "diffuse_direct")
    group.outputs.new("NodeSocketColor", "diffuse_indirect")
    group.outputs.new("NodeSocketColor", "diffuse_color")
    group.outputs.new("NodeSocketColor", "gloss_direct")
    group.outputs.new("NodeSocketColor", "gloss_indirect")
    group.outputs.new("NodeSocketColor", "gloss_color")
    group.outputs.new("NodeSocketColor", "transmission_direct")
    group.outputs.new("NodeSocketColor", "transmission_indirect")
    group.outputs.new("NodeSocketColor", "transmission_color")
    group.outputs.new("NodeSocketColor", "emission")
    group.outputs.new("NodeSocketColor", "environment")
    group.outputs.new("NodeSocketColor", "shadow")
        
    exposure_nodes = [ group.nodes.new("CompositorNodeExposure") for i in range(13) ]
    for i, node in enumerate(exposure_nodes):
        node.location = (0, -i * 150)
        node.inputs["Exposure"]
        group.links.new(group_in.outputs["Exposure"], node.inputs["Exposure"] )
        group.links.new(group_in.outputs[i+1], node.inputs["Image"])
        group.links.new(node.outputs["Image"], group_out.inputs[i])
        
    return group
       
    
def setup_nodes(scene, view_layer_name, image_base_path, data_base_path):
    """Setup and connect all the nodes needed to export multi-layer EXR for Nuke"""
    
    # Create a group that controls the exposure on multiple channels
    create_multi_exposure_group(scene)
    
    render_layers_node = scene.node_tree.nodes.new("CompositorNodeRLayers")
    file_output_node = create_file_output_node(scene, image_base_path, view_layer_name)
    data_output_node = create_data_output_node(scene, data_base_path, view_layer_name)
    
    multi_exposure_node = scene.node_tree.nodes.new("CompositorNodeGroup")
    multi_exposure_node.node_tree = bpy.data.node_groups["RJK_MultiExposure"]
    multi_exposure_node.name = "RJK_MultiExposure"
    
    render_layers_node.layer = view_layer_name
    
    links = scene.node_tree.links

    links.new(multi_exposure_node.inputs["rgba"], render_layers_node.outputs["Image"])
    links.new(multi_exposure_node.inputs["diffuse_direct"], render_layers_node.outputs["DiffDir"])
    links.new(multi_exposure_node.inputs["diffuse_indirect"], render_layers_node.outputs["DiffInd"])
    links.new(multi_exposure_node.inputs["diffuse_color"], render_layers_node.outputs["DiffCol"])
    links.new(multi_exposure_node.inputs["gloss_direct"], render_layers_node.outputs["GlossDir"])
    links.new(multi_exposure_node.inputs["gloss_indirect"], render_layers_node.outputs["GlossInd"])
    links.new(multi_exposure_node.inputs["gloss_color"], render_layers_node.outputs["GlossCol"])
    links.new(multi_exposure_node.inputs["transmission_direct"], render_layers_node.outputs["TransDir"])
    links.new(multi_exposure_node.inputs["transmission_indirect"], render_layers_node.outputs["TransInd"])
    links.new(multi_exposure_node.inputs["transmission_color"], render_layers_node.outputs["TransCol"])
    links.new(multi_exposure_node.inputs["emission"], render_layers_node.outputs["Emit"])
    links.new(multi_exposure_node.inputs["environment"], render_layers_node.outputs["Env"])
    links.new(multi_exposure_node.inputs["shadow"], render_layers_node.outputs["Shadow"])
    
    links.new(file_output_node.inputs["rgba"], multi_exposure_node.outputs["rgba"])
    links.new(file_output_node.inputs["alpha"], render_layers_node.outputs["Alpha"])
    links.new(file_output_node.inputs["depth"], render_layers_node.outputs["Depth"])
    links.new(file_output_node.inputs["mist"], render_layers_node.outputs["Mist"])
    links.new(file_output_node.inputs["diffuse_direct"], multi_exposure_node.outputs["diffuse_direct"])
    links.new(file_output_node.inputs["diffuse_indirect"], multi_exposure_node.outputs["diffuse_indirect"])
    links.new(file_output_node.inputs["diffuse_color"], multi_exposure_node.outputs["diffuse_color"])
    links.new(file_output_node.inputs["gloss_direct"], multi_exposure_node.outputs["gloss_direct"])
    links.new(file_output_node.inputs["gloss_indirect"], multi_exposure_node.outputs["gloss_indirect"])
    links.new(file_output_node.inputs["gloss_color"], multi_exposure_node.outputs["gloss_color"])
    links.new(file_output_node.inputs["transmission_direct"], multi_exposure_node.outputs["transmission_direct"])
    links.new(file_output_node.inputs["transmission_indirect"], multi_exposure_node.outputs["transmission_indirect"])
    links.new(file_output_node.inputs["transmission_color"], multi_exposure_node.outputs["transmission_color"])
    links.new(file_output_node.inputs["emission"], multi_exposure_node.outputs["emission"])
    links.new(file_output_node.inputs["environment"], multi_exposure_node.outputs["environment"])
    links.new(file_output_node.inputs["shadow"], multi_exposure_node.outputs["shadow"])
    
    
    links.new(data_output_node.inputs["position"], render_layers_node.outputs["Position"])
    links.new(data_output_node.inputs["normal"], render_layers_node.outputs["Normal"])
    
    links.new(data_output_node.inputs["CryptoObject"], render_layers_node.outputs["Image"])
    links.new(data_output_node.inputs["CryptoObject00"], render_layers_node.outputs["CryptoObject00"])
    links.new(data_output_node.inputs["CryptoObject01"], render_layers_node.outputs["CryptoObject01"])
    links.new(data_output_node.inputs["CryptoObject02"], render_layers_node.outputs["CryptoObject02"])
    
    # Position and colour nodes
    #
    Vector = render_layers_node.location.__class__
    Color = render_layers_node.color.__class__

    # Find left-most node/bottom-most node
    x = min ( node.location[0] for node in scene.node_tree.nodes )
    y = min ( (node.location[1] - node.dimensions[1]) for node in scene.node_tree.nodes )

    render_layers_node.location = Vector((x, y))
    file_output_node.location = render_layers_node.location + Vector((1000,0))
    multi_exposure_node.location = render_layers_node.location + Vector((500,0))
    data_output_node.location = file_output_node.location - Vector((0, 500))
    file_output_node.color = Color((0.22664183378219604, 0.5925127267837524, 0.6079999804496765))
    data_output_node.color = Color((0.22664183378219604, 0.5925127267837524, 0.6079999804496765))
    file_output_node.use_custom_color = True
    data_output_node.use_custom_color = True
    
    # Setup a driver to link the exposure to the color management setting.
    # - https://blender.stackexchange.com/questions/39127/how-to-put-together-a-driver-with-python#39129
    # - https://docs.blender.org/api/current/bpy.types.DriverTarget.html
    #
    d = multi_exposure_node.inputs["Exposure"].driver_add("default_value").driver
    v = d.variables.new()
    v.name = "exposure"
    v.targets[0].id_type = "SCENE"
    v.targets[0].id = scene
    v.targets[0].data_path = "view_settings.exposure"
    d.expression = "exposure"
    

def create_nuke_export_compositor_nodes_for_view_layer(render_dir, view_layer_name, shot_name, slate_number):
    scene = bpy.data.scenes[0]    

    # Compile render output directory
    view_layer_sub_dir_name = (view_layer_name[3:] if view_layer_name.startswith("RL_") else view_layer_name).lower()
    base_path = os.path.join(render_dir, 
                             shot_name,
                             "slate %s" % slate_number, 
                             view_layer_sub_dir_name
                            )

    image_base_path = os.path.join(base_path,
                                   shot_name.replace("_","") +"_" + view_layer_sub_dir_name.replace("_","") + "_s" + str(slate_number) + "_"
                                  )

    data_base_path = os.path.join(base_path,
                                   shot_name.replace("_","") +"_" + view_layer_sub_dir_name.replace("_","") + "_data_s" + str(slate_number) + "_"
                                  )


    scene.use_nodes = True


    print("Turning on CYCLES")
    scene.render.engine = "CYCLES"
    
    print("Turning on AOVs")
    turn_on_aovs(scene, view_layer_name)

    print("Setting up nodes")
    setup_nodes(scene, view_layer_name, image_base_path, data_base_path)


#scene = bpy.data.scenes[0]    
#scene.use_nodes = True


#print("Turning on CYCLES")
#scene.render.engine = "CYCLES"
    
#print("Turning on AOVs")
#turn_on_aovs(scene, VIEW_LAYER_NAME)

#print("Setting up nodes")
#setup_nodes(scene, VIEW_LAYER_NAME, BASE_PATH)
    
