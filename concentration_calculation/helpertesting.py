import pandas as pd
import docx
import re
re = re
import sys
sys.path.append(r"C:\Users\nhanp\Documents\GitHub\S-matrix")
import CalcALL
from openpyxl import load_workbook
import os
import sympy as sp
import numpy as np
from collections import Counter
import copy
import tkinter as tk 
from tkinter import ttk, messagebox, filedialog
from openpyxl import Workbook
#make a linked list to link all the data in the dataframe, this is to prevent out 
# class data_frame_node:
#     def __init__(self):
#         self.head
#         self.prev
#         self.next 

class Species_class:
    def __init__(self, docx_path=None, equations_list_input=None):
        self.docx_path = docx_path
        self.reaction_data = pd.DataFrame(columns=[
            'Keq', 'Reactants', 'Products', 'Equilibrium Concentration'
        ])
        self.equilibrium_concentration_list = []
        if docx_path is not None:
            self.equations = self._read_equations()
        elif equations_list_input is not None:
            self.equations = equations_list_input
        else:
            raise ValueError("Either docx_path or equations_list_input must be provided.")
        self.arrow = "="
        self.equilibrium_arrows_list = ["⇌", "<=>", "<->"]
        self.known_compartments = {
            "C": ("Cytosol", 0.643),
            "M": ("Mitochondria", 0.10),
            "N": ("Nucleus", 0.151),
            "V": ("Vacuoles", 0.08),
            "ER": ("Endoplasmic reticula", 0.026)
        }
        self.species_compartment_map = {}

class Species_class:
    def __init__(self, docx_path=None, equations_list_input=None):
        self.docx_path = docx_path
        self.reaction_data = pd.DataFrame(columns=[
            'Keq', 'Reactants', 'Products', 'Equilibrium Concentration'
        ])
        self.equilibrium_concentration_list = []
        if docx_path is not None:
            self.equations = self._read_equations()
        elif equations_list_input is not None:
            self.equations = equations_list_input
        else:
            raise ValueError("Either docx_path or equations_list_input must be provided.")
        self.arrow = "="
        self.equilibrium_arrows_list = ["⇌", "<=>", "<->"]
        self.known_compartments = {
            "C": ("Cytosol", 0.643),
            "M": ("Mitochondria", 0.10),
            "N": ("Nucleus", 0.151),
            "V": ("Vacuoles", 0.08),
            "ER": ("Endoplasmic reticula", 0.026)
        }
        self.species_compartment_map = {}
    def _is_number(self,s):
        try:
            float(s)
            return True
        except ValueError:
            return False    
    def extract_species_parts(self, raw_term):
        parts = raw_term.split("*")

        # Format: M*4.2*AA
        if len(parts) == 3:
            comp, coeff, species = parts
            if comp not in self.known_compartments:
                raise ValueError(f"Unknown compartment '{comp}' in '{raw_term}'")
            if not self._is_number(coeff):
                raise ValueError(f"Invalid coefficient '{coeff}' in '{raw_term}'")
            return species, comp, float(coeff)

        # Format: 4.2*AA or M*ATP
        elif len(parts) == 2:
            print(f"working parts {parts}")
            match_part = None
            for part in parts:
                buffer = re.match(r'^([A-Z]+)?(\d+(?:\.\d+)?)([A-Za-z]\w*)$', part)
                if buffer:
                    match_part = tuple(buffer_iter for buffer_iter in buffer.groups() if buffer_iter is not None)
                else:
                    none_match_part = part       

            if match_part:
                for match_iter in match_part:
                    if self._is_number(match_iter):
                        print(match_iter)
                        match_coeff = float(match_iter)
                    else:
                        match_name = match_iter
                return match_name, none_match_part, match_coeff 
            elif not match_part:
                left, right = parts
                # Case: 4.2*AA (implicit Cytosol)
                if self._is_number(left):
                    return right, 'C', float(left)
                # Case: AA*4.2
                elif self._is_number(right):
                    return left, 'C', float(right)
                elif isinstance(left,str) and isinstance(right,str):
                    if left in self.known_compartments:
                        return right, left, 1.0
                    else:
                        return left, right, 1.0
                    
            else:
                raise ValueError(f"Unrecognized format: '{raw_term}'")

        # # Format: single term like 4.2AA or M4.2AA (merged)
        elif len(parts) == 1:
            match = re.match(r'^([A-Z]+)?(\d+(?:\.\d+)?)([A-Za-z]\w*)$', raw_term)
            if match:
                comp, coeff, species = match.groups()
                comp = comp if comp in self.known_compartments else 'C'
                return species, comp, float(coeff)
            return raw_term, 'C', 1.0

        else:
            raise ValueError(f"Too many asterisks in '{raw_term}'")


    def extract_compartment(self, raw_name):
        print(f"[DEBUG] Raw input to extract_compartment: '{raw_name}'")
        species, comp, _ = self.extract_species_parts(raw_name)
        return species, comp

    def _read_equations(self):
        doc = docx.Document(self.docx_path)
        return [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    def _parse_equation(self, equation, reaction_number=0):
        def parse_side(side, label, reaction_number):
            species_dict = {}
            for term in side.split("+"):
                term = term.strip()
                if not term:
                    continue
                try:
                    species, comp, coeff = self.extract_species_parts(term)
                except ValueError:
                    continue
                self.species_compartment_map[species] = comp
                key = (species, label, comp)
                species_dict[key] = coeff
            return [(sp, coeff, label, reaction_number, comp) for (sp, label, comp), coeff in species_dict.items()]

        keq_value = None
        keq_match = re.search(r'keq\s*=\s*([\d\.]+)', equation, re.IGNORECASE)
        if keq_match:
            keq_value = float(keq_match.group(1))
            equation = equation[:keq_match.start()].strip()

        for arrow in self.equilibrium_arrows_list:
            if arrow in equation:
                self.arrow = arrow
                break

        equation = re.sub(fr'[^\w\s\+\*\.={self.arrow}]', '', equation)
        sides = equation.split(self.arrow)
        if len(sides) != 2 or not sides[0].strip() or not sides[1].strip():
            return [], [], keq_value

        reactants = parse_side(sides[0], "Reactant", reaction_number)
        products = parse_side(sides[1], "Product", reaction_number)
        return reactants, products, keq_value

    def _initialize_species_from_reaction(self, dropped_species_set=None):
        self.reaction_data = pd.DataFrame(columns=['Keq', 'Reactants', 'Products', 'Equilibrium Concentration'])
        for i, eq in enumerate(self.equations):
            reactants, products, keq = self._parse_equation(eq, reaction_number=i)
            if dropped_species_set:
                reactants = [r for r in reactants if r[0] not in dropped_species_set]
                products = [p for p in products if p[0] not in dropped_species_set]

            reactant_data = [(sp, label, '', coeff, rxn+1, comp) for sp, coeff, label, rxn, comp in reactants]
            product_data = [(sp, label, 0.0, coeff, rxn+1, comp) for sp, coeff, label, rxn, comp in products]

            if not reactant_data and not product_data:
                continue

            self.reaction_data = pd.concat([self.reaction_data, pd.DataFrame([{
                'Keq': keq,
                'Reactants': reactant_data,
                'Products': product_data,
                'Equilibrium Concentration': 0.0
            }])], ignore_index=True)


    def construct_concentration_data(self, output_path="concentration_requesting_data.xlsx",system_index=0):

        total_fraction = sum([v[1] for v in self.known_compartments.values()])
        if abs(total_fraction - 1.0) > 1e-6:
            raise ValueError(f"Compartment fractions do not sum to 1. Current sum: {total_fraction}")
        
        reactant_species = set()
        for _, row in self.reaction_data.iterrows():
            for sp, label, conc, coeff, rxn_num, comp in row['Reactants']:
                if label == "Reactant":
                    reactant_species.add(sp)

        df = pd.DataFrame({
            "species": list(reactant_species),
            "initial cellular concentration recorded": ["" for _ in reactant_species]
        })
        try: 
            with pd.ExcelWriter(output_path, engine='openpyxl', mode='a',if_sheet_exists="replace") as writer:
                df.to_excel(writer, index=False, sheet_name=f"Concentration Request data {system_index}")
        except FileNotFoundError:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name=f"Concentration Request data {system_index}")
            print(f"[INFO] File {output_path} not found. Created a new file name {output_path}.")
        return output_path
    def request_concentration_data(self):
        return
        # root = tk.Tk()
        # root.withdraw()

        # input("[WAITING] Press Enter after you have filled in the file...")

        # df_filled = pd.read_excel(output_path, sheet_name=f"Concentration Request data {system_index}")
        # df_filled.columns = [col.strip().lower() for col in df_filled.columns]
        # species_concentration_map = {
        #     str(row[0]).strip(): row[1]
        #     for row in df_filled.itertuples(index=False)
        #     if pd.notna(row[1])
        # }

        # updated_reaction_data = []
        # for _, row in self.reaction_data.iterrows():
        #     keq = row['Keq']
        #     updated_reactants = []
        #     for sp, label, conc, coeff, rxn_num, comp in row['Reactants']:
        #         if sp in species_concentration_map:
        #             conc = species_concentration_map[sp]
        #         updated_reactants.append((sp, label, conc, coeff, rxn_num, comp))
        #     updated_reaction_data.append({
        #         'Keq': keq,
        #         'Reactants': updated_reactants,
        #         'Products': row['Products'],
        #         'Equilibrium Concentration': row['Equilibrium Concentration']
        #     })

        # self.reaction_data = pd.DataFrame(updated_reaction_data)
        # print("[DONE] Cellular concentrations assigned successfully.")

    

    def export_species_template(self, output_file=None):
        if output_file is None:
            output_file = "concentration_input_data.xlsx"
        species_entries = []
        entry_idx = 1
        for reaction_idx, row in self.reaction_data.iterrows():
            for species, label, conc, coeff, rxn, comp in row['Reactants']:
                species_entries.append({
                    'Reaction Number': rxn,
                    'coefficient': coeff,
                    'Species': species,
                    'Description': '',
                    'S or P': 'S',
                    'Compartment': comp,
                    'Iron Content': 'no',
                    'Steady-State [] in uM': conc,
                    'Manual Input': 'TRUE'
                })
                entry_idx += 1
            for species, label, conc, coeff, rxn, comp in row['Products']:
                species_entries.append({
                    'Reaction Number': rxn,
                    'coefficient': coeff,
                    'Species': species,
                    'Description': '',
                    'S or P': 'P',
                    'Compartment': comp,
                    'Iron Content': 'no',
                    'Steady-State [] in uM': conc if conc else 0.0,
                    'Manual Input': 'TRUE'
                })
                entry_idx += 1

        df = pd.DataFrame(species_entries)
        if output_file.endswith('.csv'):
            df.to_csv(output_file, index=False)
        elif output_file.endswith('.xlsx'):
            df.to_excel(output_file, index=False)
        else:
            raise ValueError("Output file must be a .csv or .xlsx")
        print(f"Species template exported to {output_file}")
    
    @property
    def species(self):
        all_species = set()
        for idx, eq in enumerate(self.equations):
            reactants, products, _ = self._parse_equation(eq, reaction_number=idx)
            all_species.update([r[0] for r in reactants])
            all_species.update([p[0] for p in products])
        return all_species

    def get_species_dataframe(self, output_file=None):
        if output_file is None:
            output_file = "reaction_data_buffer.xlsx"
        if self.reaction_data.empty:
            raise ValueError("No reaction data available to export.")
        if output_file.endswith('.csv'):
            self.reaction_data.to_csv(output_file, index=False)
        elif output_file.endswith('.xlsx'):
            self.reaction_data.to_excel(output_file, index=False)
        else:
            raise ValueError("Output file must be a .csv or .xlsx")
        print(f"Reaction data exported to {output_file}")
        return pd.DataFrame(self.reaction_data)


# Bind the method to the Species_class

class SpeciesMatrix(Species_class):
    def __init__(self, docx_path=None, equations_list_input=None, dropped_species_set=None,data_file_input=None):
        super().__init__(docx_path=docx_path, equations_list_input=equations_list_input)
    @staticmethod
    def sum_species_concentration(reactants_list, products_list):
        """
        Sum all concentrations in a species list.
        Each item in species_list should be (species, concentration, label, coefficient).
        """
        reactant_sum = 0
        for row in reactants_list:
            reactant_sum += sum(iter[2] for iter in row)
        product_sum = 0
        for row in products_list:
            product_sum += sum(iter[2] for iter in row)
        return reactant_sum + product_sum

    def calculate_equilibrium(self):
        def updating_species(overlapping_list, index, data_to_update, column_name):
            for i in range (len(self.reaction_data.at[index,column_name])):
                next_item = (self.reaction_data.at[index,column_name][i][0], self.reaction_data.at[index,column_name][i][1], self.reaction_data.at[index,column_name][i][4])
                for i in range(len(overlapping_list)):
                    if next_item in overlapping_list[i]:
                        # Remove by value, not by index
                        buffer_conc = self.reaction_data.at[index,column_name][i][2]
                        if next_item in overlapping_list[i]:
                            overlapping_list[i].remove(next_item)
                            buffer_conc = sum(data_iter[2] for data_iter in data_to_update if data_iter[0] == self.reaction_data.at[index,column_name][i][0])
                            print(buffer_conc)
                            self.reaction_data.at[index,column_name][i] = (self.reaction_data.at[index,column_name][i][0], self.reaction_data.at[index,column_name][i][1], buffer_conc, self.reaction_data.at[index,column_name][i][3], self.reaction_data.at[index,column_name][i][4])
            return overlapping_list

        # Step 1: Build global concentration dictionary
        species_counter = Counter()
        print(species_counter)
        for row in self.reaction_data['Reactants']:
            for species, label, conc, coeff, rxn_num,comp in row:
                species_counter[species] += 1
        for row in self.reaction_data['Products']:
            for species, label, conc, coeff, rxn_num, comp in row:
                species_counter[species] += 1
        overlapping_species = {sp for sp, count in species_counter.items() if count > 1}
        over_lapping_big_list = []
        for current_observation in overlapping_species:
            over_lapping_current = []
            for row in self.reaction_data['Reactants']:
                for species, label, conc, coeff, rxn_num, comp in row:
                    if species == current_observation:
                        over_lapping_current.append((species, label, rxn_num))
            for row in self.reaction_data['Products']:
                for species, label, conc, coeff, rxn_num, comp in row:
                    if species == current_observation:
                        over_lapping_current.append((species, label, rxn_num))
            over_lapping_big_list.append(over_lapping_current)
        for i in range(len(over_lapping_big_list)):
            over_lapping_big_list[i].sort(key=lambda x: x[2])

        print(f"sorted overlapping species list: {over_lapping_big_list}")
        index = 0
        while index < 10:
            equilibrium_solutions_buffer_array = []
            buffer_overlapping_list = copy.deepcopy(over_lapping_big_list)
            for row in self.reaction_data.itertuples():
                current_index = row.Index
                x = sp.symbols("x")
                reactant_expr = sp.prod([pow((iter[2] - x), iter[3]) for iter in row.Reactants])
                product_expr = sp.prod([pow((iter[2] + x), iter[3]) for iter in row.Products])
                poly_expr = sp.expand(row.Keq * reactant_expr - product_expr)
                coeffs = sp.Poly(poly_expr, x).all_coeffs()
                coeffs_numeric = [float(coef.evalf()) for coef in coeffs]
                roots = np.roots(coeffs_numeric)
                valid_solutions = []
                for sol in roots:
                    if np.isreal(sol):
                        sol_real = np.real(sol)
                        reactant_value = reactant_expr.subs(x, sol_real)
                        product_value = product_expr.subs(x, sol_real)
                        if (reactant_value != 0 and all((val[2] - sol_real * val[3]) >= 0 for val in row.Reactants)) and (product_value != 0 and all((val[2] + sol_real * val[3]) >= 0 for val in row.Products)):
                            valid_solutions.append(sol_real)
                equilibrium_solutions_buffer_array.extend(valid_solutions)
                delta = valid_solutions[0] if valid_solutions else 0

                updated_reactants = [(specimen, label, conc - delta*coeff, coeff, rxn_num, comp) for specimen, label, conc, coeff, rxn_num, comp in row.Reactants]
                updated_products = [(specimen, label, conc + delta*coeff, coeff, rxn_num, comp) for specimen, label, conc, coeff, rxn_num, comp in row.Products]
                complete_update_list = updated_reactants + updated_products
                self.reaction_data.at[row.Index, 'Reactants'] = updated_reactants
                self.reaction_data.at[row.Index, 'Products'] = updated_products

                next_index = current_index + 1
                if next_index in self.reaction_data.index:
                    buffer_overlapping_list = updating_species(
                        overlapping_list=buffer_overlapping_list,
                        index=next_index,
                        data_to_update=complete_update_list,
                        column_name="Reactants"
                    )
                    buffer_overlapping_list = updating_species(
                        overlapping_list=buffer_overlapping_list,
                        index=next_index,
                        data_to_update=complete_update_list,
                        column_name="Products"
                    )
                else:
                    buffer_overlapping_list = updating_species(
                        overlapping_list=buffer_overlapping_list,
                        index=0,
                        data_to_update=complete_update_list,
                        column_name="Reactants"
                    )
                    buffer_overlapping_list = updating_species(
                        overlapping_list=buffer_overlapping_list,
                        index=0,
                        data_to_update=complete_update_list,
                        column_name="Products"
                    )
            print(f"equilibrium_solutions_buffer_array: {equilibrium_solutions_buffer_array}")
            if np.count_nonzero(equilibrium_solutions_buffer_array)!=0:
                index += 1
                continue
            else:
                print("equilibrium is reached")
                break
        print(equilibrium_solutions_buffer_array)
        self.get_species_dataframe(output_file="species_concentration_output.xlsx")
class miscellaneous():
    def __init__(self):
        # one persistent root; keep it hidden unless you run a full GUI
        self.root = tk.Tk()

    def confirm(self, title="Confirm", label="Are you sure?"):
        """Modal Yes/No dialog. Returns True for OK, False for Cancel."""
        win = tk.Toplevel(self.root)
        win.title(title)
        win.resizable(False, False)

        # message
        ttk.Label(win, text=label, wraplength=420, justify="left").grid(
            row=0, column=0, columnspan=2, padx=12, pady=12, sticky="w"
        )

        result = {"value": False}  # closure box

        def on_ok(_evt=None):
            result["value"] = True
            win.destroy()

        def on_cancel(_evt=None):
            result["value"] = False
            win.destroy()

        # buttons
        ttk.Button(win, text="Overwrite", command=on_ok).grid(row=1, column=0, padx=8, pady=(0, 12))
        ttk.Button(win, text="Cancel", command=on_cancel).grid(row=1, column=1, padx=8, pady=(0, 12))

        # keyboard shortcuts
        win.bind("<Return>", on_ok)
        win.bind("<KP_Enter>", on_ok)
        win.bind("<Escape>", on_cancel)
        win.protocol("WM_DELETE_WINDOW", on_cancel)

        # make modal
        win.transient(self.root)
        win.grab_set()
        win.update_idletasks()

        # center
        w, h = win.winfo_width(), win.winfo_height()
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 3
        win.geometry(f"+{x}+{y}")

        # block until window closes
        self.root.wait_window(win)
        return result["value"]

    def close(self):
        """Call once when your app is really done with Tk."""
        if self.root:
            self.root.destroy()
            self.root = None

    # Clean up redundant pluses and spaces    
    @staticmethod
    def clean_equation(equation):
        # Remove standalone numbers (not followed by letters)
        equation = re.sub(r'(?<![A-Za-z])\b\d+\b(?![A-Za-z])', '', equation)
        # Replace multiple pluses with a single plus
        equation = re.sub(r'\++', '+', equation)
        # Remove pluses before/after arrows (=, ⇌, <=>, <->)
        equation = re.sub(r'\+\s*(=|⇌|<=>|<->)', r'\1', equation)
        equation = re.sub(r'(=|⇌|<=>|<->)\s*\+', r'\1', equation)
        # Remove pluses at the start/end
        equation = re.sub(r'^\s*\+\s*', '', equation)
        equation = re.sub(r'\s*\+\s*$', '', equation)
        # Remove empty reactant or product sides (e.g., "+ ⇌" or "+ =")
        equation = re.sub(r'(\s*[\=⇌<=><->]\s*)\+', r'\1', equation)
        equation = re.sub(r'\+(\s*[\=⇌<=><->]\s*)', r'\1', equation)
        # Remove extra spaces
        equation = re.sub(r'\s+', ' ', equation).strip()
        return equation