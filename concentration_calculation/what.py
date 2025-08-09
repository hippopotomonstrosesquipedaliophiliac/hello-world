import tkinter as tk
from tkinter import filedialog
import pandas as pd

def pick_excel_file():
    root = tk.Tk()
    root.withdraw()            # hide the empty Tk window
    path = filedialog.askopenfilename(
        title="Select an Excel file",
        filetypes=[("Excel files", "*.xlsx *.xlsm *.xls")]
    )
    root.destroy()
    return path

def load_all_sheets(path):
    # sheet_name=None returns a dict: {sheet_name: DataFrame, ...}
    # engine="openpyxl" is the default for .xlsx in recent pandas, but you can be explicit:
    dfs_by_sheet = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    return dfs_by_sheet

if __name__ == "__main__":
    excel_path = pick_excel_file()
    if not excel_path:
        print("No file selected.")
        raise SystemExit

    dfs = load_all_sheets(excel_path)

    # 1) See what you got
    print("Sheets found:", list(dfs.keys()))


    # # 3) Iterate through all sheets
    for name, df in dfs.items():
        print(f"{name}: {df.shape}")

    # 4) Concatenate all sheets into one big DataFrame with a sheet label
    stacked = pd.concat(dfs, names=["sheet", "row"]).reset_index(level="sheet")
    print(stacked.head())

    # # 5) Optionally write each sheet to CSV
    # for name, df in dfs.items():
    #     safe = "".join(c for c in name if c.isalnum() or c in "-_ ")
    #     df.to_csv(f"{safe}.csv", index=False)
