# helpertesting.py
import tkinter as tk
from tkinter import ttk

class UI:
    def __init__(self):
        self.root = tk.Tk()
        # self.root.withdraw()  # start hidden if you like

    def show_overwrite_dialog(self, title, label_text):
        # modal toplevel
        win = tk.Toplevel(self.root)
        win.title(title)
        win.resizable(False, False)
        ttk.Label(win, text=label_text).grid(row=0, column=0, padx=12, pady=12)

        self._result = None
        def on_ok():
            self._result = True
            win.destroy()
        def on_cancel():
            self._result = False
            win.destroy()

        btns = ttk.Frame(win)
        btns.grid(row=1, column=0, pady=(0,12))
        ttk.Button(btns, text="Overwrite", command=on_ok).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Cancel", command=on_cancel).grid(row=0, column=1, padx=6)

        win.transient(self.root)
        win.grab_set()      # modal
        self.root.wait_window(win)
        return self._result

    def start(self):
        # call once if you have a real GUI; not needed for pure modal popups
        self.root.deiconify()
        self.root.mainloop()
# testing.py
import os

def main():
    ui = UI()  # ONE root for the whole app

    output_path = "concentration_requesting_data.xlsx"
    if os.path.exists(output_path):
        ok = ui.show_overwrite_dialog(
            title="File already exists",
            label_text="File already exists. Overwrite the previous data?"
        )
        if not ok:
            print("Canceled by user.")
            return
        os.remove(output_path)

    # ... proceed to compute and write Excel ...
    # If you need a full GUI, end with:
    # ui.start()

if __name__ == "__main__":
    main()
