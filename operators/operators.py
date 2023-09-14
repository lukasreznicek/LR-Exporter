import bpy, os, math
from . import utils
import time



class OBJECT_OT_lr_hierarchy_exporter(bpy.types.Operator):
    """ Exports selected object and its children into FBX file. Ideally select only parent object """
    
    bl_idname = "object.lr_exporter_export"
    bl_label = "Exports obj"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context): 

        
        if bpy.data.is_saved == False: #Saved file check
            message = f'Save .Blend file first. Cancelled'
            self.report({'WARNING'}, message)
            return {'FINISHED'}


        if len(bpy.context.selected_objects) == 0:   #Check for selected files
            message = 'Select object first'
            self.report({'WARNING'}, message)
            return {'FINISHED'}

        # --- PRE-PROCESS ---
        time_start = time.time()        
        lr_export_settings = bpy.context.scene.lr_export

        if lr_export_settings.export_full_hierarchy == True: #Bool to select full hierarchy

            store_selection_full_hierarchy_mode = bpy.context.selected_objects
            store_active_selection_full_hierarchy_mode = bpy.context.view_layer.objects.active

            obj_parent_top_list = []
            for obj in bpy.context.selected_objects:
                obj_parent = obj.parent
                if obj_parent == None: # If the object has no parent add it to evaluation
                    obj_parent_top = obj

                else:    
                    while obj_parent is not None:   # If the object has a parrent find the upper-most and add to evaluation
                        obj_parent_top = obj_parent
                        obj_parent = obj_parent.parent


                obj_parent_top_list.append(obj_parent_top)

            if len(obj_parent_top_list) != 0:
                bpy.ops.object.select_all(action='DESELECT')
                for obj in obj_parent_top_list:
                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj





        #--- START ---        
    
        #--- Input ---
        objects_to_evaluate = bpy.context.selected_objects
        objects_to_evaluate_active = bpy.context.view_layer.objects.active
        

        if lr_export_settings.export_full_hierarchy == True:
            store_selection = store_selection_full_hierarchy_mode
            store_active_selection = store_active_selection_full_hierarchy_mode

        else:
            store_selection = objects_to_evaluate
            store_active_selection = objects_to_evaluate_active

        # blender_file_location = bpy.path.abspath('//')


        #Add missing HP 
        if lr_export_settings.add_missing_hp == True:
            lp_suffix = '_LP'
            hp_suffix = '_HP'
            
            if len(objects_to_evaluate) >= 2:
                hp_root = []
                lp_root = []

                lp_names = []
                hp_names = []

                for selected_obj in objects_to_evaluate: 
                    if selected_obj.name.endswith(lp_suffix):
                        lp_root.append(selected_obj)
                        for lp_obj in selected_obj.children_recursive:
                            if lp_obj.type == 'MESH':
                                if lp_obj.name.endswith(lp_suffix):
                                    lp_names.append(lp_obj.name.rsplit(lp_suffix, 1)[0])

                    if selected_obj.name.endswith(hp_suffix):
                        hp_root.append(selected_obj)
                        for hp_obj in selected_obj.children_recursive:
                            if hp_obj.type == 'MESH':
                                if hp_obj.name.endswith(hp_suffix):
                                    hp_names.append(hp_obj.name.rsplit(hp_suffix, 1)[0])                   
                
                lp_names_without_hp_obj_set = set(lp_names) - set(hp_names)
                lp_names_without_hp_obj = list(lp_names_without_hp_obj_set)

                created_hp_objs = []
                for obj_name in lp_names_without_hp_obj:
                    
                    lp_obj = bpy.data.objects.get(obj_name+lp_suffix)
                    # Create a new HP using the data from the LP object
                    hp_obj = lp_obj.copy()
                    hp_obj.name = obj_name+hp_suffix

                    hp_obj.data = lp_obj.data
                    bpy.context.collection.objects.link(hp_obj)

                    #Parent duplicated obj to HP Root
                    hp_obj.parent = hp_root[0]
                    #Put HP obj to the same location as LP object
                    hp_obj.matrix_world = lp_obj.matrix_world.copy()
                    created_hp_objs.append(hp_obj)
            
            else:
                message = f'At laest two objects need to be selected.'
                self.report({'INFO'}, message)


        for selected_obj in objects_to_evaluate:            
            bpy.ops.object.select_all(action='DESELECT')
            
            bpy.context.view_layer.objects.active = selected_obj
            selected_obj.select_set(True)    

            children = selected_obj.children_recursive
            # bpy.ops.object.duplicates_make_real(use_hierarchy=True) WILL BE NEEDED FOR GEOMETRY NODES

            for child in children:
                child.select_set(True)

            obj_info_before = utils.SelectedObjectsInfo()


            #--- PREPARATION ---
            #After duplication Blender automatically selects nevely created objects
            bpy.ops.object.duplicate(linked=True)
            
            obj_info_after = utils.SelectedObjectsInfo()
       
            
            #Naming objects
            
            #Add suffix to old objs
            obj_info_before.add_suffix('_NameBackup')
            obj_info_before.add_data_suffix('_DataNameBackup')
            
            
            obj_info_after.restore_object_names(obj_info_before.selected_objs_names)
            obj_info_after.restore_object_data_names(obj_info_before.selected_objs_data_names)




            #Remove any parents in case of exporting a child object
            obj_info_after.active_obj.parent = None

            #Reset position
            if obj_info_after.active_obj.get("lr_export_reset_position") == 0:
                pass
            else:
                obj_info_after.active_obj.location = 0,0,0
            
            #Reset rotation
            if obj_info_after.active_obj.get("lr_export_reset_rotation") == 0:
                pass
            else:
                obj_info_after.active_obj.rotation_euler = 0,0,0



            #--- NAMING FBX ---

            blend_path = bpy.path.abspath('//')
            ui_export_path = bpy.data.scenes['Scene'].lr_export.export_path
            file_name = obj_info_after.active_obj.name
            
            prefix = bpy.data.scenes['Scene'].lr_export.export_sm_prefix
            suffix = bpy.data.scenes['Scene'].lr_export.export_sm_suffix
            filename_prefix_suffix = prefix+file_name+suffix
            file_format = '.fbx'
            
            if selected_obj.get("lr_exportsubfolder"):
                object_subbolder = obj_info_after.active_obj['lr_exportsubfolder']
            else:
                object_subbolder = ''


            export_path = os.path.join(bpy.path.abspath(ui_export_path), object_subbolder)
            export_file = os.path.join(export_path,filename_prefix_suffix+file_format)
            if os.path.exists(export_path) == False:
                os.makedirs(export_path)

            bpy.ops.export_scene.fbx(filepath = str(export_file), use_selection=True)
           
            # bpy.ops.export_scene.fbx(
                # filepath=GetExportFullpath(dirpath, filename),
                # check_existing=False,
                # use_selection=True,
                # global_scale=GetObjExportScale(active),
                # object_types={'EMPTY', 'CAMERA', 'LIGHT', 'MESH', 'OTHER'},
                # use_custom_props=addon_prefs.exportWithCustomProps,
                # mesh_smooth_type="FACE",
                # add_leaf_bones=False,
                # use_armature_deform_only=active.exportDeformOnly,
                # bake_anim=False,
                # use_metadata=addon_prefs.exportWithMetaData,
                # primary_bone_axis=active.exportPrimaryBaneAxis,
                # secondary_bone_axis=active.exporSecondaryBoneAxis,
                # axis_forward=active.exportAxisForward,
                # axis_up=active.exportAxisUp,
                # bake_space_transform=False
                # )
           
           #--- NAMING END ---


            #--- CLEANUP ---
    
            #Delete selected objects
            #bpy.ops.object.delete(use_global=False)
            for obj in bpy.context.selected_objects:
                bpy.data.objects.remove(obj, do_unlink=True)


            # Restore obj names
            obj_info_before.restore_object_names()
            obj_info_before.restore_object_data_names()
            

            #--- CLEANUP END ---
        
        
        # Additionally remove Created HPs
        if lr_export_settings.add_missing_hp == True:
            if len(objects_to_evaluate) >= 2:
                
                for obj in created_hp_objs:
                    bpy.data.objects.remove(bpy.data.objects.get(obj.name),do_unlink=True)


        #Return initial selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in store_selection:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = store_active_selection


        time_end = time.time()
        time_elapsed = time_end-time_start
        message = f'Exported: {filename_prefix_suffix}. In: {time_elapsed:.3f}s'
        self.report({'INFO'}, message)

        
        return {'FINISHED'}





class OBJECT_OT_store_object_data_json(bpy.types.Operator):
    bl_idname = "object.lr_store_object_data_json"
    bl_label = "Creates a list of object names,location,rotation and scale."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context): 
        '''File is saved next to a .blend file'''

        
        #Store initial selection
        selected_objs_init = bpy.context.selected_objects
        active_obj_init = bpy.context.view_layer.objects.active
        
        blender_file_location = bpy.path.abspath('//')
        if blender_file_location == None:
            self.report({'ERROR'}, 'Please save blender file. Aborting.')
            return {'FINISHED'}

        # print('LOCATION: ',blender_file_location)
        import json  

        active_obj = bpy.context.selected_objects[0]
        active_obj_children = active_obj.children_recursive
        object_list = active_obj_children
        
        object_assembly = {}

        lr_assembly_ids = []
        id_s = 0


        obj_prefix = ''


        for index,object in enumerate(object_list):
            id_s +=1

            # #Add Unique id for linking object between Unreal and Blender
            # if object.get('lr_assembly_id') is None:
            #     while id_s in lr_assembly_ids:
            #         id_s +=1
            #     object['lr_assembly_id'] = id_s
            #     lr_assembly_ids.append(id_s)
            

            if str(object.name.rsplit('.')[0]).startswith('SM_'):
                obj_name = object.name.rsplit('.')[0]
            else:
                obj_name = 'SM_'+object.name.rsplit('.')[0]


            object_assembly[index] = {'name': obj_name,
                                    'transform': (object.matrix_local.translation[0]*100,object.matrix_local.translation[1]*100,object.matrix_local.translation[2]*100),
                                    'rotation':(object.rotation_euler[0]*180/math.pi,object.rotation_euler[1]*180/math.pi,object.rotation_euler[2]*180/math.pi), 
                                    'scale':(object.scale[0],object.scale[1],object.scale[2]), 
                                    'id':'lr_assembly'
                                    } 


        json_object = json.dumps(object_assembly, indent= 2)

        blender_filename = bpy.path.basename(bpy.context.blend_data.filepath).rsplit('.')[0]
        filename_base = bpy.data.scenes['Scene'].lr_export.lr_assembly_filename
        temp_filename = filename_base
        extension = '.json'
        count = 0


        if bpy.data.scenes['Scene'].lr_export.lr_assembly_replace_file == False:
            while os.path.isfile(blender_file_location+temp_filename+extension):
                count += 1 
                temp_filename = filename_base+str("{:02d}".format(count))
            with open(blender_file_location+temp_filename+extension, "w") as outfile:
                outfile.write(json_object)

        else:
            with open(blender_file_location+filename_base+extension, "w") as outfile:
                outfile.write(json_object)


        return {'FINISHED'}





class OBJECT_OT_lr_pack_uvs(bpy.types.Operator):
    bl_idname = "object.lr_pack_uvs"
    bl_label = "Pack"
    bl_options = {'REGISTER', 'UNDO'}




    uv_channel_from: bpy.props.IntProperty(
        name="From UV Index",
        description="If missing create new UV Map from this index",
        default=0,
        min=0,
        soft_max=3,
    )

    uv_channel_to: bpy.props.IntProperty(
        name="To UV Index",
        description="An example integer property",
        default=1,
        min=0,
        soft_max=3,
    )
    uv_name: bpy.props.StringProperty(
        name="UV Name",
        description="An example integer property",
        default='UV_All',
    )

    def execute(self, context): 
        '''File is saved next to a .blend file'''
        
        selected_objects = bpy.context.selected_objects
        selected_objects_MESH = [i for i in selected_objects if i.type=='MESH']
        


        store_active_uv_map = []
        for index,obj in enumerate(selected_objects_MESH):

            #Store active uv map
            store_active_uv_map.append(obj.data.uv_layers.active_index)


            # List all UV maps
            uv_maps = obj.data.uv_layers.keys()
            uv_maps_amnt = len(uv_maps)-1 #Starting from 0

            #If uv with this name present rename it
            existing = obj.data.uv_layers.get(self.uv_name)
            if existing:
                existing.name = self.uv_name + '_01'


            # Make the UV active
            obj.data.uv_layers[self.uv_channel_from].active = True

            while self.uv_channel_to > uv_maps_amnt:
                obj.data.uv_layers[self.uv_channel_from].active = True
                obj.data.uv_layers.new(name='UVMap',do_init=True) #do init on true copies the UV from active
                uv_maps_amnt += 1


            obj.data.uv_layers[self.uv_channel_to].name = self.uv_name



        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected_objects_MESH:
            obj.select_set(True)

        # Step 1: Store mode
        current_mode = bpy.context.object.mode

        # Step 2: Go to edit mode
        bpy.ops.object.mode_set(mode='EDIT')

        # Step 3: Get select mode
        select_mode = bpy.context.tool_settings.mesh_select_mode[:]

        # # Step 4: Store select mode vertices/edges or polygons depending on active mode
        # selected_verts = []
        # selected_edges = []
        # selected_faces = []

        # if select_mode[0]:
        #     selected_verts = [v.index for v in obj.data.vertices if v.select]
        # if select_mode[1]:
        #     selected_edges = [e.index for e in obj.data.edges if e.select]
        # if select_mode[2]:
        #     selected_faces = [f.index for f in obj.data.polygons if f.select]

        # Step 5: Store UV sync mode
        uv_sync_mode = bpy.context.tool_settings.use_uv_select_sync

        # Step 6: Turn on UV sync mode
        bpy.context.tool_settings.use_uv_select_sync = True

        # Step 7: Select all polygons
        bpy.ops.mesh.select_all(action='SELECT')

        # Step 8: Pack UV map
        bpy.ops.uv.pack_islands(margin=0.05)

        # Step 9: Restore UV sync mode
        bpy.context.tool_settings.use_uv_select_sync = uv_sync_mode

        # # Step 10: Restore selection based on select mode
        # bpy.ops.object.mode_set(mode='EDIT')
        # bpy.ops.mesh.select_all(action='DESELECT')
        # bpy.ops.object.mode_set(mode='OBJECT')

        # if select_mode[0]:
        #     print(f"Selected verts: {selected_verts}")
        #     for v_index in selected_verts:
        #         obj.data.vertices[v_index].select = True
        # if select_mode[1]:
        #     print(f"Selected edges: {selected_edges}")
        #     for e_index in selected_edges:
        #         obj.data.edges[e_index].select = True
        # if select_mode[2]:
        #     print(f"Selected faces: {selected_faces}")
        #     for f_index in selected_faces:
        #         obj.data.polygons[f_index].select = True

        # Step 11: Restore mode
        bpy.ops.object.mode_set(mode=current_mode)

        #Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected_objects:
            obj.select_set(True)


        return {'FINISHED'}







class OBJECT_OT_lr_pack_uvs1(bpy.types.Operator):
    bl_idname = "object.lr_pack_uvs1"
    bl_label = "Pack1"
    bl_options = {'REGISTER', 'UNDO'}


    uv_channel: bpy.props.IntProperty(
        name="uv_channel",
        description="An example integer property",
        default=1,
        min=0,
        soft_max=3,
    )

    def execute(self, context): 
        '''File is saved next to a .blend file'''
        for obj in bpy.context.selected_objects:
            uv_channel_index = self.uv_channel

            # List all UV maps
            uv_maps = obj.data.uv_layers.keys()
            uv_maps_amnt = len(uv_maps)-1

            if uv_channel_index > uv_maps_amnt:
                uv_channel_index = uv_maps_amnt
                self.uv_channel = len(uv_maps)
                message = f'Executing on last UVMap'
                self.report({'INFO'}, message)

            # Select the second UV map
            second_uv_map_name = uv_maps[uv_channel_index]  # Index 1 corresponds to the second UV map
            obj.data.uv_layers.active = obj.data.uv_layers[second_uv_map_name]


            # Step 1: Store mode
            current_mode = bpy.context.object.mode

            # Step 2: Go to edit mode
            bpy.ops.object.mode_set(mode='EDIT')

            # Step 3: Get select mode
            select_mode = bpy.context.tool_settings.mesh_select_mode[:]

            # Step 4: Store select mode vertices/edges or polygons depending on active mode
            selected_verts = []
            selected_edges = []
            selected_faces = []

            if select_mode[0]:
                selected_verts = [v.index for v in obj.data.vertices if v.select]
            if select_mode[1]:
                selected_edges = [e.index for e in obj.data.edges if e.select]
            if select_mode[2]:
                selected_faces = [f.index for f in obj.data.polygons if f.select]

            # Step 5: Store UV sync mode
            uv_sync_mode = bpy.context.tool_settings.use_uv_select_sync

            # Step 6: Turn on UV sync mode
            bpy.context.tool_settings.use_uv_select_sync = True

            # Step 7: Select all polygons
            bpy.ops.mesh.select_all(action='SELECT')

            # Step 8: Pack UV map
            bpy.ops.uv.pack_islands(margin=0.05)

            # Step 9: Restore UV sync mode
            bpy.context.tool_settings.use_uv_select_sync = uv_sync_mode

            # Step 10: Restore selection based on select mode
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')

            if select_mode[0]:
                print(f"Selected verts: {selected_verts}")
                for v_index in selected_verts:
                    obj.data.vertices[v_index].select = True
            if select_mode[1]:
                print(f"Selected edges: {selected_edges}")
                for e_index in selected_edges:
                    obj.data.edges[e_index].select = True
            if select_mode[2]:
                print(f"Selected faces: {selected_faces}")
                for f_index in selected_faces:
                    obj.data.polygons[f_index].select = True

            # Step 11: Restore mode
            bpy.ops.object.mode_set(mode=current_mode)

        return {'FINISHED'}














# # Define a custom operator class
# class SimpleOperator(bpy.types.Operator):
#     bl_idname = "object.simple_operator"  # Unique identifier for the operator
#     bl_label = "Simple Operator"  # Display name for the operator
#     bl_options = {'REGISTER', 'UNDO'}  # Operator options
    
#     # Define operator properties
#     my_bool_property: bpy.props.BoolProperty(
#         name="Example Boolean",
#         description="An example boolean property",
#         default=True,
#     )
    
#     my_int_property: bpy.props.IntProperty(
#         name="Example Integer",
#         description="An example integer property",
#         default=10,
#         min=0,
#     )

#     def execute(self, context):
#         # Access the operator properties
#         bool_value = self.my_bool_property
#         int_value = self.my_int_property

#         # Do something with the settings
#         if bool_value:
#             self.report({'INFO'}, f"Boolean property is True. Integer property value: {int_value}")
#         else:
#             self.report({'INFO'}, f"Boolean property is False. Integer property value: {int_value}")
        
#         # Add your operator logic here

#         return {'FINISHED'}

# # Register the operator
# def register():
#     bpy.utils.register_class(SimpleOperator)

# def unregister():
#     bpy.utils.unregister_class(SimpleOperator)

# if __name__ == "__main__":
#     register()


































