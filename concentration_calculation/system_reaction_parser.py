import helpertesting as hd

class CompartmentSystem:
    def __init__(self, docx_path):
        self.docx_path = docx_path
        self.systems = {}  # key = system name, value = hd.SpeciesMatrix instance
        self._parse_document()

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
