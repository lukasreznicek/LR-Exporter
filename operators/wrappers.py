import bpy,re

class lr_export_one_material(bpy.types.Operator):

    """Exports objects prepared for Substance Painter mask creation. Exported mesh will have only one material. 
        Exception mat: 'Occluder'"""

    bl_idname = "object.lr_export_one_material"
    bl_label = "Exports with one material"
    
    def execute(self, context):

        act_obj = bpy.context.active_object
        selected_objects = bpy.context.selected_objects
        
        ina_objmain = []
        new_help = act_obj.copy()
        bpy.context.scene.collection.objects.link(new_help)

        bpy.ops.object.select_grouped(type='CHILDREN_RECURSIVE')

        ina_objmain = [i for i in bpy.data.objects if i.select_get() == True]



        def FilterAndDuplicateSelMeshes(objs):
            #import fnmatch
            scn = bpy.context.scene   
            dupl_meshs = []

            for i in objs:
            
                if i.type == 'MESH':
                    new_obj = i.copy()
                    new_obj.data = i.data.copy()
                    scn.collection.objects.link(new_obj)
                    dupl_meshs.append(new_obj)

            return dupl_meshs       



        children_duplicated = FilterAndDuplicateSelMeshes(ina_objmain)

        #REMOVES ACTIVE OBJECT FROM SELECTION AND CHANGES ACTIVE OBJECT, FOR LATER OPERATORS
        act_obj.select_set(False)
        context.view_layer.objects.active = children_duplicated[-1]


        for i in children_duplicated:

            bpy.context.view_layer.objects.active = i
            len(i.material_slots)
            while len(i.material_slots) > 1:
                i.active_material_index = len(i.material_slots)-1
                bpy.ops.object.material_slot_remove()


        #SET MATERIAL
        mat = bpy.data.materials.new(name="MaskBake")
        
        for i in children_duplicated:
            link = i.material_slots[0].link

            #If material is linked to data:
            if link == 'DATA':
                if i.data.materials[0].name != 'Occluder':
                    i.data.materials[0] = bpy.data.materials['MaskBake']

            #If material is linked to object:
            if link == 'OBJECT':
                if i.material_slots[0].name != 'Occluder':
                    i.material_slots[0].material = bpy.data.materials['MaskBake']


        #PARENT TO
        for i in children_duplicated:
            matrix = i.matrix_world
            i.parent = new_help
            i.matrix_world = matrix


        ##SELECTS ACTIVE OBJECT
        bpy.ops.object.select_all(action='DESELECT')
        new_help.select_set(True)
        context.view_layer.objects.active = new_help

        #Naming
        store_name = act_obj.name
        new_help.name = store_name


        #EXPORT -----------------------------
        # bpy.ops.object.exportforunreal()
        bpy.ops.object.lr_exporter_export()

        #REMOVE OBJS
        bpy.ops.object.select_all(action='DESELECT')

        for obj in children_duplicated:
            bpy.data.objects.remove(obj,do_unlink=True)
        
        bpy.data.objects.remove(new_help,do_unlink=True)

        act_obj.name = store_name

        #Restore selection
        for obj in selected_objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = act_obj

        return {'FINISHED'}



class lr_exportformask(bpy.types.Operator):

    """ Exports objects with one UV Set and one material.
        Steps:
            All meshes must have UVSet named 'MaskUV'.
            Select objects to export and one active helper used as a pivot"""

    bl_idname = "object.lr_exportformask"
    bl_label = "LR Mask export - Export objects for mask"
    
    
    
    def execute(self, context):
        lr_export_settings = bpy.context.scene.lr_export
        sel_obj = bpy.context.selected_objects
        act_obj = bpy.context.active_object
        ina_objmain = []

        if len(act_obj.children) != 0:
            message = 'Not exported. Please select parent without children.'
            self.report({'INFO'}, message)
            return {'FINISHED'}


        for i in sel_obj:
            if i == bpy.context.active_object:
                pass
            else:
                ina_objmain.append(i)

        def FilterAndDuplicateSelMeshes(objs):
            import fnmatch
            scn = bpy.context.scene   
            dupl_meshs = []

            store_names = []
            for i in objs:
                if i.type == 'MESH':
                    store_names.append(i.name)
                    new_obj = i.copy()

                    new_obj.name = i.name

                    #ASSIGN DUPLICATED OBJECT INTO THE SAME COLLECTION AS ORIGINAL OBJ (For material assignment)
                    for collect in i.users_collection:
                        collect.objects.link(new_obj)

                    new_obj.data = i.data.copy()
                    #No need to link to scene. 
                    #scn.collection.objects.link(new_obj)
                    dupl_meshs.append(new_obj)

            return dupl_meshs, store_names      



        ina_obj,stored_names = FilterAndDuplicateSelMeshes(ina_objmain)

        #REMOVES ACTIVE OBJECT FROM SELECTION AND CHANGES ACTIVE OBJECT, FOR LATER OPERATORS
        act_obj.select_set(False)
        context.view_layer.objects.active = ina_obj[-1]

        def removesalluvmapsbut(objects,keepuvmapname = None):
            uv_layers = []

            for i in objects:
                k = 0
                if keepuvmapname in i.data.uv_layers: 
                    while len(i.data.uv_layers)-1 > 0:
                        if i.data.uv_layers[0+k].name == keepuvmapname:
                            k+=1
                            continue
                        else:
                            i.data.uv_layers.remove(i.data.uv_layers[0+k])

                else:
                    while len(i.data.uv_layers)-1 > 0:
                    
                            i.data.uv_layers.remove(i.data.uv_layers[1])

        removesalluvmapsbut(ina_obj,keepuvmapname = lr_export_settings.export_mask_uv_name)  


        for i in ina_obj:
            bpy.context.view_layer.objects.active = i

            while len(i.material_slots) > 1:
                i.active_material_index = len(i.material_slots)-1
                bpy.ops.object.material_slot_remove()


        #CREATE MATERIAL
        all_mats = []
        all_collections = []
        collection_name_for_occluder = 'occluder'
        mat_occluder_name = 'MaskOccluder'
        mask_id_collection_tag = '_id'





        for material in bpy.data.materials:
            all_mats.append(material.name)

        # for collection in bpy.data.collections:
        #     all_collections.append(collection.name)
        
        # if 'MaskBake_ID1' not in all_mats:
        #     mat = bpy.data.materials.new(name='MaskBake_ID1')



        # if collection_name_for_occluder in all_collections:
        #     if mat_occluder_name not in all_mats:
        #         mat_occluder = bpy.data.materials.new(name=mat_occluder_name)
        

        #SET MATERIAL
        for obj in ina_obj: 
            
            if obj.get("lr_mat_override_mask"):


                #Create material if it isn't in scene.
                mat_name = obj['lr_mat_override_mask']

                if mat_name not in all_mats:
                    bpy.data.materials.new(name=mat_name)
                    all_mats.append('mat_name')
                

                link = obj.material_slots[0].link 
                if link == 'OBJECT':
                    obj.material_slots[0].material = bpy.data.materials[str(mat_name)]


                if link == 'DATA':
                    obj.data.materials[0] = bpy.data.materials[str(mat_name)]


                #If object is in collection containing '_ID' assign material.
                #     if 'occluder' in collection_name_lower:
                #         if mat_occluder_name not in all_mats:
                #             mat_occluder = bpy.data.materials.new(name=mat_occluder_name)
                #         if link == 'OBJECT':
                #             obj.material_slots[0].material = bpy.data.materials[str(mat_occluder_name)]

                #         if link == 'DATA':
                #             obj.data.materials[0] = bpy.data.materials[mat_occluder_name]   
            else:
                continue

        #PARENT TO
        for i in ina_obj:
            matrix = i.matrix_world
            i.parent = act_obj
            i.matrix_world = matrix


        ##SELECTS ACTIVE OBJECT
        bpy.ops.object.select_all(action='DESELECT')
        
        act_obj.select_set(True)
        context.view_layer.objects.active = act_obj

        #EXPORT
        bpy.ops.object.lr_exporter_export()



        #REMOVE OBJS
        bpy.ops.object.select_all(action='DESELECT')


        for i in ina_obj:
            #i.select_set(True)

            bpy.data.meshes.remove(i.data, do_unlink=True)

        #bpy.ops.object.delete() 
        
        #Restore names
        for name,obj in zip(stored_names,ina_objmain):
            obj.name = name

        for obj in sel_obj:
            obj.select_set(True)

        bpy.context.view_layer.objects.active = act_obj




        return {'FINISHED'}
