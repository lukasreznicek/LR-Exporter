"""
Test rename exported object.
"""

def rename_obj(self, context):
    self.selection_capture.active_obj.name = "Renamed_Object"

if __name__ == "__lr_export_script__": 
    rename_obj(self, context)



