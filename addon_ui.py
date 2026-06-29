
import bpy 

class lr_export_menu(bpy.types.Menu):
    bl_label = "LR Exporter"
    bl_idname = "OBJECT_MT_lr_export_menu"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.separator()
        row.separator()
        # row = layout.row()
        # row.operator("object.lr_export_operator", text="Export to Lightroom")
        # layout.prop(context.object.lr_object_export_settings, 'object_mode', icon='OBJECT_DATA', icon_only=False, emboss=True)
        col = layout.column()
        col.prop(context.object.lr_object_export_settings,'object_mode',icon='OBJECT_DATA',expand=False, emboss=True, text="")

        col = layout.column()
        col.separator()
        col.operator("object.lr_exporter_export", text="Export", icon = 'EXPORT')
        col.scale_y = 1.5