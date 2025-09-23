import pandas as pd
import docx
import re
from typing import List, Tuple, Set, Dict, Optional
from collections import Counter
from docx import Document
# ============= Helpers =============



class Species_class:
    # ------------- init -------------
    def __init__(self, docx_path: str = None, equations_list_input: Optional[List[str]] = None):
        self.docx_path = docx_path

        # core containers
        self.equations: List[str] = []  # normalized "X_tot = ..." strings
        self.reaction_concentration_list: List[float] = []  # 3rd-column values, aligned 1:1 with equations
        self.reaction_concentration: Dict[int, float] = {}  # {reaction_index: concentration}

        # many-side reactions (per-reaction), now 4-tuples: (species, unit_fraction, coeff_fraction, label)
        self.reaction_information_list: List[List[Tuple[str, float, float, str]]] = []

        # aggregated global sets (summing effective coefficients across reactions)
        self.reactants: Set[Tuple[str, float, str]] = set()
        self.products:  Set[Tuple[str, float, str]] = set()

        # repeats bookkeeping
        self.dictionary_of_repeating_species: Dict[str, List[int]] = {}     # {"PL3D":[5,18], ...}
        self.repeating_sepcies_dictionary: Dict[str, List[Tuple[float, int]]] = {}  # {"PL3D":[(0.45,5),(0.10,18)], ...}
        self.reactions_without_repeats_indices: List[int] = []
        self.reactions_without_repeats: List[List[Tuple[str, float, float, str]]] = []

        # per-reaction fraction maps (built from "Desired fractions" table)
        self.per_reaction_fractions: List[Dict[str, float]] = []

        # handy zero map for concentrations
        self.global_concentration: Dict[str, float] = {}

        # load inputs
        if docx_path is not None:
            # equations (2nd col) + concentrations (3rd col), both aligned 1:1
            self.equations, self.reaction_concentration_list = self._read_equations_and_concentrations_from_table()
            # build per-reaction fraction dicts aligned to self.equations
            self.per_reaction_fractions = self._build_per_reaction_fractions()
        elif equations_list_input is not None:
            # fallback path: list only; no concentrations, no per-reaction fractions
            self.equations = [self.clean_equation(x) for x in equations_list_input if x and x.strip()]
            self.equations = [eq for eq in self.equations if self._is_total_equation(eq)]
            self.reaction_concentration_list = [0.0 for _ in self.equations]
            self.per_reaction_fractions = [{} for _ in self.equations]
        else:
            raise ValueError("Either docx_path or equations_list_input must be provided.")

    # ------------- public API helpers -------------
    @property
    def species(self) -> Set[str]:
        return set([r[0] for r in self.reactants]).union([p[0] for p in self.products])

    def get_reaction_concentrations(self) -> List[float]:
        return self.reaction_concentration_list

    # ---------- NEW: parser that keeps coeffs on terms ----------
    def _parse_tokens_with_coeff(self, equation: str):
        """
        Parse equation sides keeping an explicit numeric coefficient on each term.
        Returns (reactants, products) where each item is (species, coeff_fraction, label).
        Examples:
          '2*T2F2T2' -> ('T2F2T2', 2.0, label)
          '0.5*XF2B' -> ('XF2B', 0.5, label)
          'Y'        -> ('Y', 1.0, label)
        """
        eq = self.clean_equation(equation or "")
        if "=" not in eq:
            return [], []
        left, right = [s.strip() for s in eq.split("=", 1)]
        if not left or not right:
            return [], []

        FLOAT = r"(?:\d+(?:\.\d+)?|\.\d+)"
        # Accept "a*b", "a b", or just "b" (handles occasional missing '*')
        pat = re.compile(
            rf"^\s*(?:({FLOAT})\s*\*?\s*)?([A-Za-z][A-Za-z0-9_]*)\s*$"
        )

        def parse_side(side: str, label: str):
            out = []
            for term in side.split("+"):
                s = term.strip()
                m = pat.match(s)
                if not m:
                    continue
                mult = float(m.group(1)) if m.group(1) else 1.0
                sp   = m.group(2)
                out.append((sp, float(mult), label))  # (species, coeff_fraction, label)
            return out

        return parse_side(left, "Reactant"), parse_side(right, "Product")

    def apply_average_and_redistribute_on_repeats(self) -> Dict[str, float]:
        """
        Only modify reactions that contain repeating species:
        - For each repeating species, compute its average *effective* coefficient (unit_fraction*coeff_fraction)
          across ALL reactions it appears in.
        - In each reaction that contains any repeating species, overwrite those species' *effective* coeffs with the average.
        - Redistribute the leftover effective share (1 - sum(avg_eff of repeating species present in that reaction))
          equally among the NON-repeating species in that reaction (by adjusting unit_fraction only; coeff_fraction is fixed).
        - Rebuild aggregates and repeat maps.

        Returns:
            avg_map: {species: averaged_effective_coefficient} for repeating species.
        """
        # --- build per-reaction EFFECTIVE coeff sums by exact token ---
        occurrences: Dict[str, Dict[int, float]] = {}  # species -> {rxn_idx -> eff_sum_in_that_rxn}
        for idx, rxn in enumerate(self.reaction_information_list):
            per_rxn: Dict[str, float] = {}
            for sp, uf, cf, _lbl in rxn:
                token = sp.strip()
                eff = float(uf) * float(cf)
                per_rxn[token] = per_rxn.get(token, 0.0) + eff
            for token, eff_sum in per_rxn.items():
                occurrences.setdefault(token, {})[idx] = eff_sum

        # repeating species → average EFFECTIVE coefficient across reactions
        avg_map: Dict[str, float] = {
            token: (sum(idxs.values()) / float(len(idxs)))
            for token, idxs in occurrences.items() if len(idxs) > 1
        }
        if not avg_map:
            return {}

        # guard: ensure we have the index list of reactions that contain repeats
        if not hasattr(self, "reactions_with_repeats_indices"):
            # derive it if missing
            repeating_rxn_indices: Set[int] = set()
            for idxs in (self.dictionary_of_repeating_species or {}).values():
                repeating_rxn_indices.update(idxs)
            self.reactions_with_repeats_indices = sorted(repeating_rxn_indices)

        # --- apply only to reactions that contain repeats ---
        for idx in self.reactions_with_repeats_indices:
            rxn = self.reaction_information_list[idx]

            # collapse duplicates in this reaction while preserving order
            order: List[str] = []
            labels: Dict[str, str] = {}
            per_rxn_eff_sum: Dict[str, float] = {}
            coeff_fraction_fixed: Dict[str, float] = {}

            for sp, uf, cf, lbl in rxn:
                token = sp.strip()
                if token not in per_rxn_eff_sum:
                    order.append(token)
                    labels[token] = lbl
                    per_rxn_eff_sum[token] = 0.0
                    coeff_fraction_fixed[token] = float(cf)
                per_rxn_eff_sum[token] += float(uf) * float(cf)

            reps_here   = [t for t in order if t in avg_map]
            nonreps_here = [t for t in order if t not in avg_map]

            # sum of averaged EFFECTIVE coeffs for repeating species present in THIS reaction
            S = sum(avg_map[t] for t in reps_here)
            K = len(nonreps_here)

            # compute fair share for non-repeats in EFFECTIVE space
            if K > 0:
                leftover = 1.0 - S
                if leftover < 0.0:
                    leftover = 0.0  # clamp if rounding/noisy data pushes S > 1
                each_eff = leftover / K
                scale = 1.0  # not used
            else:
                # no non-repeats: normalize repeats to sum 1.0 (effective space)
                scale = (1.0 / S) if S > 0.0 else 1.0
                each_eff = None

            # rebuild reaction row with NEW unit_fraction such that: unit_fraction * coeff_fraction = target_effective
            new_rxn: List[Tuple[str, float, float, str]] = []
            for t in order:
                lbl = labels[t]
                cf_fixed = float(coeff_fraction_fixed[t])
                if t in reps_here:
                    target_eff = (avg_map[t] if K > 0 else avg_map[t] * scale)
                else:
                    target_eff = each_eff
                uf_new = (target_eff / cf_fixed) if (cf_fixed > 0 and target_eff is not None) else 0.0
                new_rxn.append((t, float(uf_new), cf_fixed, lbl))

            self.reaction_information_list[idx] = new_rxn

        # --- re-aggregate globals (sum EFFECTIVE across reactions) ---
        sum_coeffs: Dict[str, float] = {}
        label_map: Dict[str, str] = {}
        for rxn in self.reaction_information_list:
            per_rxn: Dict[str, float] = {}
            per_lbl: Dict[str, str] = {}
            for sp, uf, cf, lbl in rxn:
                token = sp.strip()
                eff = float(uf) * float(cf)
                per_rxn[token] = per_rxn.get(token, 0.0) + eff
                if token not in per_lbl:
                    per_lbl[token] = lbl
            for token, s in per_rxn.items():
                sum_coeffs[token] = sum_coeffs.get(token, 0.0) + s
                if token not in label_map:
                    label_map[token] = per_lbl[token]

        self.reactants.clear()
        self.products.clear()
        for token, total_eff in sum_coeffs.items():
            lbl = label_map.get(token, "Product")
            tup = (token, float(total_eff), lbl)
            (self.reactants if lbl == "Reactant" else self.products).add(tup)

        self.global_concentration = {sp: 0.0 for sp in sum_coeffs.keys()}

        # --- recompute repeat dictionaries (indices & (eff, idx) lists) ---
        self.dictionary_of_repeating_species = {}
        self.repeating_sepcies_dictionary = {}
        occ_updated: Dict[str, Dict[int, float]] = {}

        for idx, rxn in enumerate(self.reaction_information_list):
            per_rxn: Dict[str, float] = {}
            for sp, uf, cf, _ in rxn:
                token = sp.strip()
                eff = float(uf) * float(cf)
                per_rxn[token] = per_rxn.get(token, 0.0) + eff
            for token, eff_sum in per_rxn.items():
                occ_updated.setdefault(token, {})[idx] = eff_sum

        for token, idx_map in occ_updated.items():
            if len(idx_map) > 1:
                self.dictionary_of_repeating_species[token] = sorted(idx_map.keys())
                self.repeating_sepcies_dictionary[token] = [(float(idx_map[i]), i) for i in sorted(idx_map.keys())]

        return avg_map

    # ------------- cleaning / parsing -------------
    @staticmethod
    def clean_equation(equation: str) -> str:
        # Always return string
        s = "" if equation is None else str(equation)

        # normalize arrows to '='
        for a in ["⇌", "<=>", "<->", "->", "→"]:
            s = s.replace(a, "=")

        # '(X)tot' -> 'X_tot'
        s = re.sub(r"\(\s*([A-Za-z0-9_]+)\s*\)\s*tot\b", r"\1_tot", s, flags=re.IGNORECASE)

        # remove '+' next to '='
        s = re.sub(r'\+\s*=', '=', s)
        s = re.sub(r'=\s*\+', '=', s)

        # collapse multiple '+'
        s = re.sub(r'\++', '+', s)
        s = re.sub(r'^\s*\+\s*', '', s)
        s = re.sub(r'\s*\+\s*$', '', s)

        # keep word chars, spaces, '+', '=', '.' (preserve decimals)
        s = re.sub(r"[^\w\s\+\=\.]", " ", s)

        # fix Word spaced decimals like "0 14533" -> "0.14533" (digits only)
        if "." not in s:
            s = re.sub(r"(?<=\b\d)\s+(?=\d\b)", ".", s)

        # collapse whitespace
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    @staticmethod
    def _canon_key(name: str) -> str:
        # canonical (order-insensitive) grouping for tokens like 'T2F2T2' vs 'T2T2F2'
        parts = re.findall(r"[A-Za-z]+(?:\d+)?", name or "")
        parts = [p.upper() for p in parts]
        parts.sort()
        return "-".join(parts) if parts else (name or "").upper()

    @staticmethod
    def _pick_float(text: str) -> Optional[float]:
        if not text:
            return None
        t = text.strip()
        if "." not in t:
            t = re.sub(r"(?<=\b\d)\s+(?=\d\b)", ".", t)
        m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", t)
        try:
            return float(m.group(0)) if m else None
        except Exception:
            return None

    @staticmethod
    def _total_regex():
        return re.compile(r"^\s*[A-Za-z][A-Za-z0-9_]*_tot\s*=")

    def _is_total_equation(self, cleaned: str) -> bool:
        if not cleaned or "=" not in cleaned:
            return False
        if not self._total_regex().match(cleaned):
            return False
        rhs = cleaned.split("=", 1)[1]
        return bool(re.search(r"[A-Za-z]", rhs))

    # (old no-coeff parser kept for reference, but unused)
    def _parse_tokens_no_coeff(self, equation: str):
        eq = self.clean_equation(equation or "")
        if "=" not in eq:
            return [], []
        left, right = [s.strip() for s in eq.split("=", 1)]
        if not left or not right:
            return [], []

        FLOAT = r"(?:\d+(?:\.\d+)?|\.\d+)"

        def parse_side(side: str, label: str):
            out = []
            for term in side.split("+"):
                s = term.strip().replace("*", "")
                m = re.match(rf"^(?:({FLOAT})\s*)?([A-Za-z][A-Za-z0-9_]*)$", s)
                if not m:
                    continue
                mult = float(m.group(1)) if m.group(1) else 1.0
                sp   = m.group(2)
                out.append((sp, mult, label))
            return out

        return parse_side(left, "Reactant"), parse_side(right, "Product")

    # ------------- DOCX readers -------------
    def _read_equations_and_concentrations_from_table(self) -> Tuple[List[str], List[float]]:
        """
        Read tables: equations from 2nd column (index 1), concentrations from 3rd (index 2).
        Returns two aligned lists (same length & order).
        """
        doc = docx.Document(self.docx_path)
        eqs: List[str] = []
        concs: List[float] = []
        seen = set()

        for tbl in doc.tables:
            for row in tbl.rows:
                cells = row.cells
                if len(cells) < 3:
                    continue

                # Equations are in 2nd column; may have multiple lines
                eq_text = None
                for line in (cells[1].text or "").splitlines():
                    cleaned = self.clean_equation(line)
                    if self._is_total_equation(cleaned):
                        eq_text = cleaned
                        break
                if not eq_text:
                    continue

                # Concentration from 3rd column (first float we find)
                conc_val = self._pick_float(cells[2].text or "")
                if conc_val is None:
                    continue

                if eq_text in seen:
                    continue
                seen.add(eq_text)

                eqs.append(eq_text)
                concs.append(float(conc_val))

        return eqs, concs

    def _read_fraction_pairs_stream(self) -> List[Tuple[str, float]]:
        """
        Scan the DOCX for 'SPEC = 0.05' lines (Desired fractions). Ignore *_tot entries.
        Return as an ordered list of (species, fraction).
        """
        doc = docx.Document(self.docx_path)
        pairs: List[Tuple[str, float]] = []
        pat = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*=\s*([0-9]+(?:\.[0-9]+)?|[0-9]\s+[0-9]+)\s*$")

        def consider(text: str):
            if not text:
                return
            line = text.strip()
            m = pat.match(line)
            if not m:
                return
            name, val = m.group(1), m.group(2)
            if name.lower().endswith("_tot"):
                return
            # normalize decimal like "0 45" -> "0.45"
            if "." not in val:
                val = re.sub(r"(?<=\b\d)\s+(?=\d\b)", ".", val)
            try:
                f = float(val)
            except ValueError:
                return
            pairs.append((name, f))

        # tables first (most likely location)
        for tbl in doc.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    for piece in (cell.text or "").splitlines():
                        consider(piece)

        # paragraphs fallback
        for p in doc.paragraphs:
            for piece in (p.text or "").splitlines():
                consider(piece)

        return pairs

    def _build_per_reaction_fractions(self) -> List[Dict[str, float]]:
        """
        Build one dict per equation, mapping RHS species -> fraction.
        Consume the flat fraction stream in order; for each equation with K RHS species,
        take the next K entries and match by exact name; if not found, match by canonical key;
        otherwise assign the next unused from the window.
        """
        stream = self._read_fraction_pairs_stream()
        pos = 0
        out: List[Dict[str, float]] = []

        for eq in self.equations:
            # parse RHS species names using with-coeff parser, but ignore *_tot
            _r, p = self._parse_tokens_with_coeff(eq)
            rhs = [sp for (sp, _m, _lbl) in p if not sp.lower().endswith("_tot")]
            k = len(rhs)
            window = stream[pos:pos + k]
            pos += k

            # exact and canonical lookup tables
            win_map = {nm: fr for (nm, fr) in window}
            win_map_canon = {self._canon_key(nm): fr for (nm, fr) in window}

            assigned: Dict[str, float] = {}
            used_names: Set[str] = set()

            for sp in rhs:
                # 1) exact match
                if sp in win_map:
                    assigned[sp] = win_map[sp]
                    used_names.add(sp)
                    continue
                # 2) canonical match
                ck = self._canon_key(sp)
                if ck in win_map_canon:
                    assigned[sp] = win_map_canon[ck]
                    # mark its original window name as used (best effort)
                    for nm, fr in window:
                        if self._canon_key(nm) == ck and nm not in used_names:
                            used_names.add(nm)
                            break
                    continue
                # 3) fallback: first unused in window
                for nm, fr in window:
                    if nm not in used_names:
                        assigned[sp] = fr
                        used_names.add(nm)
                        break

            out.append(assigned)

        return out

    # ------------- core build -------------
    def _initialize_species(
        self,
        dropped_species_set: Optional[Set[str]] = None,
        record_mode: str = "many_simple",
        ignore_tot_tokens: bool = True,
    ):
        """
        Build:
          - reaction_information_list : list of many-side species per simple reaction (with per-reaction fractions)
          - reaction_concentration_list / reaction_concentration : aligned per-reaction concentrations
          - reactants / products : aggregated (sum of EFFECTIVE coefficients across reactions)
          - repeating dictionaries with exact tokens (no substring checks)
        """
        # reset per-run state
        self.reactants.clear()
        self.products.clear()
        self.reaction_information_list.clear()
        self.reaction_concentration.clear()  # dict
        # (keep self.reaction_concentration_list as loaded from table; it's already aligned)
        seen_keys: Set[tuple] = set()

        # ensure per-reaction fractions are ready/aligned
        if not self.per_reaction_fractions or len(self.per_reaction_fractions) != len(self.equations):
            self.per_reaction_fractions = self._build_per_reaction_fractions()

        def rxn_key(rxn: List[Tuple[str, float, float, str]]) -> tuple:
            # order-independent key by (species, EFFECTIVE coeff)
            return tuple(sorted((sp, float(uf) * float(cf)) for sp, uf, cf, _ in rxn))

        for idx, eq in enumerate(self.equations):
            r_raw, p_raw = self._parse_tokens_with_coeff(eq)  # (sp, coeff_fraction, lbl)

            # decide simple BEFORE dropping *_tot
            is_decomp = (len(r_raw) == 1 and len(p_raw) >= 1)
            is_form   = (len(p_raw) == 1 and len(r_raw) >= 1)
            if record_mode != "all" and not (is_decomp or is_form):
                continue

            # filter *_tot and drop requested species
            r_side = [t for t in r_raw if not t[0].lower().endswith("_tot")]
            p_side = [t for t in p_raw if not t[0].lower().endswith("_tot")]
            if dropped_species_set:
                r_side = [t for t in r_side if t[0] not in dropped_species_set]
                p_side = [t for t in p_side if t[0] not in dropped_species_set]

            # apply per-reaction unit fractions (fallback to 1.0)
            frac_map = self.per_reaction_fractions[idx] if idx < len(self.per_reaction_fractions) else {}

            def apply_coeff(side):
                out = []
                for sp, coeff_fraction, lbl in side:
                    unit_fraction = float(frac_map.get(sp, 1.0))
                    out.append((sp, unit_fraction, float(coeff_fraction), lbl))  # 4-tuple
                return out

            r_side = apply_coeff(r_side)
            p_side = apply_coeff(p_side)

            # choose many-side
            if record_mode == "all":
                recorded = r_side + p_side
            else:
                recorded = p_side if is_decomp else r_side

            if not recorded:
                continue

            key = rxn_key(recorded)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            # append and align concentration dict
            self.reaction_information_list.append(recorded)
            self.reaction_concentration[len(self.reaction_information_list) - 1] = (
                float(self.reaction_concentration_list[idx]) if idx < len(self.reaction_concentration_list) else 0.0
            )

        # ---- aggregate global EFFECTIVE coefficients (sum across reactions) ----
        sum_coeffs: Dict[str, float] = {}
        label_map: Dict[str, str] = {}

        for rxn in self.reaction_information_list:
            within: Dict[str, float] = {}
            lbls: Dict[str, str] = {}
            for sp, uf, cf, lbl in rxn:
                token = sp.strip()
                eff = float(uf) * float(cf)
                within[token] = within.get(token, 0.0) + eff
                if token not in lbls:
                    lbls[token] = lbl
            for token, s in within.items():
                sum_coeffs[token] = sum_coeffs.get(token, 0.0) + s
                if token not in label_map:
                    label_map[token] = lbls[token]

        self.reactants.clear()
        self.products.clear()
        for token, total_eff in sum_coeffs.items():
            tup = (token, float(total_eff), label_map.get(token, "Product"))
            if tup[2] == "Reactant":
                self.reactants.add(tup)
            else:
                self.products.add(tup)

        # zeroed concentration map for all recorded species
        self.global_concentration = {sp: 0.0 for sp in sum_coeffs.keys()}

        # ---- exact-token repeat bookkeeping (in EFFECTIVE space) ----
        occurrences: Dict[str, Dict[int, float]] = {}  # species -> {rxn_idx -> eff_sum_in_that_rxn}
        for idx, rxn in enumerate(self.reaction_information_list):
            per_rxn: Dict[str, float] = {}
            for sp, uf, cf, _ in rxn:
                token = sp.strip()
                eff = float(uf) * float(cf)
                per_rxn[token] = per_rxn.get(token, 0.0) + eff
            for token, eff_sum in per_rxn.items():
                occurrences.setdefault(token, {})[idx] = occurrences.get(token, {}).get(idx, 0.0) + eff_sum

        self.dictionary_of_repeating_species = {
            token: sorted(idx_map.keys()) for token, idx_map in occurrences.items() if len(idx_map) > 1
        }
        self.repeating_sepcies_dictionary = {
            token: [(float(idx_map[i]), i) for i in sorted(idx_map.keys())]
            for token, idx_map in occurrences.items() if len(idx_map) > 1
        }

        repeating_rxn_indices: Set[int] = set()
        for idxs in self.dictionary_of_repeating_species.values():
            repeating_rxn_indices.update(idxs)

        self.reactions_without_repeats_indices = [
            i for i in range(len(self.reaction_information_list)) if i not in repeating_rxn_indices
        ]
        self.reactions_without_repeats = [
            self.reaction_information_list[i] for i in self.reactions_without_repeats_indices
        ]

    # ------------- extras -------------
    def extract_manyside_zero_dicts(self) -> List[Dict[str, float]]:
        """One zero-initialized dict per recorded simple reaction (many-side only)."""
        out: List[Dict[str, float]] = []
        for rxn in self.reaction_information_list:
            d: Dict[str, float] = {}
            for sp, _uf, _cf, _lbl in rxn:
                d[sp] = 0.0
            if d:
                out.append(d)
        return out

    def extract_manyside_coeff_dicts(self) -> List[Dict[str, float]]:
        """One dict per recorded simple reaction: {species: EFFECTIVE coefficient}."""
        out: List[Dict[str, float]] = []
        for rxn in self.reaction_information_list:
            d: Dict[str, float] = {}
            for sp, uf, cf, _lbl in rxn:
                d[sp] = float(uf) * float(cf)
            if d:
                out.append(d)
        return out

    def debug_dump(self, limit: int = 5):
        print(f"equations: {len(self.equations)}  concentrations: {len(self.reaction_concentration_list)}")
        for i, eq in enumerate(self.equations[:limit], 1):
            r, p = self._parse_tokens_with_coeff(eq)
            print(f"[{i}] {eq}")
            print(f"   Reactants(raw): {[(a,b) for a,b,_ in r]}  Products(raw): {[(a,b) for a,b,_ in p]}")
        print(f"recorded reactions (many-side): {len(self.reaction_information_list)}")

    def global_concentration_dataframe(self, reaction_index: Optional[List[int]] = None) -> pd.DataFrame:
        """
        Return a tidy DataFrame of the current global concentration map.
        If reaction_index is given, only include species that appear in those reactions.
        """
        if reaction_index is not None:
            # Collect species from the requested reactions
            selected_species = set()
            for i in reaction_index:
                if 0 <= i < len(self.reaction_information_list):
                    for sp, *_ in self.reaction_information_list[i]:
                        selected_species.add(sp)
            data = {sp: self.global_concentration.get(sp, 0.0) for sp in selected_species}
        else:
            # Default: full global concentration
            data = dict(self.global_concentration)

        df = pd.DataFrame(
            {"Species": list(data.keys()),
            "Concentration": [float(v) for v in data.values()]}
        )
        return df.sort_values("Species").reset_index(drop=True)


    def export_global_concentration(
        self,
        filepath: str = "global_concentration.xlsx",
        round_to: Optional[int] = 6,
        include_fractions: bool = True  # NEW: controls whether we also export per-reaction fractions
    ) -> str:
        """
        Write an .xlsx file with:
        - Sheet 'global_concentration': total concentration per species (after current calc).
        - Sheet 'unit_coeff_fractions' (if include_fractions): per-reaction unit & coeff fractions
            for every species as currently stored in self.reaction_information_list.

        Returns the output path.
        """
        # --- sheet 1: global concentrations (existing behavior) ---
        df_gc = self.global_concentration_dataframe()
        if round_to is not None:
            df_gc["Concentration"] = df_gc["Concentration"].round(round_to)

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df_gc.to_excel(writer, sheet_name="global_concentration", index=False)

            if include_fractions:
                # --- sheet 2: per-reaction unit/coeff fractions ---
                rows = []
                for rxn_idx, rxn in enumerate(self.reaction_information_list):
                    # If you also want to record the reaction total on this sheet:
                    rxn_total = float(self.reaction_concentration_list[rxn_idx]) if rxn_idx < len(self.reaction_concentration_list) else 0.0
                    for sp, uf, cf, lbl in rxn:
                        rows.append({
                            "Reaction": rxn_idx +1 ,
                            "Species": sp,
                            "redistributed UnitFraction": float(uf),
                            "CoeffFraction": float(cf),
                            "EffectiveFraction": float(uf) * float(cf),
                        })

                df_frac = pd.DataFrame(rows).sort_values(["Reaction", "Species"]).reset_index(drop=True)

                if round_to is not None:
                    for col in ["UnitFraction", "CoeffFraction", "EffectiveFraction", "ReactionTotal"]:
                        if col in df_frac.columns:
                            df_frac[col] = df_frac[col].round(round_to)

                df_frac.to_excel(writer, sheet_name="unit_coeff_fractions", index=False)

        return filepath
    def _recorded_equations_in_order(self) -> List[str]:
        """
        Return equation strings aligned 1:1 with self.reaction_information_list,
        using the same selection/dedup logic as _initialize_species (many_simple).
        """
        out_eqs: List[str] = []
        seen_keys: Set[tuple] = set()

        def rxn_key(rxn_rows: List[Tuple[str, float, float, str]]) -> tuple:
            # order-independent key by (species, EFFECTIVE coeff)
            return tuple(sorted((sp, float(uf) * float(cf)) for sp, uf, cf, _ in rxn_rows))

        for idx, eq in enumerate(self.equations):
            # parse
            r_raw, p_raw = self._parse_tokens_with_coeff(eq)
            is_decomp = (len(r_raw) == 1 and len(p_raw) >= 1)
            is_form   = (len(p_raw) == 1 and len(r_raw) >= 1)

            # follow same record_mode default ("many_simple")
            # if you expose record_mode as an attribute, prefer that
            record_mode = getattr(self, "record_mode", "many_simple")
            if record_mode != "all" and not (is_decomp or is_form):
                continue

            # drop *_tot tokens
            r_side = [t for t in r_raw if not t[0].lower().endswith("_tot")]
            p_side = [t for t in p_raw if not t[0].lower().endswith("_tot")]

            # apply per-reaction unit fractions (fallback 1.0)
            frac_map = self.per_reaction_fractions[idx] if idx < len(self.per_reaction_fractions) else {}
            def apply_coeff(side):
                return [(sp, float(frac_map.get(sp, 1.0)), float(cf), lbl) for sp, cf, lbl in side]
            r_side = apply_coeff(r_side)
            p_side = apply_coeff(p_side)

            # choose many-side like _initialize_species
            recorded = p_side if is_decomp else r_side
            if not recorded:
                continue

            key = rxn_key(recorded)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            out_eqs.append(eq)

        return out_eqs

    def export_redistributed_docx(
        self,
        filepath: str = "redistributed_system_exact.docx",
        round_to: int = 9,
        table_style: str = "Table Grid",
        add_heading: bool = True,
    ) -> str:
        """
        Export a DOCX with columns:
          [Reaction # | Equation (exact text) | Unit Fractions (each on its own line with '=') | Reaction Total]

        - Unit fractions are taken from the CURRENT self.reaction_information_list
          (i.e., after you run your redistribution/calculation step).
        - The table uses a grid style for visible cell borders.
        """
        doc = Document()
        if add_heading:
            doc.add_heading("Redistributed Reaction System", level=1)

        # Align equations to recorded reactions in the same order used to build reaction_information_list
        ordered_eqs = self._recorded_equations_in_order()

        # Build table with a visible grid
        table = doc.add_table(rows=1, cols=4)
        try:
            table.style = table_style  # 'Table Grid' gives visible borders
        except Exception:
            # If style not present, it's safe to proceed without setting it
            pass

        hdr = table.rows[0].cells
        hdr[0].text = "Reaction #"
        hdr[1].text = "Equation"
        hdr[2].text = "Unit Fractions (per species)"
        hdr[3].text = "Reaction Total"

        # Fill each row
        for rxn_idx, rxn in enumerate(self.reaction_information_list):
            eq_str = ordered_eqs[rxn_idx] if rxn_idx < len(ordered_eqs) else ""

            # Multi-line content inside the SAME cell, with equals signs
            # Keep the current order stored in reaction_information_list
            lines = []
            for sp, uf, cf, lbl in rxn:
                val = round(float(uf), round_to) if round_to is not None else float(uf)
                lines.append(f"{sp} = {val}")
            uf_text = "\n".join(lines)

            # Reaction total
            total = float(self.reaction_concentration_list[rxn_idx]) if rxn_idx < len(self.reaction_concentration_list) else 0.0
            total = round(total, round_to) if round_to is not None else total

            row = table.add_row().cells
            row[0].text = str(rxn_idx)
            row[1].text = eq_str
            row[2].text = uf_text
            row[3].text = str(total)

        doc.save(filepath)
        return filepath






class equilibrium_calculation(Species_class):
    def __init__(
        self,
        docx_path: str = None,
        equations_list_input: Optional[List[str]] = None,
        dropped_species_set: Optional[Set[str]] = None,
        record_mode: str = "many_simple",
        ignore_tot_tokens: bool = True,
    ):
        super().__init__(docx_path=docx_path, equations_list_input=equations_list_input)
        # will hold fixed concentrations for repeating species after redistribution
        self._fixed_repeat_conc: Dict[str, float] = {}
    


    def calculate_equilibrium_all(self, renormalize: bool = True, clear_previous: bool = True):
        """
        Compute global concentrations using CURRENT (possibly redistributed) 4-tuples:
          - Non-repeats: sum contributions across reactions (as before).
          - Repeats: set to the globally fixed concentration computed in
                     apply_average_and_redistribute_on_repeats (do NOT sum).
        """
        assert len(self.reaction_information_list) == len(self.reaction_concentration_list), \
            "reaction info and concentration lists are misaligned"

        # species universe
        all_species = set()
        for rxn in self.reaction_information_list:
            for sp, _uf, _cf, _ in rxn:
                all_species.add(sp)

        if not getattr(self, "global_concentration", None) or clear_previous:
            self.global_concentration = {sp: 0.0 for sp in all_species}
        else:
            for sp in all_species:
                self.global_concentration.setdefault(sp, 0.0)

        # Build a quick set for repeats we have fixed concentrations for
        fixed_repeats: Set[str] = set(getattr(self, "_fixed_repeat_conc", {}).keys())

        # Accumulate only NON-repeats; skip repeats here
        for idx, rxn in enumerate(self.reaction_information_list):
            total_conc = float(self.reaction_concentration_list[idx])

            # gather eff shares (after redistribution)
            effs = []
            for sp, uf, cf, _lbl in rxn:
                eff = float(uf) * float(cf)
                effs.append((sp.strip(), eff))

            eff_sum = sum(e for _, e in effs)
            scale = (1.0 / eff_sum) if (renormalize and eff_sum > 0.0) else 1.0

            for tok, eff in effs:
                if tok in fixed_repeats:
                    continue  # we'll set repeats later to their fixed values
                portion = total_conc * eff * scale
                self.global_concentration[tok] = self.global_concentration.get(tok, 0.0) + portion

        # Set fixed concentrations for repeating species
        for tok, C_S in getattr(self, "_fixed_repeat_conc", {}).items():
            self.global_concentration[tok] = float(C_S)

    def calculate_equilibrium_average(
        self,
        damp_step: float = 0.05,
        max_damp_steps: int = 200,
        enable_damping: bool = True
    ):
        self.apply_average_and_redistribute_on_repeats(
            damp_step=damp_step,
            max_damp_steps=max_damp_steps,
            enable_damping=enable_damping,
        )
        self.calculate_equilibrium_all(renormalize=True, clear_previous=True)


