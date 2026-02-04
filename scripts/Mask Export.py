"""
1. Removes "UCX_" prefixed objects from export.
2. Adds objects marked as "Mask Only" to the exported objects.
3. Assigns a single material "M_Mask" to all exported objects.
4. Retains only one UV map "UVMap"  per object.
"""
import bpy
def rename_obj(self, context):
    current_name = self.selection_capture.active_obj.name
    # self.selection_capture.active_obj.name = current_name+"_mask"

    selection = context.selected_objects
    for obj in selection:
        if obj.name.startswith("UCX_"):
            obj.select_set(False)
        

    for obj in self.selection_capture.selected_objs_for_mask_only:
        obj.select_set(True)
        print(f"Object {obj.name} selected for mask export.")

    objs_to_process = self.selection_capture.selected_objs_filtered + self.selection_capture.selected_objs_for_mask_only
    
    # ----------
    # Remove all UV maps except "UVMask" from objects marked as "Mask Only"
    # ----------
    keep_uv_name="UVMask"
        
    for obj in objs_to_process:
        if obj.type != 'MESH':
            continue

        if len(obj.data.uv_layers) == 1 and obj.data.uv_layers[0].name != keep_uv_name:
            print(f"Warning: Object {obj.name} has only one UV map named '{obj.data.uv_layers[0].name}', which is not '{keep_uv_name}'. It will be removed.")

        obj.data = obj.data.copy() #Remove Instancing

        count = 0
        if keep_uv_name in obj.data.uv_layers: 
            while len(obj.data.uv_layers) > 1:
                if obj.data.uv_layers[count].name == keep_uv_name:
                    count+=1
                    continue
                else:
                    obj.data.uv_layers.remove(obj.data.uv_layers[count])
        else:
            while len(obj.data.uv_layers) > 1:
                obj.data.uv_layers.remove(obj.data.uv_layers[1]) 

    # ----------
    # Assign single material to all exported objects
    # ----------
    new_mat_name = "M_Mask"
    
    new_mat = bpy.data.materials.get(new_mat_name)
    if new_mat is None:
        new_mat = bpy.data.materials.new(name=new_mat_name)
    
    for obj in objs_to_process: 
        if obj.type != 'MESH':
            continue
        obj.data = obj.data.copy() #in case of instancing
        obj.data.materials.clear()

        # Add the first material slot back
        obj.data.materials.append(new_mat)

if __name__ == "__lr_export_script__": 
    rename_obj(self, context)



