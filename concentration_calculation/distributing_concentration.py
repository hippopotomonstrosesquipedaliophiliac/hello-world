import helper_distribution as hd
# Read equations from docx
def main():
    drop_nutrients_bool = False
    convert_to_equilibrium = False
    user_input = input("Do you want to drop nutrients? (y/n): ").strip().lower()
    while user_input not in ['y', 'n']:
        print("Invalid input. Please enter 'y' or 'n'.")
        user_input = input("").strip().lower()
    user_to_equilibrium = input("Do you want to convert equations to equilibrium format? (y/n): ").strip().lower()
    while user_to_equilibrium not in ['y', 'n']:
        print("Invalid input. Please enter 'y' or 'n'.")
        user_to_equilibrium = input("").strip().lower()
    doc_with_equations_input = "C:/Users/nhanp/OneDrive - Texas A&M University/five-steps-TCA.docx"
    species_obj = hd.Species_class(doc_with_equations_input)
    
    csv_file_name = "testing_something"
    dropped_species = []
    print("original equations: ")
    if user_to_equilibrium == 'y':
        convert_to_equilibrium = True
        for eq in range(len(species_obj.equations)):
            species_obj.equations[eq] = species_obj.equations[eq].replace("=", "⇌")
    for eq in species_obj.equations:
        print(eq)
    if user_input == 'y':
        drop_nutrients_bool = True
    if not drop_nutrients_bool:
        species_obj._initialize_species()
   
    elif drop_nutrients_bool:
        print("Dropping nutrients is enabled. Proceeding with CalcALL.")
        final_species, dropped_species, _ = hd.CalcALL.find_S_easyname(
            csv_file_name, doc_with_equations=doc_with_equations_input)
        species_obj._initialize_species(dropped_species_set=dropped_species)
        print("Dropped Species:", dropped_species)
    print("reactions: ")
    for eq in range(len(species_obj.equations)):
        if dropped_species is not None:
            for dropped_specimen in dropped_species:
                if dropped_specimen in species_obj.equations[eq]:
                    species_obj.equations[eq] = species_obj.equations[eq].replace(dropped_specimen, "")
                    species_obj.equations[eq] = hd.miscellaneous.clean_equation(species_obj.equations[eq])
    print(species_obj.equations)
    print("All species:\n", species_obj.get_species_dataframe())
    print("Reactants:\n", species_obj.get_reactants_dataframe())
    print("Products:\n", species_obj.get_products_dataframe(),"\n")
    matrix_species_constructor = hd.SpeciesMatrix(equations_list_input=species_obj.equations, dropped_species_set=dropped_species)
    species_matrix = matrix_species_constructor.to_matrix()
    print("Species Matrix:\n", species_matrix)
    species_matrix.to_excel(f"{csv_file_name}_species_matrix.xlsx", index=True)

if __name__ == "__main__":
    main()