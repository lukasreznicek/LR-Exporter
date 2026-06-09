'''
Creates a uvs for mask and exports for painter

'''

import bpy,bmesh

uv_layer_mask_name = 'uv_mask'
def main(self, context):
    objs = self._preprocess_obj_duplicates

    # Store selection
    selected_objects = [obj for obj in bpy.context.selected_objects]
    
    for obj in objs:
        if obj.type != 'MESH':
            continue
        

        # Realize instances 
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        

        found=False
        for uv_layer in obj.data.uv_layers:
            if uv_layer.name == uv_layer_mask_name:
                found=True
                break
        if not found:
            uv_layer = obj.data.uv_layers.new(name=uv_layer_mask_name)

        # Copy uvs from uv0 to uv_mask
        uv_layer_mask = obj.data.uv_layers[uv_layer_mask_name]
        uv_layer_uv0 = obj.data.uv_layers[0]
        
        for loop in obj.data.loops:
            uv_layer_mask.data[loop.index].uv = uv_layer_uv0.data[loop.index].uv

        # Make uv mask active
        obj.data.uv_layers.active = uv_layer_mask


    store_uv_sync = bpy.context.scene.tool_settings.use_uv_select_sync
    
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objs:
        if obj.type == 'MESH':
            obj.select_set(True)    


    # pack uv mask and switch to edit mode to update uv editor
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')

    #Select all polygons to pack all uv islands
    bpy.context.scene.tool_settings.use_uv_select_sync = True
    bpy.ops.mesh.select_all(action='SELECT')  

    bpy.ops.uv.pack_islands(margin=0.001)


    #Restore uv sync state
    bpy.context.scene.tool_settings.use_uv_select_sync = store_uv_sync
    
    # Restore selection
    bpy.ops.object.mode_set(mode='OBJECT')
    for obj in selected_objects:
        obj.select_set(True)