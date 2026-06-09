
'''
Writes object names of all selected objects to the console during export.
'''
def main(self, context):
    print("Selected objects for export:")
    for obj in self.exported_objects:
        print(" - " + obj.name)



