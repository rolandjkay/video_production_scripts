bl_info = {
    "name": "Nuke Export Panel",
    "description": "Create compositor nodes for Nuke export",
    "author": "Roland Kay",
    "version": (0, 0, 1),
    "blender": (3, 4, 1),
    "location": "Output > Nuke Export Settings ",
    "support": "COMMUNITY",
    "category": "Render"}


import bpy.app
from . import nuke_export_panel


def mute_file_output_nodes(scene, *args):
    for node in scene.node_tree.nodes:
        if node.type == "OUTPUT_FILE":
            node.mute = True


def register():
    nuke_export_panel.register()

    # Mute all File Output nodes when the render is complete;
    # to avoid accidentally overwriting frames when rendering stills.
    bpy.app.handlers.render_complete.append(mute_file_output_nodes)

def unregister():
    nuke_export_panel.unregister()

    try:
        bpy.app.handlers.render_complete.remove(mute_file_output_nodes)
    except ValueError:
        print("Failed to remove 'mute_file_output_nodes' handler")


if __name__ == "__main__":
    register()
