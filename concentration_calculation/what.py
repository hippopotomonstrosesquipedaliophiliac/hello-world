import tkinter as tk
from tkinter import ttk

# Step 1: Create the big parent window class
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("My Big Window")
        self.geometry("800x600")

        # Optional shared state dict (frames can read via self.controller.state)
        self.state = {"some_value": tk.StringVar(value="hello")}

        # A container that will hold all other frames
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        # Order of frames (linear, non-circular)
        self.frame_order = ["WelcomeFrame", "SettingsFrame", "RunFrame"]
        self.current_index = 0

        # Dictionary to keep track of frames
        self.frames = {}

        # Initialize the frames you want to include in the specified order
        for name in self.frame_order:
            F = globals()[name]
            frame = F(parent=self.container, controller=self)
            self.frames[name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Build menu bar and a top Menubutton that lists frames
        self._build_menubar()
        self._build_topbar_menu()

        # Bottom navigation (Prev/Next) — linear, not circular
        self._build_bottom_nav()

        # Show the first frame
        self.show_frame(self.frame_order[self.current_index])

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()
        # sync current_index and nav button states
        if name in self.frame_order:
            self.current_index = self.frame_order.index(name)
        self._update_nav_buttons()

    def next_frame(self):
        if self.current_index < len(self.frame_order) - 1:
            self.current_index += 1
            self.show_frame(self.frame_order[self.current_index])

    def prev_frame(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_frame(self.frame_order[self.current_index])

    def _update_nav_buttons(self):
        # Disable Prev at head, Next at tail
        at_head = self.current_index == 0
        at_tail = self.current_index == len(self.frame_order) - 1
        self.prev_btn.state(["disabled"] if at_head else ["!disabled"])
        self.next_btn.state(["disabled"] if at_tail else ["!disabled"])

    def _build_menubar(self):
        menubar = tk.Menu(self)
        pages_menu = tk.Menu(menubar, tearoff=0)
        # Add a menu item for each frame in order
        for key in self.frame_order:
            label = key.replace("Frame", "")
            pages_menu.add_command(label=label, command=lambda n=key: self.show_frame(n))
        menubar.add_cascade(label="Pages", menu=pages_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=lambda: tk.messagebox.showinfo("About", "Demo big-window shell"))
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _build_topbar_menu(self):
        # Optional: a visible button with a dropdown menu of frames
        top = ttk.Frame(self)
        top.pack(fill="x")
        mb = ttk.Menubutton(top, text="Menu")
        menu = tk.Menu(mb, tearoff=0)
        for key in self.frame_order:
            label = key.replace("Frame", "")
            menu.add_command(label=label, command=lambda n=key: self.show_frame(n))
        menu.add_separator()
        menu.add_command(label="Quit", command=self.destroy)
        mb["menu"] = menu
        mb.pack(side="left", padx=6, pady=4)

    def _build_bottom_nav(self):
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", side="bottom")
        # spacer
        ttk.Label(bottom, text="").pack(side="left", expand=True)
        self.next_btn = ttk.Button(bottom, text="Next  ▶", command=self.next_frame)
        self.next_btn.pack(side="right", padx=6, pady=6)
        self.prev_btn = ttk.Button(bottom, text="◀  Back", command=self.prev_frame)
        self.prev_btn.pack(side="right", padx=(0, 6), pady=6)
       

    def _build_menubar(self):
        menubar = tk.Menu(self)
        pages_menu = tk.Menu(menubar, tearoff=0)
        # Add a menu item for each frame
        for key in self.frames.keys():
            label = key.replace("Frame", "")
            pages_menu.add_command(label=label, command=lambda n=key: self.show_frame(n))
        menubar.add_cascade(label="Pages", menu=pages_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=lambda: tk.messagebox.showinfo("About", "Demo big-window shell"))
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _build_topbar_menu(self):
        # Optional: a visible button with a dropdown menu of frames
        top = ttk.Frame(self)
        top.pack(fill="x")
        mb = ttk.Menubutton(top, text="Menu")
        menu = tk.Menu(mb, tearoff=0)
        for key in self.frames.keys():
            label = key.replace("Frame", "")
            menu.add_command(label=label, command=lambda n=key: self.show_frame(n))
        menu.add_separator()
        menu.add_command(label="Quit", command=self.destroy)
        mb["menu"] = menu
        mb.pack(side="left", padx=6, pady=4)

# Step 2: Make base frame class
class BaseFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

# Step 3: Define individual frames
class WelcomeFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        label = ttk.Label(self, text="Welcome! This is the big window.", font=("Arial", 16))
        label.pack(pady=20)

class SettingsFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        label = ttk.Label(self, text="Settings Frame", font=("Arial", 16))
        label.pack(pady=20)
        

class RunFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        label = ttk.Label(self, text="Run Frame", font=("Arial", 16))
        label.pack(pady=20)
        

# Step 4: Run the application
if __name__ == "__main__":
    app = App()
    app.mainloop()
