import bpy, os, math
from . import utils
import time
from pathlib import Path
import subprocess

@staticmethod
def get_active_3d_viewport():
    """Return a VIEW_3D space, trying context first, then fallback to first 3D viewport."""
    area = bpy.context.area
    if area and area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                return space

    # fallback: first 3D viewport
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    return space
    return None


def get_local_views():
    local_views = []
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    if space.local_view:
                        local_views.append(space)
    return local_views


@staticmethod
def objects_not_in_local_view(obj_list):
    """
    Filter a list of objects and return those not in local view
    of the active 3D viewport.

    Args:
        obj_list (list of bpy.types.Object): objects to check

    Returns:
        list of bpy.types.Object: objects not in local view
        None if local view is not active
    """
    viewport_space = get_active_3d_viewport()
    if not viewport_space or not viewport_space.local_view:
        return None

    depsgraph = bpy.context.evaluated_depsgraph_get()

    return [obj for obj in obj_list if not obj.evaluated_get(depsgraph).local_view_get(viewport_space)
    ]

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
            export_node = obj.evaluated_get(depsgraph)
            # obj.local_view_set(viewport_space, True)
            if export_node.local_view_get(viewport_space):
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


# class OT_OpenScriptsFolder(bpy.types.Operator):
#     bl_idname = "wm.lr_exporter_open_scripts_folder"
#     bl_label = "Open Scripts Folder in exporter addon"
#     bl_description = "Opens the lr exporter Scripts folder in Windows Explorer"

#     def execute(self, context):
#         # Compute the folder path
#         folder = Path(__file__).resolve().parents[1] / "Scripts"

#         # Ensure it exists
#         if not folder.exists():
#             self.report({'ERROR'}, f"Folder does not exist: {folder}")
#             return {'CANCELLED'}

#         # Open in Windows Explorer
#         try:
#             subprocess.Popen(f'explorer "{folder}"')
#         except Exception as e:
#             self.report({'ERROR'}, f"Failed to open folder: {e}")
#             return {'CANCELLED'}

#         return {'FINISHED'}
    
class OT_OpenScriptsFolder(bpy.types.Operator):
    bl_idname = "wm.lr_exporter_open_scripts_folder"
    bl_label = "Open Scripts Folder"
    bl_description = "Opens a folder inside the LR Exporter addon root"

    subfolder: bpy.props.StringProperty(
        name="Subfolder",
        description="Name of the subfolder inside the addon root",
        default="Scripts"
    )

    def execute(self, context):
        addon_root = Path(__file__).resolve().parents[1]
        folder = addon_root / self.subfolder

        if not folder.exists():
            self.report({'ERROR'}, f"Folder does not exist: {folder}")
            return {'CANCELLED'}

        try:
            subprocess.Popen(f'explorer "{folder}"')
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open folder: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

def object_depth(obj):
    depth = 0
    while obj.parent:
        depth += 1
        obj = obj.parent
    return depth
# def add_property(objects, property_name, value):
#     for obj in objects:
#         if obj.type == 'MESH':
#             obj[property_name] = value

class OBJECT_OT_lr_hierarchy_exporter(bpy.types.Operator):
    """Exports selected object and its children (or parents) into FBX file.\nOne selected object = One .FBX. Multiple object selection will result in multiple .FBX"""
    
    bl_idname = "object.lr_exporter_export"
    bl_label = "Exports obj"
    bl_options = {'REGISTER', 'UNDO'}
    

    """They are the firtst node with PARENT tag. It can have a parent but exporter is intentionally limited to first occurance."""
    export_hidden:bpy.props.BoolProperty(name="Export Hidden", description="Exports all objects in hierarchy including hidden objects.", default=True, options={'HIDDEN'})
    export_for_mask:bpy.props.BoolProperty(name="Export For Mask", description="Exports object with material and UV override in mind", default=False, options={'HIDDEN'})
    
    def execute(self, context): 
        self.ADDON_ROOT = Path(__file__).resolve().parents[1]
        self.exported_objects = []
        self.preprocess_obj_duplicates = set()
        self.export_nodes = set()
        self.main_export_nodes: list = [] 


        if bpy.data.is_saved == False: #Saved file check
            message = f'Save .Blend file first. Cancelled'
            self.report({'WARNING'}, message)
            return {'FINISHED'}


        if len(bpy.context.selected_objects) == 0:   #Check for selected files
            message = 'No object selected'
            self.report({'WARNING'}, message)
            return {'FINISHED'}

        store_mode = bpy.context.object.mode
        
        if bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # ------ PRE-PROCESS ------
              
        lr_export_settings_scene = bpy.context.scene.lr_export_settings_scene

        store_selection = list(bpy.context.selected_objects)
        store_active_selection = bpy.context.view_layer.objects.active
        
        # objects_to_evaluate = bpy.context.selected_objects #Initial selection
        parent_empty = None

        # if lr_export_settings_scene.export_full_hierarchy == True: #Bool to select full hierarchy, This will modify list. Replaces current selection for the uppermost in hierarchy.

        #     obj_parent_top_list = []
        #     for obj in objects_to_evaluate:
        #         obj_parent = obj.parent
        #         if obj_parent != None: 
        #             while obj_parent is not None:   # If the object has a parent find the upper-most and add to evaluation
        #                 obj_parent_top = obj_parent
        #                 obj_parent = obj_parent.parent
        #             obj_parent_top_list.append(obj_parent_top)
        #         else:
        #             obj_parent_top_list.append(obj)

        #     objects_to_evaluate = obj_parent_top_list

        objects_to_evaluate = []
        all_src_objects_for_export = set()
        objects_in_hierarchy= set()
        root_preprocess_nodes = set()
        #Check selected
        for obj in bpy.context.selected_objects:

            # --- Find preprocess root (absolute root only) ---
            obj_parent = obj
            while obj_parent != None: #Crawl to the top and check if there is preprocess script
                if obj_parent.lr_object_export_settings.python_scripts_prepro != 'NONE' and not obj_parent.parent:
                    root_preprocess_nodes.add(obj_parent)
                obj_parent = obj_parent.parent
            

            # If parent is present crawl up until first export node is found (.object_mode == 'PARENT')
            obj_parent = obj.parent
            if obj_parent == None: #Has no parent
                objects_in_hierarchy.update(obj.children_recursive)
                objects_in_hierarchy.add(obj)
                continue


            # --- Find first export node ---
            obj_parent = obj #Start with object itself
            while obj_parent != None: #Has parent
                if obj_parent.lr_object_export_settings.object_mode == 'PARENT':

                    objects_in_hierarchy.update(obj_parent.children_recursive)
                    objects_in_hierarchy.add(obj_parent)
                    break #Lets check only first occurence of export node. Meaning it will not export multiple upper export nodes only first.
                obj_parent = obj_parent.parent

                
    
        # Collect export nodes
        for obj in objects_in_hierarchy:
            if obj.lr_object_export_settings.object_mode == "PARENT":
                self.export_nodes.add(obj)

        if not self.export_nodes:
            self.report({'WARNING'}, "No objects have 'Export Recursive' Mode on in hierarchy.")
            return {'CANCELLED'}


        #Unhide all 
        for obj in self.export_nodes:
            all_src_objects_for_export.update(obj.children_recursive)
            all_src_objects_for_export.add(obj) # Also add parent
        



        #Im using custom scripts inside exporter - cant influence code user does like making data unique and duplicating. 
        # Collecting all influenced data and then clean up on data is by comparing against this capture and removing extra.
        meshes_start_capture = set(bpy.data.meshes)

        src_obj_hidden = set()
        src_obj_viewport_hidden=set()
        all_src_objects_data_for_export = set()
        src_obj_local_view_info = {}
        #Visibility Stuff
        
        #Local View
        local_views = get_local_views() # bpy.data.screen.areas[3].spaces[0]
        if local_views:
            for view in local_views:
                src_obj_local_view_info.setdefault(view,[])


        for obj in all_src_objects_for_export:
            if not obj.users_collection:
                continue


            if obj.hide_get(view_layer=bpy.context.view_layer):
                obj.lr_object_export_settings["orig_hidden"] = True
                src_obj_hidden.add(obj)
            else:
                obj.lr_object_export_settings["orig_hidden"] = False

            if obj.hide_viewport:
                obj.lr_object_export_settings["orig_viewport_hidden"] = True
                src_obj_viewport_hidden.add(obj)
            else:
                obj.lr_object_export_settings["orig_viewport_hidden"] = False

            for view, obj_list in src_obj_local_view_info.items():
                if not obj.local_view_get(view): # True = in local view
                    obj_list.append(obj)
                    obj.local_view_set(view,True)


            obj.lr_object_export_settings["orig_name"] = obj.name # Used for precise matching after duplication
            
            
            
            # obj.lr_object_export_settings["orig_data_name"] = obj.data.name
            # Create metadata dict for this object

            if hasattr(obj,"data") and obj.data is not None:
                all_src_objects_data_for_export.add(obj.data)
                


        for data in all_src_objects_data_for_export:
            data["orig_data_name"] = data.name
            # data.name = data.name + "_LRExportBackupOD~"

        # Unhide all if needed
        if self.export_hidden:
            for obj in src_obj_hidden:
                obj.hide_set(False)
            for obj in src_obj_viewport_hidden:
                obj.hide_viewport = False

        # all_src_objects_for_export = list(all_src_objects_for_export)



        # All objects that are part of export are unhidden and checked (original objects before duplication). 

        original_objs_dict = {}

        #Store Initial Selection
        # store_active_obj = bpy.context.view_layer.objects.active
        # store_selection = bpy.context.selected_objects
        
        


       
        # Renaming
        for obj in all_src_objects_for_export:
            all_src_objects_data_for_export.add(obj.data)
        
        for obj in all_src_objects_for_export:
            obj.name = obj.name+"_LRExportBackup~"
            

        # -----
        # Preprocess
        # -----
        if len(root_preprocess_nodes) > 0:
            #Duplicate preprocess objs
            all_root_preproc_obj_duplicates = set() # Set to remove them during cleanup
            for root_preproc_node in root_preprocess_nodes:
                self.preprocess_obj_duplicates = set()
                root_preproc_node_objs = set()
                bpy.ops.object.select_all(action='DESELECT')
                bpy.context.view_layer.objects.active = root_preproc_node
                # root_preproc_node.select_set(True)

                for child in root_preproc_node.children_recursive:
                    root_preproc_node_objs.add(child)
                root_preproc_node_objs.add(root_preproc_node)

                root_preproc_node_objs_filtered = all_src_objects_for_export & root_preproc_node_objs #No need to change objects that are not exported  
                    
                for obj in root_preproc_node_objs_filtered:
                    obj.select_set(True)

                preprocess_export_dict={}
                for obj in root_preproc_node_objs_filtered:
                    preprocess_export_dict.update({obj.lr_object_export_settings["orig_name"] : obj})
                    if obj.lr_object_export_settings.object_mode == 'PARENT': 
                        self.export_nodes.remove(obj) # Remove original wont be exported - Replaced by duplicate


                bpy.ops.object.duplicate(linked=True) #Only happens when preprocess is used


                preprocess_export_dict_duplicate = {}
                for obj in bpy.context.selected_objects:
                    if obj not in preprocess_export_dict.values():  # means it's a duplicate
                        orig_name = obj.lr_object_export_settings["orig_name"]
                        preprocess_export_dict_duplicate[orig_name] = obj
                        if obj.lr_object_export_settings.object_mode == 'PARENT':
                            self.export_nodes.add(obj) # Use new duplicates to export


                for name,obj in preprocess_export_dict_duplicate.items():
                    obj.name = name


                self.preprocess_obj_duplicates = set(preprocess_export_dict_duplicate.values()) # For preprocess script
                
                all_root_preproc_obj_duplicates.update(preprocess_export_dict_duplicate.values())

                try:
                    script_file = self.ADDON_ROOT / "scripts_preprocess" / root_preproc_node.lr_object_export_settings.python_scripts_prepro
                    namespace = {
                        "__file__": str(script_file),
                        "__name__": "__lr_export_script_preprocess__",
                        "self": self,
                        "context": context,
                    }

                    with open(script_file, "r", encoding="utf-8") as f:
                        exec(f.read(), namespace)
                
                except Exception as e:
                    self.report({'ERROR'}, f"Error executing preprocess script {export_node_dupl.lr_object_export_settings.python_scripts}: {e}")


                #Name the objects
                for obj in self.preprocess_obj_duplicates:
                    obj.name = obj.name+"_LRDuplPreprocessObjs~"







            #Execute Script on preprocess objects - rename to original
        




        # ------------ ADD MISSING HP ------------
        if lr_export_settings_scene.add_missing_hp == True:
            lp_suffix = '_lp'
            hp_suffix = '_hp'
            
            if len(self.export_nodes) >= 2:
                hp_root = []
                lp_root = []

                lp_names = []
                hp_names = []

                for selected_obj in self.export_nodes:
                    if selected_obj.type != 'EMPTY':
                        continue
                    if selected_obj.name.lower().endswith(lp_suffix):
                        lp_root.append(selected_obj)
                        for lp_obj in selected_obj.children_recursive:
                            if lp_obj.type == 'MESH':
                                if lp_obj.name.lower().endswith(lp_suffix):
                                    lp_names.append(lp_obj.name.rsplit(lp_suffix, 1)[0])

                    if selected_obj.name.lower().endswith(hp_suffix):
                        hp_root.append(selected_obj)
                        for hp_obj in selected_obj.children_recursive:
                            if hp_obj.type == 'MESH':
                                if hp_obj.name.lower().endswith(hp_suffix):
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

                    # Might have to revert this:
                    # for modifier in lp_obj.modifiers: # Apply all modifier
                    #     bpy.ops.object.modifier_apply(modifier=modifier.name)

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

        # ---------
        #   Object to evaluate is a root object to be exported. This object + descendants will be exported as one fbx.
        # ---------

        
        for export_node in self.export_nodes:
            
            self.exported_objects.clear()

            time_start = time.time()


            bpy.ops.object.select_all(action='DESELECT')
              
            # bpy.ops.object.duplicates_make_real(use_hierarchy=True) WILL BE NEEDED FOR GEOMETRY NODES
            export_node_and_children = []
            export_node_and_children.append(export_node)
            export_node_and_children.extend(export_node.children_recursive)
            

            for obj in export_node_and_children:
                if not obj.users_collection:
                    continue
                obj.select_set(True) #Only one obj selection matters which is here and line below.
            
            bpy.context.view_layer.objects.active = export_node #Active object is important for transform and naming.
            # print("Active object before duplication: ", bpy.context.view_layer.objects.active)
            # print("Selected objects before duplication:", bpy.context.selected_objects)
            export_obj_dict={}
            for obj in export_node_and_children:
                export_obj_dict.update({obj.lr_object_export_settings["orig_name"] : obj})
            export_active_obj_dict = {export_node.lr_object_export_settings["orig_name"]: export_node}

            
            
            # ----------
            # Duplicate
            # ----------
            bpy.ops.object.duplicate(linked=True) 



            # export_node_and_children_dupl = [obj for obj in bpy.data.objects if obj.select_get() == True]
            export_node_and_children_dupl = bpy.context.selected_objects

            export_obj_dict_dupl={}
            for obj in export_node_and_children_dupl:
                #Restore Orig name before export:
                obj.name = obj.lr_object_export_settings["orig_name"]
                export_obj_dict_dupl.update({obj.lr_object_export_settings["orig_name"] : obj})
            
            
            #Resolve active object after duplication
            export_node_dupl = None
            if bpy.context.view_layer.objects.active.lr_object_export_settings["orig_name"] in export_obj_dict_dupl:
                export_node_dupl = bpy.context.view_layer.objects.active
            else:
                for obj in export_node_and_children_dupl:
                    if obj.lr_object_export_settings["orig_name"] in export_active_obj_dict:
                        export_node_dupl = obj
                        bpy.context.view_layer.objects.active=export_node_dupl
            
                


            # ----------
            # Naming after duplication
            # ----------

            self.exported_objects = list(export_node_and_children_dupl)
            # bpy.ops.object.select_all(action='DESELECT')





            #Remove any parents in case of exporting a child object
            export_node_dupl.parent = None

            raw_path = bpy.data.filepath
            if not raw_path:
                raw_path = ""
            for obj in self.exported_objects:
                obj.name = obj.lr_object_export_settings["orig_name"]

                obj["BlendSrc"] = raw_path.replace("\\","/")


            # Reset position
            if export_node_dupl.lr_object_export_settings.lr_export_reset_position:
                export_node_dupl.location = (0, 0, 0)

            # Reset rotation
            if export_node_dupl.lr_object_export_settings.lr_export_reset_rotation:
                export_node_dupl.rotation_euler = (0, 0, 0)

            # --------------------
            # Custom operations:
            # --------------------
           
            if export_node_dupl.lr_object_export_settings.python_scripts != 'NONE':
                try:
                    script_file = self.ADDON_ROOT / "scripts" / export_node_dupl.lr_object_export_settings.python_scripts
                    namespace = {
                        "__file__": str(script_file),
                        "__name__": "__lr_export_script__",
                        "self": self,
                        "context": context,
                    }

                    with open(script_file, "r", encoding="utf-8") as f:
                        exec(f.read(), namespace)
                
                except Exception as e:
                    self.report({'ERROR'}, f"Error executing script {export_node_dupl.lr_object_export_settings.python_scripts}: {e}")



            #--- NAMING FBX ---
            blend_path = bpy.path.abspath('//')
            ui_export_path = lr_export_settings_scene.export_path
            file_name = export_node_dupl.name
            
            prefix = lr_export_settings_scene.export_sm_prefix


            suffix = lr_export_settings_scene.export_sm_suffix
            if self.export_for_mask:
                suffix = suffix + lr_export_settings_scene.export_mask_sm_suffix
            
            filename_prefix_suffix = prefix+file_name+suffix


            file_format = '.fbx'

            object_subbolder = export_node_dupl.lr_object_export_settings.get('lr_exportsubfolder')
            if object_subbolder == None:
                object_subbolder = ''


            export_path = os.path.join(bpy.path.abspath(ui_export_path), object_subbolder)
            export_file = os.path.join(export_path,filename_prefix_suffix+file_format)
            if os.path.exists(export_path) == False:
                os.makedirs(export_path)

            # print("Selected right before export:", bpy.context.selected_objects)
            # for obj in bpy.data.objects:
            #     print(obj.name,": ", obj.select_get())

            #Debug
            print("--- DEBUG RIGHT BEFORE EXPORT ---: ")
            print(f"Number of exported objects: {len(bpy.context.selected_objects)}")
            for obj in bpy.context.selected_objects:
                if obj.type != "MESH":
                    continue
                
                print(f"Obj: {obj.name}")
                print(f"number of mat slots obj: {len(obj.material_slots)}, data: {len(obj.data.materials)}")

                for idx, mat_slot in enumerate(obj.material_slots):
                    print(f"Object Index: {idx} has material: {mat_slot.name}")


                for idx, mat_slot in enumerate(obj.data.materials):
                    print(f"Data Index: {idx} has material: {mat_slot.name}")


                print("---")
            print("--- DEBUG RIGHT BEFORE EXPORT END---: ")

            bpy.ops.export_scene.fbx(filepath = str(export_file),
                                     check_existing=False,
                                     use_selection=True,
                                     mesh_smooth_type="FACE",
                                     prioritize_active_color=True,
                                     colors_type='SRGB',
                                     use_visible=False,
                                     use_custom_props=True,
                                     use_metadata=True,
                                     add_leaf_bones=False) 


            if lr_export_settings_scene.send_payload:
                utils.send_payload_to_listener(
                    payload={
                        "asset_path": os.path.abspath(str(export_file)).replace('\\', '/'),
                        "asset_name": filename_prefix_suffix
                    },
                    operator=self
                )


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

            #
            for obj in list(bpy.context.selected_objects):
                bpy.data.objects.remove(obj, do_unlink=True)


            #Return local view object state
            # obj_to_remove_from_local_view = []
            # if objects_in_local_view != None:
            #     for obj in export_node_and_children:
            #         if obj not in objects_in_local_view:
            #             obj_to_remove_from_local_view.append(obj)

            #     change_local_view_on_objects(obj_to_remove_from_local_view,active_viewport,add_to_local_view=False)

            if filename_prefix_suffix == None:
                message = f'Nothing Exported'
                self.report({'INFO'}, message)
            else:
                time_end = time.time()
                time_elapsed = time_end-time_start
                message = f'Exported: {filename_prefix_suffix}. In: {time_elapsed:.3f}s'
                self.report({'INFO'}, message)
            #--- CLEANUP END ---
        
        if len(root_preprocess_nodes) > 0:
            for obj in all_root_preproc_obj_duplicates:
                bpy.data.objects.remove(obj,do_unlink=True)

        #Duplicated data cleanum
        meshes_done_capture = set(bpy.data.meshes)

        meshes_extra = meshes_done_capture - meshes_start_capture
    
        for mesh in meshes_extra:
            bpy.data.meshes.remove(mesh, do_unlink=True)


        #Return visibility settings
        for obj in src_obj_hidden:
            obj.hide_set(True)

        for obj in src_obj_viewport_hidden:
            obj.hide_viewport = True

        # Hide in local view
        for view, obj_list in src_obj_local_view_info.items():
            for obj in obj_list:
                obj.local_view_set(view,False)


        # Additionally remove Created HPs
        if lr_export_settings_scene.add_missing_hp == True:
            if len(objects_to_evaluate) >= 2:
                for obj in created_hp_objs:
                    bpy.data.objects.remove(bpy.data.objects.get(obj.name),do_unlink=True)

        #Restore obj names
        for obj in all_src_objects_for_export:
            obj.name = obj.lr_object_export_settings["orig_name"]

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

        lr_export_settings_scene = bpy.context.scene.lr_export_settings_scene
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
        if len(selected_objects_MESH) == 0:
            return {'FINISHED'}
        
        for index,obj in enumerate(selected_objects_MESH):

            #Store active uv map
            store_active_uv_map.append(obj.data.uv_layers.active_index)


            # List all UV maps
            uv_maps = obj.data.uv_layers.keys()
            uv_maps_amnt = len(uv_maps)-1 #Starting from 0

            if uv_maps_amnt == -1:
                message = f'Select object.'
                self.report({'WARNING'}, message)
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
        
        message = f'Done. File created next to a .blend file.'
        self.report({'INFO'}, message)


        return {'FINISHED'}


def material_cleanup(objs,remove_old = True):
    scene_material_names = [mat.name for mat in bpy.data.materials]
    materials_to_remove = []
    for obj in objs:
        if len(obj.material_slots) == 0:
            continue 

        for material_slot in obj.material_slots: 
            if material_slot.material.name[-3:].isdigit() and material_slot.material.name[-4] == ".":
                if material_slot.material.name[:-4] in scene_material_names:
                    if material_slot.material not in materials_to_remove:
                        materials_to_remove.append(material_slot.material)
                    material_slot.material = bpy.data.materials.get(material_slot.material.name[:-4])
                    
    
    if len(materials_to_remove)>0:
        if remove_old == True:
            for material in materials_to_remove:
                bpy.data.materials.remove(material)


class OBJECT_OT_lr_reimport(bpy.types.Operator):
    """ Creates packed UVMap. !Will replace existing UVs"""
    bl_idname = "object.lr_import"
    bl_label = "Pack"
    bl_options = {'REGISTER', 'UNDO'}


    
    def execute(self, context): 
        '''File is saved next to a .blend file'''
        timer_start = time.time()

        lr_export_settings_object = context.object.lr_object_export_settings
        lr_export_settings_scene = context.scene.lr_export_settings_scene

        objs_selected = bpy.context.selected_objects

        
        
        for obj in objs_selected:

            if obj.lr_object_export_settings.lr_import_path == "":
                continue
            else:
                file_path = obj.lr_object_export_settings.lr_import_path
            all_children = obj.children_recursive

            if lr_export_settings_scene.lr_import_remove_mesh:
                all_children_data = list({child.data for child in all_children if not None})



            # if lr_export_settings_scene.lr_import_remove_mesh == False:
            bpy.ops.object.select_all(action='DESELECT')

            for child in all_children:
                # bpy.data.objects.remove(child,do_unlink=True, do_id_user=True, do_ui_user=True)#SLOW AF takes about 1min with ~2k meshes
                child.select_set(True)

            bpy.ops.object.delete(use_global=False) #This is 10x faster with 2k meshes. (batch deletes)
            bpy.ops.object.select_all(action='DESELECT')


            if lr_export_settings_scene.lr_import_remove_mesh: #takes ~25s with 2k meshes
                for data in all_children_data:
                    if data:
                        bpy.data.meshes.remove(data, do_unlink=True, do_id_user=True, do_ui_user=False)#Also remove mesh


            # Import the FBX file
            bpy.ops.import_scene.fbx(filepath=bpy.path.abspath(file_path), 
                                    #  directory="", 
                                    #  filter_glob="*.fbx", 
                                    #  files=[], 
                                    #  ui_tab='MAIN', 
                                     use_manual_orientation=False, 
                                     global_scale=1, 
                                     bake_space_transform=False, 
                                     use_custom_normals=True, 
                                     colors_type='SRGB', 
                                     use_image_search=True, 
                                     use_alpha_decals=False, 
                                     decal_offset=0, 
                                     use_anim=False, 
                                     anim_offset=1, 
                                     use_subsurf=False, 
                                     use_custom_props=True, 
                                     use_custom_props_enum_as_string=True, 
                                     ignore_leaf_bones=False, 
                                     force_connect_children=False, 
                                     automatic_bone_orientation=False, 
                                     primary_bone_axis='Y', 
                                     secondary_bone_axis='X', 
                                     use_prepost_rot=True, 
                                     axis_forward='-Z', 
                                     axis_up='Y')
            

            imported_objs = bpy.context.selected_objects

            if lr_export_settings_scene.lr_import_material_cleanup:
                material_cleanup(imported_objs,remove_old=True)

            for imported_obj in imported_objs:
                
                if imported_obj.parent:
                    imported_obj.select_set(False)
                else:
                    pass
                    # imported_obj.location = obj.location
                    # imported_obj.scale = obj.scale #If scene size is 0.01 object is importex with 100 size. If this option is enabled then 
                    imported_obj.parent = obj

        bpy.ops.object.select_all(action='DESELECT')
        for obj in objs_selected:
            obj.select_set(True)

        timer_end = time.time() - timer_start
        message = f'In: {timer_end:.3f}s.'
        self.report({'INFO'}, message)


        return {'FINISHED'}
















