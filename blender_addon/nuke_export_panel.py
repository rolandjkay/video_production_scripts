"""Nuke export panel

Add a sub-panel to the output properties panal to make it easy to create compositor node setups
to export render layers for compositing in Nuke.

Configure the shot name and slate number. Then choose the view layer name and hit "Create Nuke export nodes"
to create the compositor nodes.


"""
import bpy
import sys
from . import create_nuke_export_nodes


class CreateNukeExportNodesOperator(bpy.types.Operator):
    
    bl_idname = 'opr.nuke_export_nodes_createor_operator'
    bl_label = 'Nuke Export Nodes Creator'
    
    def execute(self, context):
        params = (
            context.scene.nuke_export_view_layer_name_to_setup,
        )
        
        create_nuke_export_nodes.create_nuke_export_compositor_nodes_for_view_layer(
                context.scene.nuke_export_view_layer_name_to_setup, 
                context.scene.shot_name, 
                context.scene.slate_number
        )
            
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
        row.prop(scene, "shot_name")
        
        row = layout.row()
        row.prop(scene, "slate_number")

        layout.label(text="Setup Export Nodes")

        row = layout.row()
        row.prop(scene, "nuke_export_view_layer_name_to_setup")
 
        # Big render button
        layout.label(text="Big Button:")
        row = layout.row()
        row.scale_y = 3.0
        row.operator("opr.nuke_export_nodes_createor_operator", text="Create Nuke export nodes")

# Register
#
#

CLASSES = [
    CreateNukeExportNodesOperator,
    NukeExportPanel,
]

PROPS = [
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
