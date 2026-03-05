import tkinter as tk
from tkinter import ttk, messagebox
import json

class WordBankEditor(tk.Toplevel):
    def __init__(self, parent, manager):
        super().__init__(parent)
        self.title("Custom Word Bank Editor")
        self.geometry("600x500")
        self.manager = manager
        
        self.setup_ui()
        self.load_current_data()

    def setup_ui(self):
        # Input Form
        form_frame = ttk.LabelFrame(self, text="Add New Word")
        form_frame.pack(fill=tk.X, padx=10, pady=10)
        
        grid = ttk.Frame(form_frame)
        grid.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(grid, text="Chinese (CN):").grid(row=0, column=0, padx=5, pady=5)
        self.cn_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.cn_var).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(grid, text="English (EN):").grid(row=0, column=2, padx=5, pady=5)
        self.en_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.en_var).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(grid, text="Type:").grid(row=1, column=0, padx=5, pady=5)
        self.type_var = tk.StringVar(value="noun_concrete")
        type_combo = ttk.Combobox(grid, textvariable=self.type_var, state="readonly")
        type_combo['values'] = ["noun_concrete", "noun_abstract", "verb", "adjective"]
        type_combo.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(grid, text="Tags (comma sep):").grid(row=1, column=2, padx=5, pady=5)
        self.tags_var = tk.StringVar()
        ttk.Entry(grid, textvariable=self.tags_var).grid(row=1, column=3, padx=5, pady=5)
        
        ttk.Button(form_frame, text="Add Word", command=self.add_word).pack(pady=5)
        
        # List View
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tree = ttk.Treeview(list_frame, columns=("CN", "EN", "Type", "Tags"), show="headings")
        self.tree.heading("CN", text="Chinese")
        self.tree.heading("EN", text="English")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Tags", text="Tags")
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)
        
        # Save Button
        ttk.Button(self, text="Save Changes to File", command=self.save_to_file).pack(pady=10)

    def load_current_data(self):
        # Flatten data for display
        data = self.manager.word_bank_data
        
        self.insert_items(data.get("nouns", {}).get("concrete", []), "noun_concrete")
        self.insert_items(data.get("nouns", {}).get("abstract", []), "noun_abstract")
        self.insert_items(data.get("verbs", []), "verb")
        self.insert_items(data.get("adjectives", []), "adjective")

    def insert_items(self, items, type_str):
        for item in items:
            tags = ", ".join(item.get("tags", []))
            self.tree.insert("", tk.END, values=(item['cn'], item['en'], type_str, tags))

    def add_word(self):
        cn = self.cn_var.get().strip()
        en = self.en_var.get().strip()
        w_type = self.type_var.get()
        tags_str = self.tags_var.get().strip()
        
        if not cn or not en:
            messagebox.showwarning("Missing Data", "CN and EN fields are required.")
            return
            
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        
        self.tree.insert("", 0, values=(cn, en, w_type, ", ".join(tags)))
        
        # Clear inputs
        self.cn_var.set("")
        self.en_var.set("")
        self.tags_var.set("")

    def save_to_file(self):
        # Reconstruct JSON structure from Treeview
        new_data = {
            "nouns": {"concrete": [], "abstract": []},
            "verbs": [],
            "adjectives": [],
            "templates": self.manager.word_bank_data.get("templates", []) # Preserve templates
        }
        
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            cn, en, w_type, tags_str = vals
            tags = [t.strip() for t in tags_str.split(", ") if t.strip()]
            
            entry = {"cn": cn, "en": en, "tags": tags}
            
            if w_type == "noun_concrete":
                new_data["nouns"]["concrete"].append(entry)
            elif w_type == "noun_abstract":
                new_data["nouns"]["abstract"].append(entry)
            elif w_type == "verb":
                new_data["verbs"].append(entry)
            elif w_type == "adjective":
                new_data["adjectives"].append(entry)
        
        # Update manager and file
        self.manager.word_bank_data = new_data
        # We need to write to file manually here as manager might not have save method exposed
        # But manager has load_word_bank. Let's add save or do it here.
        # Doing it here for now assuming path knowledge or modify manager.
        try:
            # Re-use the path from manager logic (assuming standard location)
            from pathlib import Path
            path = Path(__file__).parent.parent.parent / "writer_data" / "word_bank.json"
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Success", "Word Bank updated successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
