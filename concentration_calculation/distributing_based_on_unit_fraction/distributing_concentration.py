import helper_distribution
DOCX_PATH = "C:/Users/nhanp/OneDrive - Texas A&M University/CIA summary equations fin2.docx"
def main():
    sc = helper_distribution.equilibrium_calculation(DOCX_PATH)
    sc._initialize_species()
    # your redistribution (with or without your damping wrapper)
    sc.apply_average_and_redistribute_on_repeats()
    # if you're using the external damping wrapper, call it here, then:
    sc.calculate_equilibrium_all()

    # Now export the exact-format DOCX with grid + equals signs:
    out_path = sc.export_redistributed_docx(
        filepath="redistributed_system_CIA2.docx",
        round_to=9,              # decimals
        table_style="Table Grid" # ensures visible borders
    )
    print("Wrote:", out_path)

    # for reaction in sc.list_of_reaction:
    #     print("reaction:", reaction)
    # peek a reaction
    # sc.calculate_equilibrium_average()

if __name__ == "__main__":
    # This block will only run if the script is executed directly
    main()
    pass    
##path: "C:/Users/nhanp/OneDrive - Texas A&M University/CIA summary equations fin2.docx"