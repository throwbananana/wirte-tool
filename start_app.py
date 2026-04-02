from tools.launchers.start_app import WriterTool, tk


def main() -> None:
    root = tk.Tk()
    app = WriterTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()
