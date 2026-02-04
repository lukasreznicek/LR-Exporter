
'''
Writes object names of all selected objects to the console during export.
'''
print("READING")
def print_names(self, context):
    print("Selected objects for export:")
    for obj in self.exported_objects:
        print(" - " + obj.name)



if __name__ == "__lr_export_script__": 
    print_names(self, context)
