import helpertesting as hd
import os
class CompartmentSystem:
    def __init__(self, docx_path):
        self.docx_path = docx_path
        self.systems = {}  # key = system name, value = hd.SpeciesMatrix instance
        self._parse_document()
        self.cytosolic_concentration = {}
    def _parse_document(self):
        doc = hd.docx.Document(self.docx_path)
        print(f"[INFO] Parsing document (tables): {self.docx_path}")
        for table in doc.tables:
            headers = [cell.text.strip() for cell in table.rows[0].cells]
            if headers[:3] != ["System", "Compartment", "Reactions"]:
                continue  # Skip irrelevant tables
            for iter in table.rows[1:]:
                if not iter.cells:
                    continue
                cells = [cell.text.strip() for cell in iter.cells]
                # print(f"[INFO] Processing row: {cells}")
                if len(cells) < 3:
                    continue  # Not a valid row

                system_val = cells[0]
                compartment_val = cells[1].strip()
                reactions_list = [individual_reaction for individual_reaction in cells[2].split("\n") if individual_reaction.strip()]
                print(f"[INFO] Processing system: {system_val}")
                print(f"[INFO] Processing compartment: {compartment_val}")
                print(f"[INFO] Processing reactions: {reactions_list}")
                self._add_system(system_val, compartment_val, reactions_list)
    
    def _add_system(self, system_name, compartment, equations):
        print(f"[INFO] Parsing {system_name} in {compartment}")
        instance = hd.SpeciesMatrix(equations_list_input=equations)
        instance._initialize_species_from_reaction()
        self.systems[system_name] = {
            "compartment": compartment,
            "speciesMatrix": instance
        }
    def get_all_systems(self):
        return self.systems
    def snapshot_global_concentrations(self) -> dict[str, float]:
        """
        Return a dict of unique species -> global concentration at t=0.

        Rule:
          - If a species has any assigned concentration in any Reactants tuple,
            use the first non-zero value found.
          - Otherwise, initialize it at 0.0 (even if it appears only as a Product).
        """
        global_map: dict[str, float] = {}
        seen_anywhere: set[str] = set()

        for sys_name, info in self.systems.items():
            sm = info["speciesMatrix"]
            df = sm.reaction_data  # columns include "Reactants", "Products"
            for _, row in df.iterrows():
                # Track all species encountered (Reactants + Products)
                for bucket in ("Reactants", "Products"):
                    for species, label, conc, coeff, rxn_num, comp in row[bucket]:
                        seen_anywhere.add(species)

                # Prefer initial concentrations from Reactants (your allocation step)
                for species, label, conc, coeff, rxn_num, comp in row["Reactants"]:
                    try:
                        val = float(conc)
                    except (TypeError, ValueError):
                        val = 0.0
                    if species not in global_map and val != 0.0:
                        global_map[species] = val

        # Any species not yet given a value starts at 0.0
        for sp in seen_anywhere:
            global_map.setdefault(sp, 0.0)

        return global_map
    def validate_local_participation(self):
        """
        Ensure every reaction in each system contains at least one species
        whose compartment matches that system's representative compartment.

        Returns
        -------
        dict
            {
              <system_name>: {
                "compartment": <str>,
                "valid":   [reaction_idx, ...],
                "invalid": [{"index": reaction_idx, "equation": <str>} , ...]
              },
              ...
            }
        """
        report = {}

        for sys_name, info in self.systems.items():
            sys_comp = info["compartment"]           # e.g. "C", "M", "N", ...
            sm = info["speciesMatrix"]               # hd.SpeciesMatrix
            df = sm.reaction_data

            valid_idxs = []
            invalid_entries = []

            # Assume reaction row order aligns with sm.equations order
            for rxn_idx, row in enumerate(df.itertuples(index=False)):
                # Each side is a list of tuples: (species, label, conc, coeff, rxn_num, comp)
                reactants = getattr(row, "Reactants", [])
                products  = getattr(row, "Products",  [])

                # Does ANY participant belong to this system's compartment?
                has_local = any(t[-1] == sys_comp for t in reactants) or \
                            any(t[-1] == sys_comp for t in products)

                if has_local:
                    valid_idxs.append(rxn_idx+1)
                else:
                    eqn_str = None
                    try:
                        eqn_str = sm.equations[rxn_idx]
                    except Exception:
                        eqn_str = "<equation string unavailable>"
                    invalid_entries.append({"index": rxn_idx+1, "equation": eqn_str})

            report[sys_name] = {
                "compartment": sys_comp,
                "valid": valid_idxs,
                "invalid": invalid_entries,
            }

        return report

    def assert_local_participation(self):
        """
        Same check as validate_local_participation(), but raises a ValueError
        if any invalid reactions are found. Useful for quick gating.
        """
        rpt = self.validate_local_participation()
        problems = []
        for sys_name, block in rpt.items():
            for inv in block["invalid"]:
                problems.append(
                    f"[{sys_name} | {block['compartment']}] "
                    f"reaction #{inv['index']} has no species in this compartment. "
                    f"Eq: {inv['equation']}"
                )
        if problems:
            raise ValueError(
                "Invalid reactions found (no local species present):\n"
                + "\n".join(problems)
            )
        return True
    # --- NEW in system_reaction_parser.py -- inside class CompartmentSystem ------
    def solve_all_systems_iterative(self, max_iters: int = 500, zero_tol: float = 1e-5, window: int = 20):
        """
        Advance ALL systems in lockstep:
        - each iter: gather per-system deltas (no global mutation),
            sum them, apply once to the global pool, sync all systems,
            record history, and test convergence from combined solutions.
        Returns the final global concentration dict.
        """
        from collections import defaultdict
        global_conc = self.snapshot_global_concentrations()
        # clear previous histories
        for _, info in self.systems.items():
            sm = info["speciesMatrix"]
            if hasattr(sm, "iteration_history"):
                sm.iteration_history = {}

        all_eq_solutions = []

        for k in range(1, max_iters + 1):
            total_delta = defaultdict(float)
            eq_batch = []

            # 1) get proposed deltas from each system (read-only global)
            for sys_name, info in self.systems.items():
                sm   = info["speciesMatrix"]
                comp = info["compartment"]
                dmap, eqs = sm.compute_deltas_once(comp, global_conc)
                eq_batch.extend(eqs)
                for sp, d in dmap.items():
                    total_delta[sp] += d

            # 2) apply combined deltas to global (no negatives)
            for sp, d in total_delta.items():
                global_conc[sp] = max(0.0, float(global_conc.get(sp, 0.0)) + float(d))

            # 3) sync every system’s local tables with new global
            for _, info in self.systems.items():
                sm = info["speciesMatrix"]
                sm.sync_from_global(global_conc)

            # 4) record the iteration snapshot for plotting
            for _, info in self.systems.items():
                sm = info["speciesMatrix"]
                if hasattr(sm, "_record_iteration"):
                    sm._record_iteration(k, global_conc)

            # 5) convergence check (reuse your helper on the aggregate sequence)
            all_eq_solutions.extend(eq_batch)
            if len(all_eq_solutions) >= max(window, 3):
                # call any SpeciesMatrix's static method
                any_sm = next(iter(self.systems.values()))["speciesMatrix"]
                verdict = any_sm.check_convergence_full(all_eq_solutions, zero_tol=zero_tol, window=window)
                if verdict.get("is_decreasing") and verdict.get("tends_to_zero"):
                    break

        return global_conc
