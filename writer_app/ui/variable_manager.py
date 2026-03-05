import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class VariableManagerPanel(ttk.Frame):
    def __init__(self, parent, project_manager, controller):
        super().__init__(parent)
        self.project_manager = project_manager
        self.controller = controller
        
        self.setup_ui()
        self.project_manager.add_listener(self.refresh)
        self.refresh()
        
    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="新建变量", command=self.add_var).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="编辑", command=self.edit_var).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除", command=self.delete_var).pack(side=tk.LEFT, padx=2)
        
        # Table
        cols = ("name", "type", "status", "desc")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("name", text="变量名")
        self.tree.heading("type", text="类型")
        self.tree.heading("status", text="当前状态")
        self.tree.heading("desc", text="描述")
        
        self.tree.column("name", width=150)
        self.tree.column("type", width=100)
        self.tree.column("status", width=150)
        self.tree.column("desc", width=300)
        
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<Double-1>", self.on_double_click)

    def refresh(self, event_type="all"):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        vars_list = self.project_manager.get_variables()
        for v in vars_list:
            v_type = v.get("type")
            raw_val = v.get("value")
            
            # Type Display (Friendly Names)
            type_map = {
                "bool": "事件开关",
                "int": "程度等级",
                "str": "文本信息"
            }
            display_type = type_map.get(v_type, v_type)
            
            # Status Display (Qualitative & Narrative)
            if v_type == "bool":
                status = "已触发" if str(raw_val).lower() in ("true", "1") else "未触发"
            elif v_type == "int":
                try:
                    val = int(raw_val)
                    name_lower = v.get("name", "").lower()
                    
                    # Heuristic: Relationship variables
                    rel_keywords = ["好感", "羁绊", "love", "trust", "affection", "rel", "like", "hate"]
                    if any(k in name_lower for k in rel_keywords):
                        if val <= 0: status = "敌对/冷漠"
                        elif val < 20: status = "疏离"
                        elif val < 40: status = "相识"
                        elif val < 60: status = "友好"
                        elif val < 80: status = "暧昧/亲密"
                        else: status = "挚爱/至死不渝"
                    else:
                        # Standard quantity variables
                        if val <= 0: status = "无 (Empty)"
                        elif val < 20: status = "微弱 (Trace)"
                        elif val < 40: status = "少量 (Low)"
                        elif val < 60: status = "适中 (Medium)"
                        elif val < 80: status = "丰富 (High)"
                        else: status = "极高 (Max)"
                except:
                    status = "未知"
            else:
                status = str(raw_val)

            self.tree.insert("", tk.END, values=(
                v.get("name"),
                display_type,
                status,
                v.get("desc", "")
            ), tags=(v.get("uid"),))
            
    def add_var(self):
        dlg = VariableDialog(self.winfo_toplevel())
        if dlg.result:
            self.controller.add_variable(
                dlg.result["name"],
                dlg.result["type"],
                dlg.result["value"],
                dlg.result["desc"]
            )
            self.refresh()
            
    def edit_var(self):
        sel = self.tree.selection()
        if not sel: return
        item = self.tree.item(sel[0])
        uid = item["tags"][0]
        
        vars_list = self.project_manager.get_variables()
        var_data = next((v for v in vars_list if v["uid"] == uid), None)
        
        if var_data:
            dlg = VariableDialog(self.winfo_toplevel(), var_data)
            if dlg.result:
                self.controller.update_variable(uid, dlg.result)
                self.refresh()
                
    def delete_var(self):
        sel = self.tree.selection()
        if not sel: return
        item = self.tree.item(sel[0])
        uid = item["tags"][0]
        
        if messagebox.askyesno("确认删除", "确定要删除这个变量吗？"):
            self.controller.delete_variable(uid)
            self.refresh()

    def on_double_click(self, event):
        self.edit_var()

class VariableDialog(simpledialog.Dialog):
    def __init__(self, parent, initial_data=None):
        self.initial_data = initial_data or {}
        # Mapping friendly names to backend types
        self.reverse_map = {"bool": "事件开关 (Flag)", "int": "程度等级 (Level)", "str": "文本信息 (Text)"}
        self.type_map_data = {v: k for k, v in self.reverse_map.items()}
        super().__init__(parent, title="变量编辑")
        
    def body(self, master):
        tk.Label(master, text="变量名 (ID):").grid(row=0, column=0, sticky="e")
        self.e_name = tk.Entry(master, width=20)
        self.e_name.grid(row=0, column=1, padx=5, pady=5)
        self.e_name.insert(0, self.initial_data.get("name", ""))
        
        tk.Label(master, text="类型:").grid(row=1, column=0, sticky="e")
        self.cb_type = ttk.Combobox(master, values=list(self.reverse_map.values()), state="readonly")
        self.cb_type.grid(row=1, column=1, padx=5, pady=5)
        
        current_type = self.initial_data.get("type", "bool")
        self.cb_type.set(self.reverse_map.get(current_type, list(self.reverse_map.values())[0]))
        
        tk.Label(master, text="初始值:").grid(row=2, column=0, sticky="e")
        self.e_value = tk.Entry(master, width=20)
        self.e_value.grid(row=2, column=1, padx=5, pady=5)
        self.e_value.insert(0, str(self.initial_data.get("value", "")))
        
        tk.Label(master, text="描述:").grid(row=3, column=0, sticky="e")
        self.e_desc = tk.Entry(master, width=30)
        self.e_desc.grid(row=3, column=1, padx=5, pady=5)
        self.e_desc.insert(0, self.initial_data.get("desc", ""))
        
        return self.e_name
        
    def apply(self):
        val = self.e_value.get()
        ui_type = self.cb_type.get()
        vtype = self.type_map_data.get(ui_type, "bool")
        
        final_val = val
        if vtype == "bool":
            final_val = val.lower() in ("true", "1", "yes")
        elif vtype == "int":
            try:
                final_val = int(val)
            except:
                final_val = 0
        
        self.result = {
            "name": self.e_name.get().strip(),
            "type": vtype,
            "value": final_val,
            "desc": self.e_desc.get().strip()
        }