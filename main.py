import functions as sf

def main ():
    # Create scatch workspace and initialize list of scratch names
    old_workspace, ok, error = sf.create_temp_workspace()

    # Define a variable to differentiate each process
    json_count = 1

    # Get complete filepaths for all JSON files for process
    json_filepaths, ok, error = sf.get_filepaths("Select JSON file(s).", [('JSON', '*.json')])

    # Iterate over each JSON filepath
    for path in json_filepaths:
        # Print a message for the user
        print("\n###### Performing operations defined in JSON #{}...".format(json_count))

        # Call function to parse current JSON file
        setup_dict, ok, error = sf.parse_json(path)

        # Call function to check if JSON is valid - Also completes operations on JSON
        ok, error = sf.check_json(setup_dict)

        # Iterate JSON file number
        json_count += 1

    # Clean up scratch workspace
    ok, error = sf.delete_temp_workspace([], old_workspace)


if __name__ == "__main__":
    main()
