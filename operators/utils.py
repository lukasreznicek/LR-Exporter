import bpy, math



def get_outliner_selection():
    '''If multiple outliners then outputs the first created one'''
    for area in bpy.context.screen.areas:
        if area.type == 'OUTLINER':
            outliner_area = area 

    with bpy.context.temp_override(area = outliner_area):
        return bpy.context.selected_ids

#remove duplicates
def f7(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


class SelectionCapture():
    def __init__(self):
        self.active_obj = None
        self.selected_objs = []
        self.selected_objs_data = []
        self.selected_objs_names = []
        self.selected_objs_data_names = []

        data_temp = []
        self.active_obj = bpy.context.object
        self.selected_objs = bpy.context.selected_objects
        for obj in self.selected_objs:
            self.selected_objs_names.append(obj.name)
            if obj.type == 'MESH':
                data_temp.append(obj.data)
        
        #Remove duplicate data
        self.selected_objs_data = f7(data_temp) 
        for data in self.selected_objs_data:
            self.selected_objs_data_names.append(data.name)


    def __repr__(self) -> str:
        return str(self.selected_objs_names)   

    def make_selection(self):
        '''Will select only objects in this class instance. Preserves active obj. Will deselect everything before.'''
        bpy.ops.object.select_all(action='DESELECT')
        for obj in self.selected_objs:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = self.active_obj

    def deselect_ignored_objects(self):
        for obj in self.selected_objs:
            if obj.lr_object_export_settings.object_mode == 'NOT_EXPORTED':
                obj.select_set(False)

    def select_ignored_objects(self):
        for obj in self.selected_objs:
            if obj.lr_object_export_settings.object_mode == 'NOT_EXPORTED':
                obj.select_set(True)

    def get_objects(self):
        return self.selected_objs
    
    def get_objects_names(self):
        return self.selected_objs_names

    def apply_modifiers(self):
        store_active_obj = bpy.context.view_layer.objects.active
        
        for obj in self.selected_objs:
            if obj.type == 'MESH':
                bpy.context.view_layer.objects.active = obj

                for modifier in obj.modifiers:
                    bpy.ops.object.modifier_apply(modifier=modifier.name, report=False, merge_customdata=True, single_user=True)

        bpy.context.view_layer.objects.active = store_active_obj

    def restore_object_names(self, name_list = None):
        if name_list == None:
            name_list = self.selected_objs_names
        for obj,name in zip(self.selected_objs, name_list):
            obj.name = name

    def restore_object_data_names(self, name_list= None):
        if name_list == None:
            name_list = self.selected_objs_data_names
        for data,name in zip(self.selected_objs_data, name_list):
            data.name = name

    def add_suffix(self, suffix):
        for obj in self.selected_objs:
            current_name = obj.name
            obj.name = current_name+suffix

    def add_data_suffix(self, suffix):
        for data in self.selected_objs_data:
            current_name = data.name
            data.name = current_name+suffix

    def add_missing_low_poly(self, lp_naming = None):
        if lp_naming == None:
            lp_suffix = '_LP'
        else:
            lp_suffix = lp_naming

        new_duplicates =[]
        for obj in self.selected_objs:
            if obj.name.endswith(lp_suffix):
                name_no_suffix = obj.name.rsplit('_LP', 1)[0]

        return(new_duplicates)    
        
    def remove_objects(self):
        for obj in self.selected_objs:
            bpy.data.objects.remove(obj, do_unlink=True)

    def material_override(self):
        '''Removes all materials and assigns one provided in obj parameter'''

        for obj in self.selected_objs: 

            new_mat_name=obj.lr_object_export_settings.get('lr_mat_override_mask')
            
            if new_mat_name == '' or new_mat_name == None:
                continue
            else:
                new_mat = bpy.data.materials.get(new_mat_name)
                if new_mat is None:
                    new_mat = bpy.data.materials.new(name=new_mat_name)
                
                obj.data = obj.data.copy() #making the object unique so i wont affect the existing one
                obj.data.materials.clear()

                # Add the first material slot back
                obj.data.materials.append(new_mat)

            #If object is in collection containing '_ID' assign material.
            #     if 'occluder' in collection_name_lower:
            #         if mat_occluder_name not in all_mats:
            #             mat_occluder = bpy.data.materials.new(name=mat_occluder_name)
            #         if link == 'OBJECT':
            #             obj.material_slots[0].material = bpy.data.materials[str(mat_occluder_name)]
            #         if link == 'DATA':
            #             obj.data.materials[0] = bpy.data.materials[mat_occluder_name]   


    def remove_all_but_one_uv(self):
        for obj in self.selected_objs:
            keep_uv_name=obj.lr_object_export_settings.get('lr_uv_isolate_mask')
            
            if keep_uv_name == '' or keep_uv_name == None:
                continue

            else:
                print(f'{keep_uv_name=}')
                obj.data = obj.data.copy()
                dat = obj.data
                count = 0
                if keep_uv_name in dat.uv_layers: 
                    while len(dat.uv_layers) > 1:
                        if dat.uv_layers[count].name == keep_uv_name:
                            count+=1
                            continue
                        else:
                            dat.uv_layers.remove(dat.uv_layers[count])
                else:
                    while len(dat.uv_layers) > 1:
                        dat.uv_layers.remove(dat.uv_layers[1]) 


