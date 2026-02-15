
'''
Writes object names of all selected objects to the console during export.
'''
print("READING")
def print_names(self, context):
    print("--- PREPROCESS ---")
    print("Selected objects for export:")
    for obj in self.preprocess_obj_duplicates:
        print(f"Obj: {obj.name}")
        print(f"number of mat slots: {len(obj.material_slots)}")
        for idx, mat_slot in enumerate(obj.material_slots):
            print(f"Index: {idx} has material: {mat_slot.name}")

        print("---")
    print("--- PREPROCESS END ---")


if __name__ == "__lr_export_script_preprocess__": 
    print_names(self, context)
