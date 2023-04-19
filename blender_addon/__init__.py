bl_info = {
    "name": "Nuke Export Panel",
    "description": "Create compositor nodes for Nuke export",
    "author": "Roland Kay",
    "version": (0, 0, 1),
    "blender": (3, 4, 1),
    "location": "Output > Nuke Export Settings ",
    "support": "COMMUNITY",
    "category": "Render"}

from . import nuke_export_panel

def register():
	nuke_export_panel.register()


def unregister():
	nuke_export_panel.unregister()

if __name__ == "__main__":
    register()
