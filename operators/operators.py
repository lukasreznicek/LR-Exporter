import bpy, os, math, numpy, bmesh
from . import utils


class OBJECT_OT_lr_hierarchy_exporter(bpy.types.Operator):
    bl_idname = "object.lr_exporter_export"
    bl_label = "Exports obj"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context): 
        normalize = numpy.linalg.norm

        #Store initial selection
        selected_objs_init = bpy.context.selected_objects
        active_obj_init = bpy.context.view_layer.objects.active
        
        blender_file_location = bpy.path.abspath('//')

        for selected_obj in selected_objs_init:            
            bpy.ops.object.select_all(action='DESELECT')
            
            bpy.context.view_layer.objects.active = selected_obj
            

            selected_obj.select_set(True)    

            children = selected_obj.children_recursive
            # bpy.ops.object.duplicates_make_real(use_hierarchy=True) WILL BE NEEDED FOR GEOMETRY NODES

            for child in children:
                child.select_set(True)

            obj_info_before = utils.SelectedObjectsInfo()
            obj_info_before.get_info()
            #--- PREPARATION ---


            #After duplication Blender automatically selects nevely created objects
            bpy.ops.object.duplicate(linked=False)

            obj_info_after = utils.SelectedObjectsInfo()
            obj_info_after.get_info()

            print('Names Before: ', obj_info_before.selected_objs_names)
            print('Names After: ', obj_info_after.selected_objs_names)
            
            print('DataNames Before: ', obj_info_before.selected_objs_data_names)
            print('DataNames After: ', obj_info_after.selected_objs_data_names)            
            
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
            print('OBJECT INFO ACTIVE BEFORE:'+obj_info_before.active_obj.name)
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
            #--- NAMING END ---


            #--- CLEANUP ---
    
                #Delete selected objects
            bpy.ops.object.delete(use_global=False)

            # Restore obj names
            obj_info_before.restore_object_names()
            obj_info_before.restore_object_data_names()

    
            #--- CLEANUP END ---
    
        #Return initial selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected_objs_init:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active_obj_init

        message = 'Exported file: '+filename_prefix_suffix
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



























