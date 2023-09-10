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
import bpy

bl_info = {
    "name" : "LR exporter",
    "author" : "Lukas Reznicek",
    "description" : "",
    "blender" : (2, 80, 0),
    "version" : (0, 0, 1),
    "location" : "",
    "warning" : "",
    "category" : "Generic"
}


addon_name = 'lr_export'

from .operators.operators import OBJECT_OT_lr_hierarchy_exporter, OBJECT_OT_store_object_data_json
from .operators.wrappers import lr_export_one_material,lr_exportformask
from bpy.props import IntProperty, CollectionProperty, StringProperty,FloatVectorProperty,BoolProperty,EnumProperty

# Properties 
# To acess properties: bpy.data.scenes['Scene'].lr_export
# Is assigned by pointer property below in class registration.
class lr_export_settings(bpy.types.PropertyGroup):
    
    export_sm_prefix: bpy.props.StringProperty(name="Prefix", description="Prefix for exported file", default="SM_", maxlen=1024,)
    export_sm_suffix:bpy.props.StringProperty(name="Suffix", description="Suffix for exported file", default="", maxlen=1024,)
    export_path:bpy.props.StringProperty(name="Export Path", description="// = .blend file location\n//..\ = .blend file parent folder", default="//..\\", maxlen=1024,subtype='DIR_PATH')
    export_type:bpy.props.EnumProperty(name= 'Export Type', description= '', items= [('OP1', 'Option 1',''),('OP2', 'Option 2',''),('OP3', 'Option 3','')])
    add_missing_hp: bpy.props.BoolProperty(name="Add Missing HP",description= 'Select one _LP and _HP object. Exporter goes through all children with _HP/_LP and matches them by name. Then adds missing _HP objects. \n Useful when some object dont need high poly but still need to be baked', default=False)
    export_full_hierarchy: bpy.props.BoolProperty(name="Full Hierarchy  ",description='Parent and child objects are exported', default=True)
    
    lr_assembly_replace_file: bpy.props.BoolProperty(name="Replace File", default=True)
    lr_assembly_filename: bpy.props.StringProperty(name="JSON filename", default = 'Assembly')
    
    # name_to_uv_index_set: bpy.props.StringProperty(name="  Name", description="Set uv index by name", default="UVMap Name", maxlen=1024,)
    # uv_map_rename: bpy.props.StringProperty(name="  To", description="Rename uv on selected objects", default="New Name", maxlen=1024,)
    # uv_map_delete_by_name: bpy.props.StringProperty(name="  Name", description="Name of the UV Map to delete on selected objects", default="UV Name", maxlen=1024,)
    # select_uv_index: bpy.props.IntProperty(name="  Index", description="UV Map index to set active on selected objects", default=1, min = 1, soft_max = 5)
    # remove_uv_index: bpy.props.IntProperty(name="Index to remove", description="UV Map index to remove on selected objects", default=1, min = 1, soft_max = 5)
    # vertex_color_offset_amount: bpy.props.FloatProperty(name="Offset amount", default=0.1, min = 0, max = 1)
    # lr_vc_swatch: FloatVectorProperty(name="object_color",subtype='COLOR',default=(1.0, 1.0, 1.0),min=0.0, max=1.0,description="color picker")
    # lr_vc_alpha_swatch: bpy.props.FloatProperty(name="Alpha Value", step = 5, default=0.5, min = 0, max = 1)

#UI -------------------------------------------------------------------------------------


 


class VIEW3D_PT_lr_export(bpy.types.Panel):
    bl_label = "EXPORT"
    bl_idname = "OBJECT_PT_lr_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'LR Export'

    bpy.types.Object.lr_export_type = EnumProperty(
        name="Export mode",
        description="Export mode",
        override={'LIBRARY_OVERRIDABLE'},
        items=[
            ("auto",
                "Auto",
                "Export with the parent if the parents is \"Export recursive\"",
                "BOIDS",
                1),
            ("export_recursive",
                "Export recursive",
                "Export self object and all children",
                "KEYINGSET",
                2),
            ("dont_export",
                "Not exported",
                "Will never export",
                "CANCEL",
                3)
            ]
        )

    bpy.types.Object.lr_exportsubfolder = StringProperty(
        name="Sub folder name",
        description=(
            'The name of sub folder.' +
            ' You can now use ../ for up one directory.'
            ),
        override={'LIBRARY_OVERRIDABLE'},
        maxlen=64,
        default="",
        subtype='FILE_NAME'
        )

    bpy.types.Object.lr_export_reset_position = BoolProperty(
        name="Move to zero",
        description=('Main object will be positioned to zero before exporting'),
        default=True
        )

    bpy.types.Object.lr_export_reset_rotation = BoolProperty(
        name="Reset Rotation",
        description=('Main object rotation will have rotation set to zero'),
        default=True
        )

    bpy.types.Object.lr_export_add_missing_hp = BoolProperty(
        name="Add missing HP",
        description=('Adds missing HP objects during export for baking. Detects _LP and _HP suffix.'),
        default=False
        )
    
 
    def draw(self, context):

        lr_export = context.scene.lr_export

        layout = self.layout.box()
        # layout.label(text="Settings")
        
        row = layout.column()
        row.prop(lr_export, "export_sm_prefix", slider=True)
        row.prop(lr_export, "export_sm_suffix")

        row = layout.column()
        

        row.prop(lr_export, "export_path")
        # row = layout.row(align=True)        
        if context.object:
            row.prop(context.object,'lr_exportsubfolder')
        
        row.separator()
        
        row = layout.column_flow(columns=1)
        if context.object:
            row.prop(context.object,'lr_export_reset_position')
            row.prop(context.object,'lr_export_reset_rotation')

        # row = layout.row(align=True)
        if context.object:
            row.prop(lr_export, "add_missing_hp")
            
        # row = layout.row(align=True)
        row.prop(lr_export, "export_full_hierarchy")
        
        layout = self.layout.box()
        # layout.label(text="Export")
        row = layout.row(align=True)
        row.scale_y = 2
        row.operator("object.lr_exporter_export", text="Export", icon = 'EXPORT')
    
        # layout = self.layout.box()
        # layout.label(text='Export modes')

        row = layout.column_flow()
        row.scale_y = 1
        row.operator("object.lr_export_one_material", text="Export one Mat", icon = 'EXPORT')
        
        
        # row = layout.row(align=True)
        row.scale_y = 1
        row.operator("object.lr_exportformask", text="Export for mask", icon = 'EXPORT')
        



class VIEW3D_PT_lr_export_assembly(bpy.types.Panel):
    bl_label = "EXPORT ASSEMBLY"
    bl_idname = "OBJECT_PT_lr_export_assembly"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'LR Export'


    def draw(self, context):
        '''File is saved next to a .blend file'''
        lr_export = context.scene.lr_export

        layout = self.layout.box()
        # layout.label(text="Settings")
        row = layout.row(align=True)
        
        row.prop(lr_export, "lr_assembly_filename")
        row.prop(lr_export, "lr_assembly_replace_file")
        row = layout.row(align=True)
        row.scale_y = 2
        row.operator("object.lr_store_object_data_json", text="Export Placement", icon = 'EXPORT')

classes = [lr_export_settings,OBJECT_OT_lr_hierarchy_exporter,VIEW3D_PT_lr_export, VIEW3D_PT_lr_export_assembly, OBJECT_OT_store_object_data_json, lr_export_one_material, lr_exportformask]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        bpy.types.Scene.lr_export = bpy.props.PointerProperty(type=lr_export_settings)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.lr_export
