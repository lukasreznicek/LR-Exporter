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



class SelectedObjectsInfo():
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
    
    def get_objects(self):
        return self.selected_objs
    
    def get_objects_names(self):
        return self.selected_objs_names

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
        
    def delete_all():
        pass

