# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import bpy,os
import pathlib




bl_info = {
    "name" : "LR exporter",
    "author" : "Lukas Reznicek",
    "description" : "",
    "blender" : (2, 80, 0),
    "version" : (1, 1, 0),
    "location" : "",
    "warning" : "",
    "category" : "Generic"
}


addon_name = 'lr_export'

dir_name_scripts = "scripts"
dir_name_prepro_scripts = "scripts_preprocess"

from .operators.operators import OBJECT_OT_lr_hierarchy_exporter, OBJECT_OT_store_object_data_json,OBJECT_OT_lr_pack_uvs,OBJECT_OT_lr_reimport, OT_OpenScriptsFolder
# from .operators.wrappers import lr_export_one_material,lr_exportformask
from bpy.props import IntProperty, CollectionProperty, StringProperty,FloatVectorProperty,BoolProperty,EnumProperty

import importlib.util
from pathlib import Path
# import ui.ui as ui
from . import addon_ui
from .shared import PYTHON_SCRIPT_MODULES, PYTHON_PREPRO_SCRIPT_MODULES

def load_module(path):
    path = Path(path)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_modules_from_dir(directory: pathlib.Path, registry: dict):
    for i, file in enumerate(directory.iterdir(), start=1):
        if file.is_file() and file.suffix == ".py":
            path = pathlib.Path(file)

            # Build spec + module
            spec = importlib.util.spec_from_file_location(path.stem, path)
            module = importlib.util.module_from_spec(spec)

            try:
                spec.loader.exec_module(module)
            except Exception as e:
                print(f"[LR Exporter] Failed to load {path.name}: {e}")
                continue

            # Attach metadata
            module.__file__ = str(path)
            module.__filename__ = path.stem
            module.__folder__ = str(path.parent)
            module.__foldername__ = path.parent.name

            # Tooltip = module docstring or empty
            tooltip = module.__doc__ or ""

            # Build enum item
            enum_item = (
                file.name,      # identifier
                file.stem,      # display name
                tooltip,        # tooltip
                "FILE_SCRIPT",  # icon
                i               # index
            )

            # Store in registry
            registry[path.name] = {
                "module": module,
                "enum_item": enum_item
            }



addon_keymaps = []
wm = bpy.context.window_manager
kc = wm.keyconfigs.addon
def register_keymap(
    space_type="EMPTY",       # e.g. 'VIEW_3D', 'NODE_EDITOR', 'IMAGE_EDITOR'
    region_type="WINDOW",     # usually 'WINDOW'
    keymap_name="3D View",    # e.g. '3D View', 'Mesh', 'Object Mode'
    operator="wm.call_menu",  # operator idname
    key="A",                  # keyboard key
    event="PRESS",            # PRESS, RELEASE, CLICK, etc.
    shift=False,
    ctrl=False,
    alt=False,
    oskey=False,
    properties: dict | None = None # operator properties as dict
):
    """
    Registers a keymap item with full user control.
    Returns (km, kmi) so you can modify it further if needed.
    """

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return None, None

    # Get or create keymap
    km = kc.keymaps.get(keymap_name)
    if km is None:
        km = kc.keymaps.new(name=keymap_name, space_type=space_type, region_type=region_type)

    # Create keymap item
    kmi = km.keymap_items.new(
        operator,
        type=key,
        value=event,
        shift=shift,
        ctrl=ctrl,
        alt=alt,
        oskey=oskey)

    # Apply operator properties
    if properties:
        for prop, value in properties.items():
            setattr(kmi.properties, prop, value)

    addon_keymaps.append((km, kmi))
    return km, kmi



def unregister_keymap(addon_keymaps):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return

    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass  # item already removed or keymap missing

    addon_keymaps.clear()


class LR_Exporter_RefreshScripts(bpy.types.Operator):
    """Refresh scripts in exporter addon folder"""
    bl_idname = "wm.lr_exporter_refresh_scripts"
    bl_label = "Refresh scripts in LR Exporter"

    def execute(self, context):
        global PYTHON_SCRIPT_MODULES
        global PYTHON_PREPRO_SCRIPT_MODULES

        PYTHON_SCRIPT_MODULES.clear()
        PYTHON_PREPRO_SCRIPT_MODULES.clear()

        base = pathlib.Path(__file__).parent

        load_modules_from_dir(base / "scripts", PYTHON_SCRIPT_MODULES)
        load_modules_from_dir(base / "scripts_preprocess", PYTHON_PREPRO_SCRIPT_MODULES)

        return {'FINISHED'}







def get_addon_dir():
    return pathlib.Path(__file__).parent

def load_script_docstring(path):
    namespace = {"__name__": "lr_preview"} 

    with open(path, "r", encoding="utf-8") as f:
        code = f.read()

    exec(code, namespace)  # safe: guarded code won't run

    doc = namespace.get("__doc__", "")
    return doc.strip() if doc else ""

_script_cache = {}  # global: { path_str: { "mtime": float, "doc": str } }



def list_python_files(self, context):
    if not PYTHON_SCRIPT_MODULES: 
        return [("NONE", "No Script", "", "FILE_BLANK", 0)]
    return [("NONE", "No Script", "", "FILE_BLANK", 0)]+[entry["enum_item"] for entry in PYTHON_SCRIPT_MODULES.values()]

def list_python_preprocess_files(self, context):
    if not PYTHON_PREPRO_SCRIPT_MODULES: 
        return [("NONE", "No Script", "", "FILE_BLANK", 0)]
    return [("NONE", "No Script", "", "FILE_BLANK", 0)]+[entry["enum_item"] for entry in PYTHON_PREPRO_SCRIPT_MODULES.values()]


# Properties 
# To acess properties: bpy.data.scenes['Scene'].lr_export
# Is assigned by pointer property below in class registration.

class LR_ExportSettings_Scene(bpy.types.PropertyGroup):
    
    export_sm_prefix: bpy.props.StringProperty(name="Prefix", description="Prefix for exported file", default="SM_", maxlen=1024)
    export_sm_suffix:bpy.props.StringProperty(name="Suffix", description="Suffix for exported file", default="", maxlen=1024)
    export_mask_sm_suffix:bpy.props.StringProperty(name="Obj Suffix", description="Suffix for exported mask file", default="_ForMask", maxlen=1024,)
    # export_mask_uv_name:bpy.props.StringProperty(name="UV", description="UV With this name will be kept", default="UV_All", maxlen=1024,)
    export_path:bpy.props.StringProperty(name="Path", description="// = .blend file location\n//..\ = .blend file parent folder", default="//..\\", maxlen=1024,subtype='DIR_PATH',options={'PATH_SUPPORTS_BLEND_RELATIVE'})


    
    export_type:bpy.props.EnumProperty(name= 'Export Type', description= '', items= [('OP1', 'Option 1',''),('OP2', 'Option 2',''),('OP3', 'Option 3','')])
    add_missing_hp: bpy.props.BoolProperty(name="Add Missing HP",description= 'Select one _LP and _HP object. Exporter goes through all children with _HP/_LP and matches them by name. Then adds missing _HP objects. \n Useful when some object dont need high poly but still need to be baked', default=False)
    send_payload: bpy.props.BoolProperty(name="Send Request to UE", default=False,description= 'Requires Unreal’s communication listener to be active.\nSends json file containing export information. Unreal Engine will take that data and use it for import setup.')
    # export_full_hierarchy: bpy.props.BoolProperty(name="Full Hierarchy  ",description='True: Children and all parent objects are exported. FBX name/settings is taken from upper most object in hierarchy.\nFalse: Selected and children objects are exported', default=True)
    export_hidden: bpy.props.BoolProperty(name="Export Hidden",description='True: Export hidden objects in hierarchy', default=True)
    
    lr_assembly_replace_file: bpy.props.BoolProperty(name="Replace File", default=True)
    lr_assembly_filename: bpy.props.StringProperty(name="JSON filename", default = 'Assembly')
    
    

    #Importer
    lr_import_remove_mesh: bpy.props.BoolProperty(name="Remove mesh as well",description= '', default=False)# type: ignore
    lr_import_material_cleanup: bpy.props.BoolProperty(name="Clean Materials",description= '', default=True)# type: ignore
    
    

def make_relative(self, context):
    # Get the current value of lr_import_path
    file_path = getattr(self.object.lr_object_export_settings, "lr_import_path")
    
    # Make the path relative to the blend file
    blend_file_path = bpy.data.filepath
    relative_path = bpy.path.relpath(file_path, blend_file_path)
    
    # Update the property with the relative path
    setattr(self.object.lr_object_export_settings, "lr_import_path", relative_path)
#UI -------------------------------------------------------------------------------------
class LR_ExportSettings_Object(bpy.types.PropertyGroup):

    object_mode:bpy.props.EnumProperty(
        name="Export mode",
        description="Export mode",
        override={'LIBRARY_OVERRIDABLE'},
        items=[
            ("PARENT","Export Node","Export this object and its children","EMPTY_ARROWS",1),
            ("AUTO", "Exported", "Object is included in export if in hierarchy.","BOIDS",2),
            ("NOT_EXPORTED","Ignored","Object is excluded from export.","X",3),
            ("MASK_EXPORT","Mask Only","Object is exported only fro mask","MOD_MASK",4)
            ],
            default="AUTO"
        ) # type: ignore

    lr_exportsubfolder:bpy.props.StringProperty(
        name="Sub Folder",
        description=("(Optional) Each exported object can have additional folder location. Value in this input is added on top of the 'Path:' in Scene Settings\nExample: Modules\\Ceiling"
            ),
        override={'LIBRARY_OVERRIDABLE'},
        maxlen=64,
        default="",
        subtype='FILE_NAME'
        )# type: ignore


    #For mask export
    lr_mat_override_mask:bpy.props.StringProperty(
        name="Mat Override",
        description=(
            '(Optional, Object Setting)\n\nRemoves all materials and assigns a new one.\nIf empty, nothing is changed\n-Set only on child objects and not parent empty'
            ),
        # override={'LIBRARY_OVERRIDABLE'},
        maxlen=64,
        default="",
        # subtype='FILE_NAME'
        )# type: ignore
    #For mask export
    lr_uv_isolate_mask:bpy.props.StringProperty(
        name="Keep UV",
        description=(
            '(Optional, Object Setting)\n\nDeletes all UVs except one specified.\n-If empty, nothing is changed.\n-All child objects take highest parent value if not specified'
            ),
        maxlen=64,
        default="",)# type: ignore

    processing_orig_name:bpy.props.StringProperty(
        name="orig_name",
        description=(""),
        maxlen=64,
        default="",)# type: ignore
    processing_original:bpy.props.BoolProperty(
        name="Clear Location",
        description=('To identify if object during export is original or duplicate'),
        default=False
        )# type: ignore

    lr_export_reset_position:bpy.props.BoolProperty(
        name="Clear Location",
        description=('Reset location before export'),
        default=True
        )# type: ignore

    lr_export_reset_rotation:bpy.props.BoolProperty(
        name="Clear Rotation",
        description=('Reset rotation before export'),
        default=True
        )# type: ignore

    #UV Manipulation settings
    uvs_index: bpy.props.IntProperty(name="UV Index", description="Operations below will be applied to this Index. If index is missing it will be added automtically. Duplicates UV 1", default=2, min = 1, soft_max = 5)# type: ignore
    uvs_unwrap: bpy.props.BoolProperty(name="Unwrap UVs",description= 'Unwrap UVs during export', default=False)# type: ignore
    uvs_unwrap_method: bpy.props.EnumProperty(name= 'Method', 
                                              description= '', 
                                              items= [('ANGLE_BASED', 'Angle Based',''),
                                                      ('CONFORMAL', 'Conformal','')])# type: ignore
    uvs_unwrap_margin: bpy.props.FloatProperty(name="Unwrap Margin", default=0.001, min = 0, max = 1)# type: ignore
    uvs_average_scale: bpy.props.BoolProperty(name="Average UVs",description= 'Average scale on UVs during export', default=False)# type: ignore
    uvs_pack: bpy.props.BoolProperty(name="Pack UVs",description= 'Pack UVs during export', default=False)# type: ignore
    uvs_pack_margin: bpy.props.FloatProperty(name="Pack Margin", default=0.001, min = 0, max = 1)# type: ignore

    #Importer
    lr_import_path:bpy.props.StringProperty(
        name="import_path",
        description=("Add path to .FBX file"),
        override={'LIBRARY_OVERRIDABLE'},
        maxlen=256,
        default="",
        subtype='FILE_PATH',
        )# type: ignore
    
    python_scripts:bpy.props.EnumProperty(name="Script",description="Select a Python script",items=list_python_files)
    python_scripts_prepro:bpy.props.EnumProperty(name="Script Prepro",description="Select a Python preprocess script",items=list_python_preprocess_files)


class VIEW3D_PT_lr_export(bpy.types.Panel):
    bl_label = "EXPORT"
    bl_idname = "OBJECT_PT_lr_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'LR Export'

    def draw(self, context):
        

        layout = self.layout.box()

        # Check if no object is selected
        if context.object is None:
            layout.label(text="Select an object", icon='INFO')
            return
        
        layout.label(text="Scene Settings:")
        lr_export_settings_scene = context.scene.lr_export_settings_scene
        lr_object_export_settings = context.object.lr_object_export_settings

        row = layout.column()
        row.prop(lr_export_settings_scene, "export_sm_prefix", slider=True)
        row.prop(lr_export_settings_scene, "export_sm_suffix")
        # row = layout.column()

        row.prop(lr_export_settings_scene, "export_path")
        # row = layout.row(align=True)        
        # row.prop(lr_export_settings_scene, "export_full_hierarchy")
        row.prop(lr_export_settings_scene, "export_hidden")
        row.prop(lr_export_settings_scene, "add_missing_hp")    
        row.prop(lr_export_settings_scene, "send_payload")  
        # layout.alignment = 'RIGHT'  # or 'LEFT', 'CENTER', 'RIGHT'


        # Object Settings
        layout = self.layout.box()
        layout.label(text='Object Settings:')
        row = layout.row(align=True)  
        if context.object:
            row.prop(context.object.lr_object_export_settings, 'object_mode', text="Mode", icon='OBJECT_DATA', emboss=True, expand=False, icon_only=False)
            # row = layout.column()


        row = layout.row(align=True)  
        if context.object:
            # row.alignment = 'RIGHT'
            row.prop(context.object.lr_object_export_settings,'lr_exportsubfolder')
            
        row = layout.column_flow(columns=2)
        row.prop(context.object.lr_object_export_settings,'lr_export_reset_position')
        row.prop(context.object.lr_object_export_settings,'lr_export_reset_rotation')
                 #Setting is avaliable on parent object only
        if lr_object_export_settings.object_mode == "PARENT" and context.object.parent is None and context.object.lr_object_export_settings.python_scripts == "NONE":
            row = layout.row(align=True)
            row.prop(lr_object_export_settings, "python_scripts_prepro")
            row.operator("wm.lr_exporter_refresh_scripts", text= "", icon= "FILE_REFRESH")
            op = row.operator("wm.lr_exporter_open_scripts_folder", text="", icon='FILE_FOLDER')
            op.subfolder = "scripts_preprocess"

        if lr_object_export_settings.object_mode == "PARENT" and context.object.lr_object_export_settings.python_scripts_prepro == "NONE":
            row = layout.row(align=True)
            row.prop(lr_object_export_settings, "python_scripts")
            row.operator("wm.lr_exporter_refresh_scripts", text= "", icon= "FILE_REFRESH")
            op = row.operator("wm.lr_exporter_open_scripts_folder", text="", icon='FILE_FOLDER')
            op.subfolder = "scripts"

        layout = self.layout.box()
        layout.scale_y = 2
        op_export = layout.operator("object.lr_exporter_export", text="Export", icon = 'EXPORT')
        op_export.export_hidden=lr_export_settings_scene.export_hidden
        
        row.separator()
        
class VIEW3D_PT_lr_importer(bpy.types.Panel):
    bl_label = "REIMPORTER"
    bl_idname = "OBJECT_PT_lr_importer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'LR Export'
    bl_options = {'DEFAULT_CLOSED'}
    

    def draw(self, context):
        '''File is saved next to a .blend file'''
        if context.object:
            lr_export_settings_scene = context.scene.lr_export_settings_scene
            lr_export_settings_object = context.object.lr_object_export_settings
        
        layout = self.layout.box()

        # Check if no object is selected
        if context.object is None:
            layout.label(text="Select an object", icon='INFO')
            return
        
        # # ------------ UV Manipulation ------------ ONLY IN Blender 4.1


        row = layout.row(align=True)
        row.scale_y = 1.5 
        row.prop(lr_export_settings_object,'lr_import_path', text="Path")
        # row = layout.row(align=True)
        if context.object.lr_object_export_settings.lr_import_path != "":
            #Object Settings
            header, panel = layout.panel("my_panel_id", default_closed=True)
            header.label(text="Settings Scene")
            if panel:
                panel.prop(lr_export_settings_scene,'lr_import_material_cleanup', text="Material Cleanup")
                panel.prop(lr_export_settings_scene,'lr_import_remove_mesh', text="Remove Mesh")
                
                # panel.label(text="Success")
        
        if context.object and context.object.lr_object_export_settings.lr_import_path != "":
            layout = self.layout.box()
            row = layout.row(align=True)
            row.scale_y = 2
            row.operator("object.lr_import", text="Reimport Selected", icon = 'IMPORT')


        # row.prop(lr_export_settings_scene, "lr_assembly_replace_file")
        # row = layout.row(align=True)
        # row.scale_y = 2
        # row.operator("object.lr_store_object_data_json", text="Export Placement", icon = 'EXPORT')

def on_load(dummy): 
    bpy.ops.wm.lr_exporter_refresh_scripts()

class VIEW3D_PT_lr_export_assembly(bpy.types.Panel):
    bl_label = "EXPORT ASSEMBLY"
    bl_idname = "OBJECT_PT_lr_export_assembly"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'LR Export'
    bl_options = {'DEFAULT_CLOSED'}
    

    def draw(self, context):
        '''File is saved next to a .blend file'''
        lr_export_settings_scene = context.scene.lr_export_settings_scene

        layout = self.layout.box()
        # layout.label(text="Settings")
        row = layout.row(align=True)
        
        row.prop(lr_export_settings_scene, "lr_assembly_filename")
        row.prop(lr_export_settings_scene, "lr_assembly_replace_file")
        row = layout.row(align=True)
        row.scale_y = 2
        row.operator("object.lr_store_object_data_json", text="Export Placement", icon = 'EXPORT')
        



classes = [LR_ExportSettings_Scene,
           LR_ExportSettings_Object,
           OBJECT_OT_lr_hierarchy_exporter,
           VIEW3D_PT_lr_export,#VIEW3D_PT_ObjectProperties,
        #    VIEW3D_PT_lr_Export_UV_Mainpulation,
           OBJECT_OT_lr_pack_uvs,
           OT_OpenScriptsFolder,
           
           #Importer
           VIEW3D_PT_lr_importer,
           OBJECT_OT_lr_reimport,

           #Export assembly 
           VIEW3D_PT_lr_export_assembly,
           OBJECT_OT_store_object_data_json,
           LR_Exporter_RefreshScripts,
           
           #UI
           addon_ui.lr_export_menu
           
           ]
# def add_to_object_context_menu(self, context):
#     if context.mode == 'OBJECT' and context.object:
#         layout = self.layout
#         layout.separator()
#         # layout.prop_menu_enum(context.object.lr_object_export_settings, "object_mode")

#         row = layout.column()
#         # row.prop(context.object.lr_object_export_settings, "object_mode", text="")
# # bpy.ops.object.lr_exporter_export(export_hidden=True, export_for_mask=False)
#         row.label(text="Exporter settings")
#         row.prop(
#             context.object.lr_object_export_settings,
#             "object_mode",
#             text="",
#             icon='OBJECT_DATA'
#         )
#         row.operator("object.lr_exporter_export", text="Export", icon = 'EXPORT')

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.lr_export_settings_scene = bpy.props.PointerProperty(type=LR_ExportSettings_Scene)
    bpy.types.Object.lr_object_export_settings = bpy.props.PointerProperty(type=LR_ExportSettings_Object)
    bpy.app.handlers.load_post.append(on_load)
    # bpy.types.VIEW3D_MT_object_context_menu.append(add_to_object_context_menu)
    register_keymap(keymap_name="Object Mode",key="E",shift=True,operator="wm.call_menu",properties={"name": "OBJECT_MT_lr_export_menu"})

def unregister():
    unregister_keymap(addon_keymaps)
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.lr_export_settings_scene
    del bpy.types.Object.lr_object_export_settings
    # bpy.types.VIEW3D_MT_object_context_menu.remove(add_to_object_context_menu)



# classes = [LR_ExportSettings_Scene,
#            LR_ExportSettings_Object,
#            OBJECT_OT_lr_hierarchy_exporter,
#            VIEW3D_PT_lr_export,#VIEW3D_PT_ObjectProperties,
#            VIEW3D_PT_lr_export_assembly,
#            VIEW3D_PT_lr_Export_UV_Mainpulation,
#            OBJECT_OT_store_object_data_json,
#            OBJECT_OT_lr_pack_uvs]

# def register():
#     for cls in classes:
#         bpy.utils.register_class(cls)
#     bpy.types.Scene.lr_export_settings_scene = bpy.props.PointerProperty(type=LR_ExportSettings_Scene)
#     bpy.types.Object.lr_object_export_settings = bpy.props.PointerProperty(type=LR_ExportSettings_Object)

# def unregister():
#     for cls in classes:
#         bpy.utils.unregister_class(cls)
#     del bpy.types.Scene.lr_export_settings_scene
#     del bpy.types.Object.lr_object_export_settings




