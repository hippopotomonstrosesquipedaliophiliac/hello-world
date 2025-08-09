import pandas as pd
import docx
import re
import CalcALL


class Species_class:
    def __init__(self, docx_path= None, equations_list_input = None):
        self.docx_path = docx_path
        if docx_path is not None:
            self.equations = self._read_equations()
        elif equations_list_input is not None:
            self.equations = equations_list_input
        else:
            raise ValueError("Either docx_path or equations_list_input must be provided.")
        self.reactants = set()
        self.products = set()
        self.arrow = "="  # Default to False, can be set later if needed
        self.equilibrium_arrows_list = ["⇌", "<=>", "<->"]
    def _read_equations(self):
        doc = docx.Document(self.docx_path)
        return [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    def _parse_equation(self, equation):
        for arrow in self.equilibrium_arrows_list:
            if arrow in equation:
                self.arrow = arrow
        equation = re.sub(fr'[^\w\s\+\{self.arrow}]', '', equation)
        sides = equation.split(self.arrow)

        if len(sides) != 2:
            return [], []
        # Ignore if either side is empty (e.g., "=H2O" or "H2O=")
        if not sides[0].strip() or not sides[1].strip():
            return [], []
        if not sides[0].strip() and not sides[1].strip():
            raise ValueError(f"Invalid equation format: {equation}")
        def parse_side(side, label):
            tuples = []
            for term in side.split("+"):
                term = term.strip()
                match = re.match(r'^(\d+)?\s*(\w+)', term)
                if match:
                    coeff = int(match.group(1)) if match.group(1) else 1
                    species = match.group(2)
                    tuples.append((species, coeff, label)) 
            return tuples
        reactants = parse_side(sides[0], "Reactant")
        products = parse_side(sides[1], "Product")
        return reactants, products

    def _initialize_species(self, dropped_species_set=None):
        self.reactants = set()
        self.products = set()
        for eq in self.equations:
            reactants, products = self._parse_equation(eq)
            if dropped_species_set is not None:
                reactants = [r for r in reactants if r[0] not in dropped_species_set]
                products = [p for p in products if p[0] not in dropped_species_set]
            self.reactants.update(reactants)
            self.products.update(products)

    def categorize_species(self, dropped_species_set=None):
        self._initialize_species(dropped_species_set)

    @property
    def species(self):
        return set([r[0] for r in self.reactants]).union([p[0] for p in self.products])

    def get_species_dataframe(self):
        return pd.DataFrame((list(self.species)), columns=["Species"])

    def get_reactants_dataframe(self):
        return pd.DataFrame((list(self.reactants)), columns=["Species", "Coefficient", "Type"])

    def get_products_dataframe(self):
        return pd.DataFrame((list(self.products)), columns=["Species", "Coefficient", "Type"])

class equilibrium_calculation(Species_class):
    def __init__(self, docx_path=None, equations_list_input=None, dropped_species_set=None):
        super().__init__(docx_path=docx_path, equations_list_input=equations_list_input)
        self._initialize_species(dropped_species_set)
    def to_matrix(self):
        reactants = list([r for r in self.reactants])
        products = list([p for p in self.products])

        print()
        matrix = pd.DataFrame(float(0), index=[r[0] for r in reactants], columns=[p[0] for p in products])
        # Mark 1 if the reactant and product exist in the global sets
        print(self.equations)
        for eq in self.equations:
            reactants, products = self._parse_equation(eq)
            for r_species, r_coeff, _ in reactants:
                for p_species, p_coeff, _ in products:
                    # You can choose what to fill here. Example: sum of coefficients
                    matrix.at[r_species, p_species] += round(r_coeff/ p_coeff,6) if p_coeff != 0 else 0
        matrix["synthesized_unit"] = matrix.sum(axis=1) 
    # Add column-wise sum as a new row
        total_fraction_row = matrix.sum(axis=0)
        total_fraction_row.name = "total_fraction_synthesized/intermediates"
        matrix = pd.concat([matrix, total_fraction_row.to_frame().T])
        return matrix
    
        

class miscellaneous():
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