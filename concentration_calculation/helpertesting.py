import pandas as pd
import docx
import re, os
import sympy as sp
import numpy as np
from collections import Counter
import copy
from scipy.stats import linregress
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
            for part in parts:
                if self._is_number(part):
                    coeff = part
                elif part in self.known_compartments:
                    comp = part
                else:
                    coeff = part
            if comp not in self.known_compartments:
                raise ValueError(f"Unknown compartment '{comp}' in '{raw_term}'")
            if not self._is_number(coeff):
                raise ValueError(f"Invalid coefficient '{coeff}' in '{raw_term}'")
            return species, comp, float(coeff)

        # Format: 4.2*AA or M*ATP
        elif len(parts) == 2:
            # print(f"working parts {parts}")
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
        # Explicit dtypes so list-like fields are always object and numerics are floats
        self.reaction_data = pd.DataFrame({
            'Keq': pd.Series(dtype='float'),
            'Reactants': pd.Series(dtype='object'),
            'Products': pd.Series(dtype='object'),
            'Equilibrium Concentration': pd.Series(dtype='float'),
        })

        for i, eq in enumerate(self.equations):
            reactants, products, keq = self._parse_equation(eq, reaction_number=i)
            if dropped_species_set:
                reactants = [r for r in reactants if r[0] not in dropped_species_set]
                products = [p for p in products if p[0] not in dropped_species_set]

            reactant_data = [(sp, label, 0.0, float(coeff), rxn+1, comp) for sp, coeff, label, rxn, comp in reactants]
            product_data = [(sp, label, 0.0, int(coeff), rxn+1, comp) for sp, coeff, label, rxn, comp in products]

            if not reactant_data and not product_data:
                continue

            row = {
                'Keq': float(keq) if keq is not None else float('nan'),
                'Reactants': reactant_data if reactant_data is not None else [],
                'Products': product_data if product_data is not None else [],
                'Equilibrium Concentration': 0.0,
            }
            row_df = pd.DataFrame([row], columns=self.reaction_data.columns)
            # Keep old behavior explicitly; ignore_index ensures clean append
            self.reaction_data = pd.concat([self.reaction_data, row_df], ignore_index=True)
            row_df = row_df.dropna(axis=1, how='all')



    def construct_concentration_data(self, output_path: str = None, system_name: str = None, to_rewrite: bool = False):
        # sanity check on compartment fractions
        total_fraction = sum(v[1] for v in self.known_compartments.values())
        if abs(total_fraction - 1.0) > 1e-6:
            raise ValueError(f"Compartment fractions do not sum to 1. Current sum: {total_fraction}")

        # include ALL species from both sides
        species_set = set()
        for _, row in self.reaction_data.iterrows():
            for sp_name, label, conc, coeff, rxn_num, comp in row["Reactants"]:
                species_set.add(sp_name)
            for sp_name, label, conc, coeff, rxn_num, comp in row["Products"]:
                species_set.add(sp_name)

        df = pd.DataFrame({
            "species": sorted(species_set),
            "initial cellular concentration recorded": ["" for _ in range(len(species_set))],
        })

        if to_rewrite:
            if not output_path:
                raise ValueError("output_path is required when to_rewrite=True")
            sheet = f"Concentration Request data {system_name}" if system_name else "Concentration Request data"
            try:
                # append/replace sheet if file exists
                with pd.ExcelWriter(output_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
                    df.to_excel(writer, index=False, sheet_name=sheet)
            except FileNotFoundError:
                # create new workbook
                with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name=sheet)

        return df
    def appending_concentration_data(self, concentration_file_path:os.path = None, system_sheet_name: str = None):
      
        df_filled = pd.read_excel(concentration_file_path, sheet_name=f"{system_sheet_name}")
        df_filled.columns = [col.strip().lower() for col in df_filled.columns]
        species_concentration_map = {
            str(row[0]).strip(): row[1]
            for row in df_filled.itertuples(index=False)
            if pd.notna(row[1])
        }

        updated_reaction_data = []
        for _, row in self.reaction_data.iterrows():
            keq = row['Keq']
            updated_reactants = []
            for sp, label, conc, coeff, rxn_num, comp in row['Reactants']:
                if sp in species_concentration_map:
                    conc = float(species_concentration_map[sp])
                updated_reactants.append((sp, label, float(conc), int(coeff), rxn_num, comp))
            updated_products = []
            for sp, label, conc, coeff, rxn_num, comp in row['Products']:
                if sp in species_concentration_map:
                    conc = float(species_concentration_map[sp])
                updated_products.append((sp, label, float(conc), int(coeff), rxn_num, comp))
            updated_reaction_data.append({
                'Keq': float(keq),
                'Reactants': updated_reactants,
                'Products': updated_products,
                'Equilibrium Concentration': row['Equilibrium Concentration']
            })
        self.reaction_data = pd.DataFrame(updated_reaction_data)
        print("[DONE] Cellular concentrations assigned successfully.")

    

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
        self.iteration_history = {}  # e.g., {"A": [c1, c2, ...], "B": [...], ...}
        self.eq_solution_series = []   # list[(iter_idx:int, metric:float)]
        self._last_eq_value = 0.0      # set by compute_deltas_once() each pass
        self._last_eq_by_rxn = {}   # maps <rxn_label> -> float(x) for this iteration

    def get_iteration_history(self):
        """Return per-species concentration sequences recorded during the last solve."""
        return getattr(self, "iteration_history", {})

    def _record_iteration(self, iter_idx: int, conc_map: dict):
        if not hasattr(self, "iteration_history") or not isinstance(self.iteration_history, dict):
            self.iteration_history = {}

        # existing: store concentrations
        for sp, val in conc_map.items():
            try:
                v = float(val)
            except Exception:
                v = float("nan")
            self.iteration_history.setdefault(str(sp), []).append(v)

        # NEW: store each reaction's extent x for this iteration
        rxn_map = getattr(self, "_last_eq_by_rxn", {})
        for rxn_label, xval in rxn_map.items():
            key = f"__eq_x__::{rxn_label}"
            self.iteration_history.setdefault(key, []).append(float(xval))

        # If a reaction didn't fire this iteration, keep series aligned by appending 0
        # (optional but recommended)
        if rxn_map:
            keys_now = set(self.iteration_history.keys())
            # collect all reaction-keys we ever created
            all_rxn_keys = [k for k in keys_now if k.startswith("__eq_x__::")]
            for k in all_rxn_keys:
                if k not in [f"__eq_x__::{r}" for r in rxn_map.keys()]:
                    self.iteration_history.setdefault(k, []).append(0.0)

        # reset buffer for next iteration
        self._last_eq_by_rxn = {}

    def plot_eq_progress(self, save_path: str = None, semilogy: bool = True, title: str = None):
        """
        Plot |x| vs iteration using the series recorded in _record_iteration().
        """
        import matplotlib.pyplot as plt

        key = "__eq_step_max_abs_x__"
        series = self.iteration_history.get(key)
        if not series:
            raise ValueError("No recorded equilibrium steps. Run the solver first.")

        its = list(range(1, len(series) + 1))
        fig = plt.figure(figsize=(7, 4))
        ax = fig.add_subplot(111)
        if semilogy:
            ax.semilogy(its, series, marker='o', linewidth=1.5)
            ax.set_ylabel("max |x| (log scale)")
        else:
            ax.plot(its, series, marker='o', linewidth=1.5)
            ax.set_ylabel("max |x|")
        ax.set_xlabel("Iteration")
        ax.grid(True, which="both", linestyle="--", alpha=0.4)
        ax.set_title(title or "Equilibrium step size vs iteration")
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=160)
        return fig
    def plot_reaction_extents(self, which: str = None, save_path: str = None, semilogy: bool = True):
        """
        Plot per-reaction extent x vs iteration.
        - which: None -> plot all reactions found in iteration_history;
                or pass a substring to filter by reaction label.
        """
        import matplotlib.pyplot as plt

        if not hasattr(self, "iteration_history") or not self.iteration_history:
            raise ValueError("No iteration history recorded.")

        # collect reaction keys
        rxn_series = {k: v for k, v in self.iteration_history.items() if k.startswith("__eq_x__::")}
        if not rxn_series:
            raise ValueError("No per-reaction extents recorded yet.")

        # optional filtering
        if which:
            rxn_series = {k: v for k, v in rxn_series.items() if which in k}
            if not rxn_series:
                raise ValueError(f"No reaction key matches substring: {which}")

        # normalize lengths (pad with last value) so matplotlib aligns lines
        max_len = max(len(v) for v in rxn_series.values())
        for k, v in rxn_series.items():
            if len(v) < max_len:
                rxn_series[k] = v + [v[-1]]*(max_len - len(v))

        its = list(range(1, max_len + 1))
        fig = plt.figure(figsize=(8, 4.8))
        ax = fig.add_subplot(111)

        for k, vals in sorted(rxn_series.items()):
            y = vals
            if semilogy:
                ax.semilogy(its, y, marker='o', linewidth=1.2, label=k.replace("__eq_x__::", ""))
            else:
                ax.plot(its, y, marker='o', linewidth=1.2, label=k.replace("__eq_x__::", ""))

        ax.set_xlabel("Iteration")
        ax.set_ylabel("Reaction extent x" + (" (log scale)" if semilogy else ""))
        ax.set_title("Per-reaction extents vs iteration")
        ax.grid(True, which="both", linestyle="--", alpha=0.4)
        ax.legend(loc="best", fontsize=8)
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=160)
        return fig

    @staticmethod
    def check_convergence_full(data, zero_tol=1e-5, window=20, jitter_tol=1e-5):
        """
        Decide if a nonnegative sequence is converging to 0.

        zero_tol   : absolute threshold for 'close to zero'
        window     : only require monotonic nonincrease over the last `window` points
        jitter_tol : allow tiny increases up to this tolerance
        """
        data = np.asarray(data, dtype=float)
        n = np.arange(1, len(data) + 1)

        # 1) Tail-wise monotonic nonincrease (with tolerance)
        tail = data[-min(window, len(data)):]
        diffs = np.diff(tail)
        is_tail_nonincreasing = np.all(diffs <= jitter_tol)

        # 2) Tends to zero (absolute check)
        tends_to_zero = np.isclose(data[-1], 0.0, rtol=0.0, atol=zero_tol)

        # 3) Ratio test on valid pairs only (avoid div-by-zero, negatives)
        valid = (data[:-1] > 0) & np.isfinite(data[:-1]) & np.isfinite(data[1:])
        if np.any(valid):
            ratios = data[1:][valid] / data[:-1][valid]
            avg_ratio = float(np.nanmean(ratios)) if ratios.size else np.inf
        else:
            avg_ratio = np.inf

        # 4) log–log slope (mask zeros)
        positive_mask = data > 0
        if np.count_nonzero(positive_mask) >= 2:
            slope, intercept, r_value, p_value, std_err = linregress(
                np.log(n[positive_mask]), np.log(data[positive_mask])
            )
            p_estimate = -slope
        else:
            p_estimate = np.nan

        # Verdict
        if tends_to_zero and is_tail_nonincreasing:
            verdict = "Convergent to 0 (tail monotone & below tol)"
        elif tends_to_zero and (avg_ratio < 1 or (np.isfinite(p_estimate) and p_estimate > 1)):
            verdict = "Likely convergent to 0 (tests support)"
        else:
            verdict = "Divergent or inconclusive"

        return {
            "is_decreasing": bool(is_tail_nonincreasing),
            "tends_to_zero": bool(tends_to_zero),
            "average_ratio": avg_ratio,
            "p_estimate": p_estimate,
            "verdict": verdict,
        }
   
    def sum_species_concentration(self):
        """
        Sum all concentrations in a species list.
        Each item in species_list should be (species, concentration, label, coefficient).
        """
        reactant_sum = 0
        for row in self.reaction_data.itertuples():
            reactant_sum += sum(iter[2] for iter in row.Reactants)
        product_sum = 0
        for row in self.reaction_data.itertuples():
            product_sum += sum(iter[2] for iter in row.Products)
        return reactant_sum + product_sum

    def calculate_equilibrium(self, system_compartment,global_concentration:dict = None):
        if global_concentration is None:
            raise ValueError("global concentration is not defined")

        # --- NEW: fresh history for this run ---
        self.iteration_history = {}  # e.g., {"A": [c1, c2, ...], "B": [...], ...}
        if global_concentration == None:
            raise ValueError("global concentration is not defined")
        
        def limiting_compartment_determinator(self,species_row,system_compartment:str = None):
            list_of_compartment_ratio = [self.known_compartments[comp][1] for specimen, label, conc, coeff, rxn_num, comp in species_row]
            print(list_of_compartment_ratio)
            minimum_ratio = min(list_of_compartment_ratio)
            print(minimum_ratio)
            smallest_compartment = [val for val in self.known_compartments if self.known_compartments[val][1] == minimum_ratio]
            return smallest_compartment
        def updating_species_concentration(self, species_row,delta_x, species_type:int = 1,system_compartment:str = None,limiting_compartment:str=None,global_concentration:dict = None):
            updated_species_list = []
            for specimen, label, conc, coeff, rxn_num, comp in species_row:
                global_concentration[specimen] -= delta_x*species_type*coeff*(self.known_compartments[limiting_compartment][1]/
                                                                              self.known_compartments[system_compartment][1])*self.known_compartments[comp][1]
                updated_species_list.append((specimen,label,global_concentration[specimen],coeff,rxn_num,comp))
            return updated_species_list
            
        def updating_overlapping_species(overlapping_list, index, data_to_update, column_name):
    
            for i in range (len(self.reaction_data.at[index,column_name])):
                next_item = (self.reaction_data.at[index,column_name][i][0], self.reaction_data.at[index,column_name][i][1], self.reaction_data.at[index,column_name][i][4])
                for j in range(len(overlapping_list)):
                    if next_item in overlapping_list[j]:
                        # Remove by value, not by index
                        buffer_conc = self.reaction_data.at[index,column_name][i][2]
                        if next_item in overlapping_list[i]:
                            overlapping_list[i].remove(next_item)
                            buffer_conc = sum(data_iter[2] for data_iter in data_to_update if data_iter[0] == self.reaction_data.at[index,column_name][i][0])
                            self.reaction_data.at[index,column_name][i] = (self.reaction_data.at[index,column_name][i][0], self.reaction_data.at[index,column_name][i][1], buffer_conc, self.reaction_data.at[index,column_name][i][3], self.reaction_data.at[index,column_name][i][4],self.reaction_data.at[index,column_name][i][5])
            return overlapping_list
        equilibrium_solution_array = []
        # Step 1: Build global concentration dictionary
        species_counter = Counter()
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

        index = 0
        while index <= 500:
            index+=1
            equilibrium_solutions_buffer_array = []
            buffer_overlapping_list = copy.deepcopy(over_lapping_big_list)
            for row in self.reaction_data.itertuples():
                current_index = row.Index
                x = sp.symbols("x")
                terms_reactant = []
                for spc in row.Reactants:
                    conc = sp.sympify(spc[2])                 # ensure sympy number
                    coeff = int(float(spc[3])) if spc[3] not in (None, "") else 1
                    exp = min(coeff, 10)                      # cap exponent at 10
                    terms_reactant.append((conc - coeff*x)**exp)
                reactant_expr = sp.prod(terms_reactant) if terms_reactant else sp.Integer(1)
                terms_product = []
                for spc in row.Products:
                    conc = sp.sympify(spc[2])                 # ensure sympy number
                    coeff = int(float(spc[3])) if spc[3] not in (None, "") else 1
                    exp = min(coeff, 10)                      # cap exponent at 10
                    terms_product.append((conc + coeff*x)**exp)
                product_expr = sp.prod(terms_product) if terms_product else sp.Integer(1)

                print(reactant_expr, product_expr)
                poly_expr = sp.expand(row.Keq * reactant_expr - product_expr)
                coeffs = sp.Poly(poly_expr, x).all_coeffs()
                coeffs_numeric = [float(coef.evalf()) for coef in coeffs]
                roots = np.roots(coeffs_numeric)
                valid_solutions = []
                for sol in roots:
                    if np.isreal(sol):
                        sol_real = np.real(sol)
                       
                        if (all((val[2] - sol_real * val[3]) >= 0 for val in row.Reactants)) and (all((val[2] + sol_real * val[3]) >= 0 for val in row.Products)):
                            valid_solutions.append(sol_real)
                equilibrium_solutions_buffer_array.extend(valid_solutions)
                delta = valid_solutions[0] if valid_solutions else 0
                limiting_compartment_of_reaction = limiting_compartment_determinator(self=self, species_row= row.Reactants + row.Products, system_compartment = system_compartment)[0]

                # print(limiting_compartment_of_reaction)
                updated_reactants =  updating_species_concentration(self = self,species_row=row.Reactants,delta_x = delta,species_type = 1,system_compartment=system_compartment,limiting_compartment=limiting_compartment_of_reaction,global_concentration=global_concentration)
                updated_products = updating_species_concentration(self = self, species_row = row.Products,delta_x= delta,species_type=-1, system_compartment=system_compartment,limiting_compartment=limiting_compartment_of_reaction,global_concentration=global_concentration)
                complete_update_list = updated_reactants + updated_products
                self.reaction_data.at[row.Index, 'Reactants'] = updated_reactants
                self.reaction_data.at[row.Index, 'Products'] = updated_products

                next_index = current_index + 1
                if next_index in self.reaction_data.index:
                    buffer_overlapping_list = updating_overlapping_species(
                        overlapping_list=buffer_overlapping_list,
                        index=next_index,
                        data_to_update=complete_update_list,
                        column_name="Reactants"
                    )
                    buffer_overlapping_list = updating_overlapping_species(
                        overlapping_list=buffer_overlapping_list,
                        index=next_index,
                        data_to_update=complete_update_list,
                        column_name="Products"
                    )
                else:
                    buffer_overlapping_list = updating_overlapping_species(
                        overlapping_list=buffer_overlapping_list,
                        index=0,
                        data_to_update=complete_update_list,
                        column_name="Reactants"
                    )
                    buffer_overlapping_list = updating_overlapping_species(
                        overlapping_list=buffer_overlapping_list,
                        index=0,
                        data_to_update=complete_update_list,
                        column_name="Products"
                    )
        
            print(f"equilibrium_solutions_buffer_array: {equilibrium_solutions_buffer_array}")
            equilibrium_solution_array.extend(equilibrium_solutions_buffer_array)
            snapshot = {}
            for species_name, val in global_concentration.items():
                snapshot[str(species_name)] = val
            self._record_iteration(index, snapshot)  # no need for +1 since you already ++ at top

            # k should be your 1-based iteration index; if you have 0-based, do k+1
            self._record_iteration(index, snapshot)
            if np.count_nonzero(equilibrium_solutions_buffer_array)!=0:
                result = self.check_convergence_full(equilibrium_solution_array)
                print(result)
                if result["is_decreasing"] and result["tends_to_zero"]:
                    print("equilibrium is reached")
                    break
                index += 1
                continue
            else:
                print("equilibrium is reached")
                break
        
        print(f"number of iteration: {index}")
        print(equilibrium_solution_array[0], equilibrium_solution_array[1])
        print(self.sum_species_concentration())
        self.export_species_template(output_file="species_concentration_output.xlsx")
    # --- NEW in helpertesting.py -- inside class SpeciesMatrix -------------------
    def compute_deltas_once(self, system_compartment: str, global_concentration: dict):
        """
        Do ONE pass over all reactions for this system using the *current*
        global concentrations, but DO NOT mutate global_concentration here.
        Return (delta_map, eq_solutions).

        Behavior:
        - If ANY coefficient in a reaction row > 10 -> solve x in LOG domain (robust).
        - Else -> keep the existing polynomial approach (capped exponent at 10).
        - Validate nonnegativity before applying; raise informative errors if invalid.
        """
        import numpy as np
        import sympy as sp
        import math

        delta_map = {}
        eq_solutions = []
        x_sym = sp.symbols("x")

        # --- helpers ------------------------------------------------------------
        def _rxn_label(row):
            # Prefer a human string if you store it; else fall back to index
            lbl = getattr(row, "Equation", None)
            if not lbl:
                try:
                    lbl = f"rxn_{row.Index}"
                except Exception:
                    lbl = f"rxn_{len(getattr(self, '_last_eq_by_rxn', {}))}"
            # keep labels short for plotting legends
            return (str(lbl)[:120]).strip()
        def _current_c(spec_name: str) -> float:
            try:
                return float(global_concentration.get(spec_name, 0.0))
            except Exception:
                return 0.0

        def _limiting_compartment(species_rows):
            # species_rows is list of tuples: (species, label, conc, coeff, rxn_num, comp)
            ratios = [self.known_compartments[comp][1] for *_, comp in species_rows]
            min_ratio = min(ratios)
            # choose first matching name if tie
            for name, (_, r) in self.known_compartments.items():
                if r == min_ratio:
                    return name
            return system_compartment
        
        def _accumulate_delta(delta_val: float, reactants_now, products_now, limiting_comp: str):
            """Apply scaled +/- deltas into delta_map (no mutation of global here)."""
            lim_ratio = self.known_compartments[limiting_comp][1]
            sys_ratio = self.known_compartments[system_compartment][1]

            def add_side(side, species_type):
                for (specimen, _, _, coeff, _, comp) in side:
                    try:
                        coeff_int = int(float(coeff)) if coeff not in (None, "") else 1
                    except Exception:
                        coeff_int = 1
                    comp_ratio = self.known_compartments[comp][1]
                    d = - delta_val * species_type * coeff_int * (lim_ratio / sys_ratio) * comp_ratio
                    delta_map[specimen] = delta_map.get(specimen, 0.0) + d

            add_side(reactants_now, species_type=+1)
            add_side(products_now,  species_type=-1)

        # --- LOG-domain solver for a single reaction row ------------------------
        def _solve_x_log(row):
            """
            Solve:
                sum_prod ν log(S0 + ν x) - sum_reac ν log(S0 - ν x) = log(Keq)
            Return x (float). If domain/bracketing/convergence is problematic, return 0.0 (no move).
            """
            import math

            Keq = float(row.Keq)
            if not (Keq > 0.0 and math.isfinite(Keq)):
                return 0.0
            logKeq = math.log(Keq)

            # Build [(nu, S0, name)] from CURRENT global concentrations
            reactants_now = [(int(float(coeff)) if coeff not in (None, "") else 1,
                            _current_c(sp_name), sp_name)
                            for (sp_name, _, _, coeff, _, _) in row.Reactants]
            products_now  = [(int(float(coeff)) if coeff not in (None, "") else 1,
                            _current_c(sp_name), sp_name)
                            for (sp_name, _, _, coeff, _, _) in row.Products]

            # Full domain (allow reverse extent too):
            #   x <  min_i S0_reac/nu_reac   and   x > max_j ( - S0_prod/nu_prod )
            try:
                x_hi = min((S0/nu for (nu, S0, _) in reactants_now), default=float("inf"))
            except ZeroDivisionError:
                x_hi = float("inf")
            try:
                x_lo = max((-(S0/nu) for (nu, S0, _) in products_now), default=-float("inf"))
            except ZeroDivisionError:
                x_lo = -float("inf")

            # If infeasible or degenerate interval → no move
            if not (math.isfinite(x_lo) and math.isfinite(x_hi) and x_lo < x_hi):
                return 0.0

            def f(x: float) -> float:
                s = 0.0
                # products: + ν log(S0 + ν x)
                for (nu, S0, _) in products_now:
                    val = S0 + nu*x
                    if val <= 0:  # outside domain (numerical guard)
                        return float("inf")
                    s += nu * math.log(val)
                # reactants: - ν log(S0 - ν x)
                for (nu, S0, _) in reactants_now:
                    val = S0 - nu*x
                    if val <= 0:
                        return -float("inf")
                    s -= nu * math.log(val)
                return s - logKeq

            def fp(x: float) -> float:
                s = 0.0
                for (nu, S0, _) in products_now:
                    s += (nu*nu) / (S0 + nu*x)
                for (nu, S0, _) in reactants_now:
                    s += (nu*nu) / (S0 - nu*x)
                return s

            # Bracket strictly inside (x_lo, x_hi)
            eps = 1e-12
            a = x_lo + eps*(1 + (abs(x_hi) + abs(x_lo)))
            b = x_hi - eps*(1 + (abs(x_hi) + abs(x_lo)))
            if not (a < b):
                return 0.0

            fa, fb = f(a), f(b)

            # Need fa < 0 < fb (f is strictly increasing)
            if not (fa < 0 < fb):
                f0 = f(0.0)
                if not math.isfinite(f0) or f0 == 0.0:
                    return 0.0
                # try tightening; if still no bracket, no move
                ok = False
                for shrink in (1e-6, 1e-5, 1e-4, 1e-3):
                    aa = a + shrink*(b - a)
                    bb = b - shrink*(b - a)
                    faa, fbb = f(aa), f(bb)
                    if faa < 0 < fbb:
                        a, b, fa, fb = aa, bb, faa, fbb
                        ok = True
                        break
                if not ok:
                    return 0.0

            # Hybrid Newton–Bisection
            rtol, atol, max_iter = 1e-12, 1e-14, 100
            x = 0.5*(a + b)
            for _ in range(max_iter):
                fx = f(x)
                if abs(fx) <= atol or abs(b - a) <= rtol*(1 + abs(x)):
                    return x
                dfx = fp(x)
                xn = x - fx/dfx
                x_new = xn if (a < xn < b and math.isfinite(xn)) else 0.5*(a + b)
                fx_new = f(x_new)
                if fx_new < 0:
                    a = x_new
                else:
                    b = x_new
                x = x_new

            # no convergence → no move
            return 0.0


        # --- main loop over reactions -------------------------------------------
        for row in self.reaction_data.itertuples():
            # snapshot tuples with *current global* concs
            def with_current(t):
                sp_name, label, conc, coeff, rxn_num, comp = t
                return (sp_name, label, _current_c(sp_name), coeff, rxn_num, comp)

            reactants_now = [with_current(t) for t in row.Reactants]
            products_now  = [with_current(t) for t in row.Products]
            coeffs_this_row = []
            for (_, _, _, coeff, _, _) in reactants_now + products_now:
                try:
                    coeffs_this_row.append(int(float(coeff)) if coeff not in (None, "") else 1)
                except Exception:
                    coeffs_this_row.append(1)

            use_log = any(c > 10 for c in coeffs_this_row)

            if use_log:
                # --- LOG METHOD ---
                try:
                    s = float(_solve_x_log(row))
                except Exception as e:
                    # Include coefficients in the error message
                    desc = ", ".join(
                        [f"{sp}:{int(float(coeff)) if coeff not in (None,'') else 1}"
                        for (sp, _, _, coeff, _, _) in reactants_now + products_now]
                    )
                    raise ValueError(
                        f"Log-equilibrium solve failed for a reaction (Keq={row.Keq}). "
                        f"Coefficients: {desc}. Reason: {e}"
                    )

                # Validate nonnegativity with candidate s
                ok_reac = all((_current_c(sp) - s * (int(float(coeff)) if coeff not in (None, "") else 1)) >= 0
                            for (sp, _, _, coeff, _, _) in reactants_now)
                ok_prod = all((_current_c(sp) + s * (int(float(coeff)) if coeff not in (None, "") else 1)) >= 0
                            for (sp, _, _, coeff, _, _) in products_now)
                if not (ok_reac and ok_prod):
                    desc = ", ".join(
                        [f"{sp}:{int(float(coeff)) if coeff not in (None,'') else 1}"
                        for (sp, _, _, coeff, _, _) in reactants_now + products_now]
                    )
                    raise ValueError(
                        "Found a log-domain solution for x, but it would make a concentration negative. "
                        f"Coefficients: {desc}. x={s}"
                    )

                eq_solutions.append(s)
                limiting_comp = _limiting_compartment(reactants_now + products_now)
                label = _rxn_label(row)
                self._last_eq_by_rxn[label] = float(s)
                _accumulate_delta(s, reactants_now, products_now, limiting_comp)

            else:
                # --- EXISTING POLYNOMIAL PATH (capped exponent at 10, as before) ---
                def side_poly(side, sign):
                    terms = []
                    for (_, _, c, coeff, _, _) in side:
                        try:
                            coeff_int = int(float(coeff)) if coeff not in (None, "") else 1
                        except Exception:
                            coeff_int = 1
                        coeff_int = min(coeff_int, 10)
                        terms.append((c + sign * coeff_int * x_sym) ** coeff_int)
                    return sp.prod(terms) if terms else sp.Integer(1)

                reactant_expr = side_poly(reactants_now, sign=-1)
                product_expr  = side_poly(products_now,  sign=+1)

                poly_expr   = sp.expand(row.Keq * reactant_expr - product_expr)
                coeffs      = sp.Poly(poly_expr, x_sym).all_coeffs()
                coeffs_num  = [float(sp.N(co)) for co in coeffs]
                roots       = np.roots(coeffs_num)

                valid_solutions = []
                for sol in roots:
                    if np.isreal(sol):
                        s = float(np.real(sol))
                        ok_reac = all((c - s * (int(float(coeff)) if coeff not in (None, "") else 1)) >= 0
                                    for (_, _, c, coeff, _, _) in reactants_now)
                        ok_prod = all((c + s * (int(float(coeff)) if coeff not in (None, "") else 1)) >= 0
                                    for (_, _, c, coeff, _, _) in products_now)
                        if ok_reac and ok_prod:
                            valid_solutions.append(s)

                s = valid_solutions[0] if valid_solutions else 0.0
                if s != 0.0:
                    eq_solutions.extend(valid_solutions)
                label = _rxn_label(row)
                self._last_eq_by_rxn[label] = float(s)
                limiting_comp = _limiting_compartment(reactants_now + products_now)
                _accumulate_delta(s, reactants_now, products_now, limiting_comp)
        # record a single scalar to summarize “how big” the solution(s) were this pass
        self._last_eq_value = max((abs(s) for s in eq_solutions), default=0.0)
        return delta_map, eq_solutions



    def sync_from_global(self, global_concentration: dict):
        """
        Overwrite every tuple's 'conc' field in reaction_data with
        global_concentration[species]. This keeps local tables in sync after a global update.
        """
        for idx, row in self.reaction_data.iterrows():
            new_reactants = []
            for (sp_name, label, _, coeff, rxn_num, comp) in row["Reactants"]:
                c = float(global_concentration.get(sp_name, 0.0))
                new_reactants.append((sp_name, label, c, coeff, rxn_num, comp))
            new_products = []
            for (sp_name, label, _, coeff, rxn_num, comp) in row["Products"]:
                c = float(global_concentration.get(sp_name, 0.0))
                new_products.append((sp_name, label, c, coeff, rxn_num, comp))
            self.reaction_data.at[idx, "Reactants"] = new_reactants
            self.reaction_data.at[idx, "Products"]  = new_products

