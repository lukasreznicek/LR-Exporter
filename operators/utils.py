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
        self.selected_objs_filtered = []
        
        for obj in self.selected_objs:
            self.selected_objs_names.append(obj.name)
            if obj.type == 'MESH':
                data_temp.append(obj.data)
            if obj.lr_object_export_settings.object_mode == 'EXPORTED':
                self.selected_objs_filtered.append(obj)
        
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
                obj.data = obj.data.copy() #Remove Instancing
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

    def add_uv_index(self):
        pass


    def uv_edit(self,
            
                uv_index, 
                unwrap = False, 
                unwrap_method = 'ANGLE_BASED', 
                unwrap_margin = 0.001,
                
                average_scale = False, 
                
                pack_islands = False,
                pack_margin = 0.001):
        
        '''
        Optionally unwraps, averages or packs UVs in specified index on stored objects.
        unwrap_method 'ANGLE_BASED', 'CONFORMAL'
        '''

        
        uv_index -= 1 #From 0

        check_missing_uv_id = False

        store_sel = bpy.context.selected_objects
        store_active = bpy.context.active_object
        bpy.context.view_layer.objects.active = self.selected_objs_filtered[0]
        store_mode = bpy.context.mode
        
        bpy.ops.object.select_all(action='DESELECT')
        
        for obj in self.selected_objs_filtered:
            if obj.type == 'MESH':
                obj.select_set(True)

        #Make single user and Apply modifiers
        bpy.ops.object.make_single_user(object=True, obdata=True, material=False, animation=False, obdata_animation=False)
        bpy.ops.object.convert(target='MESH')
        

        for obj in self.selected_objs_filtered:
            if obj.type != 'MESH':
                continue

            # store_uv_index = obj.data.uv_layers.active_index
            uv_layer_amount = ((len(obj.data.uv_layers))-1) #From 0

            if uv_index > uv_layer_amount:
                check_missing_uv_id = True
                obj.data.uv_layers[0].active = True #Copy from 0 if destination UV not present
                while len(obj.data.uv_layers)-1 < uv_index:
                    obj.data.uv_layers.new(name='UVMap', do_init = True)
        
            obj.data.uv_layers[uv_index].active = True


        if check_missing_uv_id:
            print(f'Some objects are missing UV #{uv_index}. Duplicating UV 0.')

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.select_all(action='SELECT')
        
        if unwrap == True:
            bpy.ops.uv.unwrap(method=unwrap_method, 
                            fill_holes=True, 
                            correct_aspect=True, 
                            use_subsurf_data=False, 
                            margin_method='SCALED', 
                            margin=0.001)

        if average_scale == True:
            bpy.ops.uv.average_islands_scale(scale_uv=False, 
                                            shear=False)

        if pack_islands == True:
            bpy.ops.uv.pack_islands(udim_source ='CLOSEST_UDIM', 
                                    rotate = True,
                                    rotate_method = 'ANY',
                                    scale = True,
                                    merge_overlap = False,
                                    margin_method = 'SCALED',
                                    margin = pack_margin,
                                    pin = False,
                                    pin_method = 'LOCKED',
                                    shape_method = 'CONCAVE')

        bpy.ops.object.mode_set(mode=store_mode)
        for obj in bpy.data.objects:
            obj.select_set(False)
        for obj in store_sel:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = store_active