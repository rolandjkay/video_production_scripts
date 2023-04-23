"""Nuke export panel

Add a sub-panel to the output properties panal to make it easy to create compositor node setups
to export render layers for compositing in Nuke.

Configure the shot name and slate number. Then choose the view layer name and hit "Create Nuke export nodes"
to create the compositor nodes.


"""
import bpy
import sys, os, re

if __name__ == "__main__":
    import create_nuke_export_nodes
else:
    from . import create_nuke_export_nodes

class CreateNukeExportNodesOperator(bpy.types.Operator):
    
    bl_idname = 'opr.nuke_export_nodes_createor_operator'
    bl_label = 'Nuke Export Nodes Creator'
    
    def execute(self, context):
        params = (
            context.scene.nuke_export_view_layer_name_to_setup,
        )
        
        create_nuke_export_nodes.create_nuke_export_compositor_nodes_for_view_layer(
                context.scene.render_directory,
                context.scene.nuke_export_view_layer_name_to_setup, 
                context.scene.shot_name, 
                context.scene.slate_number
        )
            
        return {'FINISHED'}
    

class UpdateSlateNumberOperator(bpy.types.Operator):
    
    bl_idname = 'opr.slate_number_updater_operator'
    bl_label = 'Update the slate number of all File Output nodes and the default render output directory'
    
    def execute(self, context):
        params = (
            context.scene.shot_name,
            context.scene.slate_number,
        )

        # Update the default Blender output path based on our settings.
        #
        context.scene.render.filepath = os.path.join(context.scene.render_directory, 
                                                     context.scene.shot_name,
                                                     ("slate %d" % context.scene.slate_number),
                                                     context.scene.shot_name.replace("_","") + "_s" + str(context.scene.slate_number) + "_"
                                                     )

        # We capture to proceeding '/' or '\' and reproduce it in the replacement
        # string to, anally, avoid changing anything.
        def repl(m):
            path_sep = m.group(1)
            path_sep_end = m.group(2)
            return (path_sep + "slate %d" + path_sep_end) % context.scene.slate_number

        # set the base path for all file output nodes to filename:
        for scene in bpy.data.scenes:
            for node in scene.node_tree.nodes:
                if node.type == 'OUTPUT_FILE':
                    node.base_path = re.sub("([\\\/])slate [0-9]+([\\\/])", repl, node.base_path) 
                    node.base_path = re.sub("_s[0-9]+_", "_s" + str(context.scene.slate_number) + "_", node.base_path) 

        return {'FINISHED'}
    
class LaunchRenderOperator(bpy.types.Operator):
    
    bl_idname = 'opr.rjk_launch_render_operator'
    bl_label = 'Unmute file output nodes and launch render'

    def unmute_file_output_nodes(self, scene):
        for node in scene.node_tree.nodes:
            if node.type == "OUTPUT_FILE":
                node.mute = False
    
    def execute(self, context):
        self.unmute_file_output_nodes(context.scene)
        bpy.ops.render.render('INVOKE_DEFAULT', animation=True)
        return {'FINISHED'}
    

class NukeExportPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Nuke Export Settings"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        # Create a simple row.
        layout.label(text="Shot settings")

        row = layout.row()
        row.prop(scene, "render_directory")
        
        row = layout.row()
        row.prop(scene, "shot_name")
        
        row = layout.row()
        row.prop(scene, "slate_number")

        layout.label(text="Setup Export Nodes")

        row = layout.row()
        row.prop(scene, "nuke_export_view_layer_name_to_setup")
 
        # Big render button
        #layout.label(text="Big Button:")
        row = layout.row()
        row.scale_y = 2.0
        row.operator("opr.nuke_export_nodes_createor_operator", text="Create Nuke export nodes")

        row = layout.row()
        row.scale_y = 2.0
        row.operator("opr.slate_number_updater_operator", text="Update slate number")

        row = layout.row()
        row.scale_y = 3.0
        row.operator("opr.rjk_launch_render_operator", text="Render Animation")


# Register
#
#

CLASSES = [
    CreateNukeExportNodesOperator,
    UpdateSlateNumberOperator,
    LaunchRenderOperator,
    NukeExportPanel
]

PROPS = [
        ('render_directory', bpy.props.StringProperty(name='Render directory', default=r'\tmp')),
        ('shot_name', bpy.props.StringProperty(name='Shot name', default='my_shot')),
        ('slate_number', bpy.props.IntProperty(name='Slate number', default=1)),
        ('nuke_export_view_layer_name_to_setup', bpy.props.StringProperty(name='View layer name', default="ViewLayer")),
]


def register():
    for (prop_name, prop_value) in PROPS:
        setattr(bpy.types.Scene, prop_name, prop_value)
    
    for klass in CLASSES:
        bpy.utils.register_class(klass)


def unregister():
    for (prop_name, _) in PROPS:
        delattr(bpy.types.Scene, prop_name)

    for klass in CLASSES:
        bpy.utils.unregister_class(klass)


if __name__ == "__main__":
    register()
