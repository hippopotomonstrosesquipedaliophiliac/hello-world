import system_reaction_parser as srp

# Read equations from docx
def main():
    tkinter_object = srp.hd.miscellaneous()
    root = tkinter_object.root
    user_input = input("Do you want to drop nutrients? (y/n): ").strip().lower()
    while user_input not in ['y', 'n']:
        print("Invalid input. Please enter 'y' or 'n'.")
        user_input = input("").strip().lower()

    user_to_equilibrium = input("Do you want to convert equations to equilibrium format? (y/n): ").strip().lower()
    while user_to_equilibrium not in ['y', 'n']:
        print("Invalid input. Please enter 'y' or 'n'.")
        user_to_equilibrium = input("").strip().lower()

    doc_with_equations_input = "C:/Users/nhanp/OneDrive - Texas A&M University/five-steps-TCA.docx"
    csv_file_name = "testing_something"
    concentration_requesting_file = "concentration_requesting_data.xlsx"
    compartment_manager = srp.CompartmentSystem(doc_with_equations_input)
    i = 0
    if srp.hd.os.path.exists(concentration_requesting_file):
        overwrite = tkinter_object.confirm(
            title="File already exists",
            label=f"'{concentration_requesting_file}' already exists.\nDo you want to overwrite the previous data?"
        )
        if not overwrite:
            print("Canceled by user.")
            tkinter_object.close()
            return
        srp.hd.os.remove(concentration_requesting_file)


    for system_name, system_info in compartment_manager.get_all_systems().items():
        system_obj = system_info["speciesMatrix"]

        if user_to_equilibrium == 'y':
            system_obj.equations = [eq.replace("=", "⇌") for eq in system_obj.equations]
            system_obj._initialize_species_from_reaction()

        # write/append the sheet – pandas will create the file on first write
        system_obj.construct_concentration_data(output_path=concentration_requesting_file, system_index=i+1)
        i += 1

    print("reactants' dataframe has been exported")
    print(f"[INFO] Please fill in the whole-cell concentrations here: {concentration_requesting_file}")
    tkinter_object.close()
if __name__ == "__main__":
    main()