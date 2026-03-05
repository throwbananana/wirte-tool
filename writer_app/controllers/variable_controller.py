from writer_app.ui.variable_manager import VariableManagerPanel

class VariableController:
    def __init__(self, parent, project_manager, execute_command=None):
        self.parent = parent
        self.project_manager = project_manager
        self.execute_command = execute_command
        self.view = None
        
        self._setup_ui()
        
    def _setup_ui(self):
        self.view = VariableManagerPanel(self.parent, self.project_manager, self)
        self.view.pack(fill="both", expand=True)

    def add_variable(self, name, var_type, value, desc):
        # In a real app with undo, wrap in a Command
        return self.project_manager.add_variable(name, var_type, value, desc)
        
    def update_variable(self, uid, data):
        return self.project_manager.update_variable(uid, data)
        
    def delete_variable(self, uid):
        return self.project_manager.delete_variable(uid)
