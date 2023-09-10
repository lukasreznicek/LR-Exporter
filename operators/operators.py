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


        if len(objects_to_evaluate) == 0:   #Check for selected files
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
        #Store initial selection
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



























