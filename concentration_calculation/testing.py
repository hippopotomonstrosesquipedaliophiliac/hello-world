import system_reaction_parser as srp

# Read equations from docx
import testing_miscellaneous
from testing_miscellaneous import edit_then_wait, check_if_previous_data_frame_exist, load_workbook
def main():
    tkinter_object = testing_miscellaneous.miscellaneous()
    # while True:
    #     dropping_nutrient_bool = tkinter_object.to_confirm(label="Do you want to drop nutrients? (y/n): ")
    #     break
    
    # user_to_equilibrium = input("Do you want to convert equations to equilibrium format? (y/n): ").strip().lower()
    # while user_to_equilibrium not in ['y', 'n']:
    #     print("Invalid input. Please enter 'y' or 'n'.")
    #     user_to_equilibrium = input("").strip().lower()
    prev_frame_exist= False
    choose_prev_frame = False
    doc_with_equations_input = "C:/Users/nhanp/OneDrive - Texas A&M University/five-steps-TCA.docx"
    """using a previous file that matches the current data frame:
    1. construct the dataframe
    2. check in the folder to see if there's any matching dataframe
    3. as the user if they want to use the previous dataframe or not
    - if yes: use that dataframe
    - if no: ask user to enter new input """
    requesting_reactants_dataframe = r"reactants' dataframe/"
    compartment_manager = srp.CompartmentSystem(doc_with_equations_input)
    current_species_list = []
    for system_name, system_info in compartment_manager.get_all_systems().items():

        # if user_to_equilibrium == 'y':
        #     system_obj.equations = [eq.replace("=", "⇌") for eq in system_obj.equations]
        #     system_obj._initialize_species_from_reaction()

        # write/append the sheet – pandas will create the file on first write
        current_species_list.extend(([current_spec_name for current_spec_name 
                                   in system_info["speciesMatrix"].construct_concentration_data(system_name=system_name)["species"]]))

    current_species_list = sorted(current_species_list)
    previous_data_frames = (check_if_previous_data_frame_exist(folders_path=requesting_reactants_dataframe))
    print(current_species_list)
    print(previous_data_frames)
    list_of_previous_frame_xlsx = []
# testing.py  — replace the block after computing previous_data_frames with this

    previous_data_frames = check_if_previous_data_frame_exist(folders_path=requesting_reactants_dataframe)
    list_of_previous_frame_xlsx = []
    prev_frame_exist = False

    for d in previous_data_frames:
        for fname, species_list in d.items():
            if current_species_list == species_list:
                list_of_previous_frame_xlsx.append(fname)
                prev_frame_exist = True

    if prev_frame_exist:
        choose_prev_frame = tkinter_object.to_confirm(
            title="previous frame exist",
            label="there're previous dataframes that match with the current system, use a previous dataframe ?"
        )
        if choose_prev_frame:
            requesting_reactants_dataframe = testing_miscellaneous.os.path.join(
                requesting_reactants_dataframe,
                tkinter_object.select_from_list(
                    title="select the dataframe to be used",
                    options=list_of_previous_frame_xlsx
                )
            )
        else:
            # user wants a new file inside that folder
            requesting_reactants_dataframe = tkinter_object.choose_output_path(
                ui=tkinter_object, dir=requesting_reactants_dataframe
            )
            for system_name, system_info in compartment_manager.get_all_systems().items():
                system_info["speciesMatrix"].construct_concentration_data(
                    system_name=system_name, to_rewrite=True, dir=requesting_reactants_dataframe
                )
            testing_miscellaneous.messagebox.showinfo(
            message=f"[INFO] Please fill in the whole-cell concentrations here: {requesting_reactants_dataframe}"
            )
            ok = edit_then_wait(requesting_reactants_dataframe, require_saved=True, timeout=600)
    else:
        # << NEW: no previous frames found — create a new file >>
        requesting_reactants_dataframe = tkinter_object.choose_output_path(
            ui=tkinter_object, dir=requesting_reactants_dataframe
        )
        for system_name, system_info in compartment_manager.get_all_systems().items():
            system_info["speciesMatrix"].construct_concentration_data(
                system_name=system_name, to_rewrite=True, dir=requesting_reactants_dataframe
            )
        testing_miscellaneous.messagebox.showinfo(
        message=f"[INFO] Please fill in the whole-cell concentrations here: {requesting_reactants_dataframe}"
        )
        ok = edit_then_wait(requesting_reactants_dataframe, require_saved=True, timeout=600)

    # Now we *definitely* have a FILE path in requesting_reactants_dataframe
    

    data_sheets_name = load_workbook(requesting_reactants_dataframe,read_only=True).sheetnames
    sheet_names_iterator = iter(data_sheets_name)
    for system_name , system_info in compartment_manager.get_all_systems().items():
        try:
            sheet_name = next(sheet_names_iterator)
        except StopIteration:
            testing_miscellaneous.messagebox.showerror(message = f"{RuntimeError("there are more reaction systems than data sheet to be allowed")}")
        system_info["speciesMatrix"].appending_concentration_data(concentration_file_path = requesting_reactants_dataframe, system_sheet_name = sheet_name)
        system_info["speciesMatrix"].export_species_template(output_file = f"system_{system_info["compartment"]}_{system_name}_template.xlsx")
        system_info["speciesMatrix"].get_species_dataframe(output_file = f"system_{system_info["compartment"]}_{system_name}_dataframe.xlsx")
    global_concentration = compartment_manager.snapshot_global_concentrations()
    validate_chemical_reactions = compartment_manager.validate_local_participation()
    asser_chemical_reactions = compartment_manager.assert_local_participation()
    print(global_concentration)
 
# Unique species -> totals + per-compartment breakdown
    
    for system_name, system_info in compartment_manager.get_all_systems().items():
        system_info["speciesMatrix"].calculate_equilibrium(system_info["compartment"],global_concentration)
    tkinter_object.close()
if __name__ == "__main__":
    main()