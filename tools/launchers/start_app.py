import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tkinter as tk
from writer_app.main import WriterTool

if __name__ == "__main__":
    root = tk.Tk()
    app = WriterTool(root)
    root.mainloop()
