import tkinter as tk
from tkinter import ttk

root = tk.Tk()
style = ttk.Style()

# Simulate the issue
style.theme_use('vista') 
style.configure("Test.TButton", foreground="#E0E0E0", background="#333333")

btn = ttk.Button(root, text="Vista Theme (White Text)", style="Test.TButton")
btn.pack(pady=20, padx=20)

# Simulate the fix
style2 = ttk.Style()
style2.theme_use('clam')
style2.configure("Fix.TButton", foreground="#E0E0E0", background="#333333")

btn2 = ttk.Button(root, text="Clam Theme (Fix)", style="Fix.TButton")
btn2.pack(pady=20, padx=20)

root.mainloop()