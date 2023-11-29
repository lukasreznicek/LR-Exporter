import bpy, os, math
from . import utils
import time


@staticmethod
def get_objects_in_local_view():
    '''
    Inputs:
    Example: bpy.context.screen.areas[0].spaces[0]
    
    Outputs:
    List of objects which are isolated, current active viewport space. used for getting and setting local viewmode on objects.
    or
    None if viewport is not in local view mode.
    '''
    
    for space in bpy.context.area.spaces: #Based on CONTEXT
        if space.type == 'VIEW_3D':
            viewport_space = space
        else: # If context is not correct Grab first 3d window.
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            viewport_space = space

    if bool(viewport_space.local_view) == True:

        depsgraph = bpy.context.evaluated_depsgraph_get()
        objects_in_local_view =[]
        for obj in bpy.data.objects:
            obj_evaluated = obj.evaluated_get(depsgraph)
            # obj.local_view_set(viewport_space, True)
            if obj_evaluated.local_view_get(viewport_space):
                objects_in_local_view.append(obj)
                

        return objects_in_local_view,viewport_space
    else: 
        return None,None

@staticmethod
def change_local_view_on_objects(objects:list,viewport,add_to_local_view=True):
    '''
    Works only when local view is enabled.

    Viewport example: bpy.context.screen.areas[0].spaces[0]
    add_to_local_view:  True= Adds objects
                        False = Removes them from local view.
    '''
    if bool(viewport.local_view) == True:
        for obj in objects:
            obj.local_view_set(viewport, add_to_local_view)

class OBJECT_OT_lr_hierarchy_exporter(bpy.types.Operator):
    """ Exports selected object and its children into FBX file. Ideally select only parent object """
    
    bl_idname = "object.lr_exporter_export"
    bl_label = "Exports obj"
    bl_options = {'REGISTER', 'UNDO'}
    
    export_hidden:bpy.props.BoolProperty(name="Export Hidden", description="Exports all objects in hierarchy including hidden objects.", default=True, options={'HIDDEN'})


    def execute(self, context): 
        
        if bpy.data.is_saved == False: #Saved file check
            message = f'Save .Blend file first. Cancelled'
            self.report({'WARNING'}, message)
            return {'FINISHED'}


        if len(bpy.context.selected_objects) == 0:   #Check for selected files
            message = 'No object selected'
            self.report({'WARNING'}, message)
            return {'FINISHED'}


        # ------ PRE-PROCESS ------
              
        lr_export_settings_scene = bpy.context.scene.lr_export_settings_scene

        store_selection = bpy.context.selected_objects
        store_active_selection = bpy.context.view_layer.objects.active
        
        objects_to_evaluate = bpy.context.selected_objects #Initial selection


        if lr_export_settings_scene.export_full_hierarchy == True: #Bool to select full hierarchy, This will modify list. Replaces current selection for the uppermost in hierarchy.

            obj_parent_top_list = []
            for obj in objects_to_evaluate:
                obj_parent = obj.parent
                if obj_parent != None: 
                    while obj_parent is not None:   # If the object has a parrent find the upper-most and add to evaluation
                        obj_parent_top = obj_parent
                        obj_parent = obj_parent.parent
                
                    obj_parent_top_list.append(obj_parent_top)
                else:
                    obj_parent_top_list.append(obj)

                

            objects_to_evaluate = obj_parent_top_list
 


        #Each object in list to evaluate. 




        #--- START ---        
    
        #--- Input ---
        
        # objects_to_evaluate_active = bpy.context.view_layer.objects.active
        

        # blender_file_location = bpy.path.abspath('//')



        # ------------ ADD EXPORTED OBJECTS TO LOCAL VIEW IF LOCAL VIEW IS ENABLED ------------
        objects_in_local_view, active_viewport =get_objects_in_local_view()



        # ------------ ADD MISSING HP ------------
        if lr_export_settings_scene.add_missing_hp == True:
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


                position_offset = (hp_root[0].location[0]-lp_root[0].location[0], hp_root[0].location[1]-lp_root[0].location[1], hp_root[0].location[2]-lp_root[0].location[2])

                
                created_hp_objs = []
                for obj_name in lp_names_without_hp_obj:
                    
                    lp_obj = bpy.data.objects.get(obj_name+lp_suffix)

                    # for modifier in lp_obj.modifiers:
                    #     # Apply the modifier
                    #     bpy.ops.object.modifier_apply({"object": lp_obj},modifier=modifier.name)

                    #obj.data = obj.data.copy() #Make object unique. Remove instancing.

                    act_obj = bpy.context.active_object
                    bpy.context.view_layer.objects.active = lp_obj
                    for modifier in lp_obj.modifiers: # Apply all modifier
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
                    bpy.context.view_layer.objects.active = act_obj



                    # Create a new HP using the data from the LP object
                    hp_obj = lp_obj.copy()
                    hp_obj.name = obj_name+hp_suffix

                    hp_obj.data = lp_obj.data
                    #hp_obj.data.shade_smooth()
                    #hp_obj.data.edges.foreach_set('use_edge_sharp',[False]*len(hp_obj.data.edges)) #Remove all sharp edges
                    bpy.context.collection.objects.link(hp_obj)


                    #Parent duplicated obj to HP Root
                    hp_obj.parent = hp_root[0]
                    #Put HP obj to the same location as LP object
                    hp_obj.matrix_world = lp_obj.matrix_world.copy()
                    
                    hp_obj.matrix_world.translation[0] += position_offset[0]
                    hp_obj.matrix_world.translation[1] += position_offset[1]
                    hp_obj.matrix_world.translation[2] += position_offset[2]

                    created_hp_objs.append(hp_obj)
            
            else:
                message = f'At laest two objects need to be selected.'
                self.report({'INFO'}, message)


        for obj_evaluated in objects_to_evaluate:         
            time_start = time.time()

            if obj_evaluated.lr_object_export_settings.object_mode == 'NOT_EXPORTED':
                continue


            bpy.ops.object.select_all(action='DESELECT')
              
            # bpy.ops.object.duplicates_make_real(use_hierarchy=True) WILL BE NEEDED FOR GEOMETRY NODES
            parent_and_children = []
            parent_and_children.append(obj_evaluated)
            parent_and_children.extend(obj_evaluated.children_recursive)
            
            
            object_hidden = []
            object_hidden_in_viewport = []

            for obj in parent_and_children:    
                if self.export_hidden == True: #Unhide objects before export if wanted.

                    if obj.hide_viewport == True:
                        object_hidden_in_viewport.append(obj)
                        obj.hide_viewport = False
                    
                    if obj.hide_get(view_layer=bpy.context.view_layer) == True:
                        object_hidden.append(obj)
                        obj.hide_set(False)

                obj.select_set(True) #Only one obj selection matters which is here and line below. This needs to be after unhide. In Blender hidden selected object count as unselected.
            
            bpy.context.view_layer.objects.active = obj_evaluated #Active object is important for transform and naming.


            if objects_in_local_view != None:
                change_local_view_on_objects(parent_and_children,active_viewport,add_to_local_view=True)


            obj_info_before = utils.SelectionCapture()

            #--- PREPARATION ---
            #After duplication Blender automatically selects nevely created objects
            bpy.ops.object.duplicate(linked=True)
            
            obj_info_after = utils.SelectionCapture()
       

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

            obj_info_after.deselect_ignored_objects() #Deselect object which are marked as Ignored.        




            #--- NAMING FBX ---
            blend_path = bpy.path.abspath('//')
            ui_export_path = bpy.data.scenes['Scene'].lr_export_settings_scene.export_path
            file_name = obj_info_after.active_obj.name
            
            prefix = lr_export_settings_scene.export_sm_prefix
            suffix = lr_export_settings_scene.export_sm_suffix
            filename_prefix_suffix = prefix+file_name+suffix
            file_format = '.fbx'


            object_subbolder = obj_info_after.active_obj.lr_object_export_settings.get('lr_exportsubfolder')
            if object_subbolder == None:
                object_subbolder = '' 

                
            export_path = os.path.join(bpy.path.abspath(ui_export_path), object_subbolder)
            export_file = os.path.join(export_path,filename_prefix_suffix+file_format)
            if os.path.exists(export_path) == False:
                os.makedirs(export_path)


            bpy.ops.export_scene.fbx(filepath = str(export_file), 
                                     use_selection=True,
                                     prioritize_active_color=True,
                                     colors_type='SRGB',
                                     use_visible=False) 

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

            obj_info_after.remove_objects()

            # Restore obj names
            obj_info_before.restore_object_names()
            obj_info_before.restore_object_data_names()
                
            #Return visibility settings
            if self.export_hidden == True: #Unhide objects before export if wanted.
                for obj in object_hidden_in_viewport:
                    obj.hide_viewport = True

                for obj in object_hidden:
                    obj.hide_set(True)


            #Return local view object state
            obj_to_remove_from_local_view = []
            if objects_in_local_view != None:
                for obj in parent_and_children:
                    if obj not in objects_in_local_view:
                        obj_to_remove_from_local_view.append(obj)

                change_local_view_on_objects(obj_to_remove_from_local_view,active_viewport,add_to_local_view=False)

            if filename_prefix_suffix == None:
                message = f'Nothing Exported'
                self.report({'INFO'}, message)
            else:
                time_end = time.time()
                time_elapsed = time_end-time_start
                message = f'Exported: {filename_prefix_suffix}. In: {time_elapsed:.3f}s'
                self.report({'INFO'}, message)
            #--- CLEANUP END ---
        
        
        # Additionally remove Created HPs
        if lr_export_settings_scene.add_missing_hp == True:
            if len(objects_to_evaluate) >= 2:
                
                for obj in created_hp_objs:
                    bpy.data.objects.remove(bpy.data.objects.get(obj.name),do_unlink=True)


        #Return initial selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in store_selection:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = store_active_selection




            



        
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
        filename_base = lr_export_settings_scene.lr_assembly_filename
        temp_filename = filename_base
        extension = '.json'
        count = 0


        if lr_export_settings_scene.lr_assembly_replace_file == False:
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
    """ Creates packed UVMap. !Will replace existing UVs"""
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

    unwrap_uv: bpy.props.BoolProperty(
        name="Unwrap UVs",
        description="Unwrap UVs",
        default=True,
    )

    average_uv_scale: bpy.props.BoolProperty(
        name="Average scale",
        description="Averages uv scale before packing",
        default=True,
    )

    uv_channel_pack_margin: bpy.props.FloatProperty(
        name="Pack Margin",
        description="An example integer property",
        default=0.05,
        min=0,
        soft_max=2,
    )

    def execute(self, context): 
        '''File is saved next to a .blend file'''
        

        mode_store = bpy.context.mode
        if mode_store != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        selected_objects = bpy.context.selected_objects
        selected_objects_MESH = [i for i in selected_objects if i.type=='MESH']
        store_active_uv_map = []
        for index,obj in enumerate(selected_objects_MESH):

            #Store active uv map
            store_active_uv_map.append(obj.data.uv_layers.active_index)


            # List all UV maps
            uv_maps = obj.data.uv_layers.keys()
            uv_maps_amnt = len(uv_maps)-1 #Starting from 0

            if uv_maps_amnt == -1:
                message = f'At least on UV set needs to be present'
                self.report({'INFO'}, message)
                return {'FINISHED'}

            #If uv with this name present rename it
            existing = obj.data.uv_layers.get(self.uv_name)
            if existing:
                existing.name = self.uv_name + '_01'


            
            obj.data.uv_layers[self.uv_channel_from].active = True # Make active UV to copy from

            while self.uv_channel_to > uv_maps_amnt:
                obj.data.uv_layers[self.uv_channel_from].active = True
                obj.data.uv_layers.new(name='UVMap',do_init=True) #do init on true copies the UV from active
                uv_maps_amnt += 1


            obj.data.uv_layers[self.uv_channel_to].name = self.uv_name
            obj.data.uv_layers[self.uv_channel_to].active = True 



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
        if self.average_uv_scale == True:
            bpy.ops.uv.average_islands_scale()


        if self.unwrap_uv == True:
            bpy.ops.uv.unwrap(method='ANGLE_BASED',fill_holes=True)

        bpy.ops.uv.pack_islands(margin=self.uv_channel_pack_margin,margin_method='SCALED')
 
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

        
        if mode_store == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')
        elif mode_store == 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}





































