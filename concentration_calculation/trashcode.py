import tkinter as tk
from tkinter import ttk, messagebox

# -----------------------------
# Step 1: ask for number of cats
# -----------------------------
def ask_for_number(title="Enter a value", label="Number of cats"):
    result = {"value": None}  # use a dict so inner func can modify it

    root = tk.Tk()
    root.title(title)
    root.resizable(False, False)

    ttk.Label(root, text=label).grid(row=0, column=0, padx=10, pady=10, sticky="w")
    entry = ttk.Entry(root, width=15)
    entry.grid(row=0, column=1, padx=10, pady=10)
    entry.focus()

    def on_ok(event=None):
        v = entry.get().strip()
        try:
            num = int(v)
            if num <= 0:
                raise ValueError
            result["value"] = num
            root.destroy()
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a positive integer.")

    def on_cancel(event=None):
        root.destroy()

    btn_ok = ttk.Button(root, text="OK", command=on_ok)
    btn_cancel = ttk.Button(root, text="Cancel", command=on_cancel)
    btn_ok.grid(row=1, column=0, padx=10, pady=(0, 10))
    btn_cancel.grid(row=1, column=1, padx=10, pady=(0, 10))

    root.bind("<Return>", on_ok)
    root.bind("<KP_Enter>", on_ok)
    root.bind("<Escape>", on_cancel)

    # Center the window
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 3
    root.geometry(f"+{x}+{y}")

    root.mainloop()
    return result["value"]

# -----------------------------
# Step 2: ask for cat names
# -----------------------------
def ask_for_cat_names(num_cats):
    result = {"value": []}

    root = tk.Tk()
    root.title("Enter cat names")
    root.resizable(False, False)

    ttk.Label(root, text="Enter your cat names:").grid(row=0, column=0, columnspan=2, pady=(5, 5))

    entries = []
    for i in range(num_cats):
        ttk.Label(root, text=f"Cat {i+1}:").grid(row=i + 1, column=0, padx=5, pady=2, sticky="e")
        e = ttk.Entry(root, width=20)
        e.grid(row=i + 1, column=1, padx=5, pady=2)
        entries.append(e)

    # Navigation function
    def focus_next(event, direction):
        current = event.widget
        if current in entries:
            idx = entries.index(current)
            next_idx = idx + direction
            if 0 <= next_idx < len(entries):
                entries[next_idx].focus_set()
            else:
                # optional wrap-around
                if next_idx < 0:
                    entries[-1].focus_set()
                elif next_idx >= len(entries):
                    entries[0].focus_set()
        return "break"  # prevent default cursor move inside the Entry

    # Bind arrow keys for each entry
    for e in entries:
        e.bind("<Down>", lambda ev, d=+1: focus_next(ev, d))
        e.bind("<Right>", lambda ev, d=+1: focus_next(ev, d))
        e.bind("<Up>", lambda ev, d=-1: focus_next(ev, d))
        e.bind("<Left>", lambda ev, d=-1: focus_next(ev, d))

    def on_ok(event=None):
        names = [e.get().strip() for e in entries if e.get().strip()]
        if len(names) != num_cats:
            messagebox.showerror("Invalid input", "Please fill in all cat names.")
            return
        result["value"] = names
        root.destroy()

    def on_cancel(event=None):
        root.destroy()

    btn_ok = ttk.Button(root, text="OK", command=on_ok)
    btn_cancel = ttk.Button(root, text="Cancel", command=on_cancel)
    btn_ok.grid(row=num_cats + 1, column=0, pady=10)
    btn_cancel.grid(row=num_cats + 1, column=1, pady=10)

    root.bind("<Return>", on_ok)
    root.bind("<KP_Enter>", on_ok)
    root.bind("<Escape>", on_cancel)

    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 3
    root.geometry(f"+{x}+{y}")

    entries[0].focus_set()  # focus first entry at start
    root.mainloop()
    return result["value"]

# -----------------------------
# Main program flow
# -----------------------------
def main():
    num_cats = ask_for_number()
    if not num_cats:
        print("No cats entered. Exiting.")
        return

    cat_names = ask_for_cat_names(num_cats)
    if not cat_names:
        print("No names entered. Exiting.")
        return

    print("Your cats are:", cat_names)
    messagebox.showinfo("Cat List", "\n".join(f"cat name: {name}" for name in cat_names))

if __name__ == "__main__":
    main()
