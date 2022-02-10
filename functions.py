import json, pandas, os, time, arcpy
import tkinter as tk
from tkinter import filedialog as tkfd

def create_temp_workspace ():
    # Print a status message
    print("Creating temporary workspace...\n")

    # Preserve current workspace, if any
    old_workspace = arcpy.env.workspace

    # Set scratch workspace to current working directory
    arcpy.env.scratchWorkspace = os.getcwd()

    # Set scratch workspace to a new scratch folder - this is created in the current working directory
    arcpy.env.scratchWorkspace = arcpy.env.scratchFolder

    # Return path to temporary folder and return code and message
    return old_workspace, 1, 'No errors'


def delete_temp_workspace (scratch_names, old_workspace):
    # Print a status message
    print("\nCleaning up...")

    # Iterate over any scratch names created while doing any geoprocessing
    for name in scratch_names:
        # Delete current name from the scratch workspace
        arcpy.Delete_management(name)

    # Delete the scratch folder once it is empty
    arcpy.Delete_management(arcpy.env.scratchFolder)

    # Restore old workspace
    arcpy.env.workspace = old_workspace

    # Return code and message
    return 1, 'No Errors'


def get_filepaths (message, filetypes):
    # Create tkinter window and hide it
    root = tk.Tk()
    root.withdraw()

    # Print a message for the user
    print(message)

    # Define filetypes and get path to input table
    filetypes = filetypes
    initial_dir = r'C:'
    filepaths = tkfd.askopenfilenames(title = message, initialdir = initial_dir, filetypes = filetypes)

    # Destroy tkinter window
    root.destroy()

    return filepaths, 1, 'No errors'


def parse_json (json_path):
    # Print a message for the user
    print("Parsing JSON at location:\n\t{}".format(json_path))

    # Open JSON files with read access
    with open(json_path, 'r') as file_object:
        # Convert opened JSON into Python dictionary
        parsed_json = json.load(file_object)

    # Return parsed JSON files as Python dictionary
    return parsed_json, 1, 'No errors'


def check_json (setup_dict):
    # Print message for the user
    print("\nChecking current JSON for errors...")

    # Initialize variables for JSON validity and bad columns and subsets
    good = True
    bad_subsets_present = False
    bad_subsets = []
    bad_columns = []

    # Check if source path exits
    if not os.path.isfile(setup_dict["absolute_source_path"]):
        # If it does not, print a message to the user
        print("\tERROR: Source path is invalid, please verify that file exists. Terminating operations for current file."
              "\n\t\t- Path: {}".format(setup_dict["absolute_source_path"]))

        # If source table doesn't exist, return error codes
        return 2, "Nonexistent source table"

    # Check if output path exists
    if not os.path.isdir(setup_dict["absolute_svi_path"]):
        # If not, print message to the user
        print("\tERROR: Output path does not exist. Creating directory at following location:"
              "\n\t\t- Path: {}".format(setup_dict["absolute_svi_path"]))

        # Create new directory at the output path
        os.mkdir(setup_dict["absolute_svi_path"])

    # Loop through all subsets
    for key, value in setup_dict["subsets"].items():
        # Check if subset components are in theme dictionary
        if value != "ALL" and any(theme not in setup_dict["themes"].keys() for theme in value):
            # If not, append key to list of bad subsets and set bad_subsets to True
            bad_subsets.append(key)
            bad_subsets_present = True

    # Check if bad subsets were found
    if bad_subsets_present:
        # If so, print message for user
        print("\tERROR: The following subsets contain nonexistent themes and will be skipped:"
              "\n\t\t- Themes: {}".format(bad_subsets))

    # Convert source CSV to Pandas dataframe
    pandas_df = pandas.read_csv(setup_dict["absolute_source_path"])

    # Create new list to store all columns in JSON file
    all_columns = setup_dict["geoid_fields"] + [setup_dict["join_field"]]

    # Loop through all themes in JSON file
    for themes_key, themes_value in setup_dict["themes"].items():
        # Loop through values in estimated_totals section of current theme
        for key, value in themes_value["estimated_totals"].items():
            # Append the values of all keys in estimated_totals to all_columns list
            all_columns += value
        # Generate a list of all values in the estimated_percentages section and store in all_columns list
        all_columns += [value for key, value in themes_value["estimated_percentages"].items()]

    # Loop through list of all columns
    for item in all_columns:
        # Check if item in list match a column name in pandas_df
        if item not in pandas_df.columns:
            # If not, append to list of bad columns and set JSON validity variable to False
            bad_columns.append(item)
            good = False

    # Check if JSON validity variable is still good
    if not good:
        # If not, print message to user displaying all bad columns
        print("\tERROR: The following columns do not exist in source table. Terminating operations for current file."
              "\n\t\t- Path: {0}\n\t\t- Columns: {1}".format(setup_dict["absolute_source_path"], bad_columns))
    elif good:
        # If so, call function to process current JSON file
        ok, error = subset_pros(setup_dict, pandas_df, bad_subsets)

    return 1, 'No errors'


def subset_pros (setup_dict, pandas_df, bad_subsets):
    # Print a message for the user
    print("\nCreating subset tables...")

    # Create path for new directory
    dir_path = setup_dict["absolute_svi_path"]
    dir_name = r"{0}_csv_{1}".format(setup_dict["set_name"], time.strftime("%Y%m%d-%H%M%S"))
    complete_dir_path = os.path.join(dir_path, dir_name)

    # Create new directory to store generated files in
    os.mkdir(complete_dir_path)

    # Loop through all subsets
    for key, value in setup_dict["subsets"].items():
        # Check if current key is not in list of bad subsets
        if key not in bad_subsets:
            # Print a message for the user
            print("\tCreating table for subset: {}".format(key))

            # Create subset of columns
            subset, ok, error = svi_calc(key, value, pandas_df, setup_dict)

            # Create complete output path for subset CSV
            path = complete_dir_path
            filename = r"{0}_{1}.csv".format(setup_dict["set_name"], key)
            output_path = os.path.join(path, filename)

            # Save subset to CSV located at generated output path
            subset.to_csv(output_path, encoding = 'utf-8', index = False)

            # Print a message for the user
            print("\t\t- Table stored at: {}".format(output_path))

            # Check if current subset key is in list of spatial subsets
            if key in setup_dict["spatial_subsets"]:
                # If so, call function to join csv to spatial features
                shp_output_path, ok, errors = join_table(complete_dir_path, key, setup_dict["join_shapefile_path"],
                                                         output_path, setup_dict["join_field"])

                # Print a message for the user
                print("\t\t- Spatial features stored at: {}".format(shp_output_path))

    # Create complete output path for complete pandas dataframe
    path = complete_dir_path
    filename = r"{0}_COMPLETE.csv".format(setup_dict["set_name"])
    output_path = os.path.join(path, filename)

    # Convert final dataframe to csv
    pandas_df.to_csv(output_path, encoding = 'utf-8', index = False)

    # Print a message for the user
    print("\n\tTable containing all fields in final dataframe stored at: \n\t\t{}".format(output_path))

    return 1, 'No errors'


def svi_calc (subset_key, subset_comp, pandas_df, setup_dict):
    # Define list of theme SVIs and list of fields to include in subset
    theme_svi_list = []
    field_list = []

    # Loop through all themes defined in setup_dict
    for setup_dict_key, setup_dict_value in setup_dict["themes"].items():
        # If theme is included in subset_comp, do SVI calculation for that theme
        if setup_dict_key in subset_comp or subset_comp == "ALL":
            # Create list of estimate and percentage keys
            e_key_list = []
            ep_key_list = []
            epl_key_list = []

            # Loop through fields defined in 'estimated_totals' for current theme in setup_dict
            for key, value in setup_dict_value["estimated_totals"].items():
                # Create complete key and append to list of estimate keys
                comp_key = "E_{}".format(key)
                e_key_list.append(comp_key)

                # Calculate new column for sum of columns in original data
                pandas_df[comp_key] = pandas_df[value].sum(axis = 1)

            # Create value to iterate over indexes in est_key_list
            est_list_iter = 0

            # Loop through fields defined in 'estimated_percentages' for current theme in setup_dict
            for key, value in setup_dict_value["estimated_percentages"].items():
                # Create complete key and append to list of estimate percentage keys
                comp_key = "EP_{}".format(key)
                ep_key_list.append(comp_key)

                # If key is present in array of fields that are not percentages
                if key in setup_dict_value["non_percentage_fields"]:
                    # Do no calculations, just save value
                    pandas_df[comp_key] = pandas_df[value]
                # Else if key is not present in array of fields that are not percentages
                else:
                    # Calculate percentage of whole using total field defined in JSON and totals calculated in Line 70
                    pandas_df[comp_key] = ((pandas_df[e_key_list[est_list_iter]] / pandas_df[value]) * 100)

                # Iterate iterator
                est_list_iter += 1

            # Iterate over list of estimated percentage keys
            for value in ep_key_list:
                # Create and append a complete name for new EPL column using current EP name
                comp_name = "{0}L{1}".format(value[:2], value[2:])
                epl_key_list.append(comp_name)

                # Check if current value is in list of inverse percentile rank columns
                if value[3:] in setup_dict_value["inverse_fields"]:
                    # If it is, calculate 1 - percentile rank for current column
                    pandas_df[comp_name] = 1 - pandas_df[value].rank(pct=True)
                else:
                    # If it is not, calculate percentile rank as normal
                    pandas_df[comp_name] = pandas_df[value].rank(pct = True)

            # Create total of epl column
            prcnt_total_name = r"SPL_{}".format(setup_dict_key)
            pandas_df[prcnt_total_name] = pandas_df[ep_key_list].sum(axis = 1)

            # Calculate percent rank for percentages column to get SVI for current theme
            prcnt_rank_name = r"RPL_{}".format(setup_dict_key)
            pandas_df[prcnt_rank_name] = pandas_df[prcnt_total_name].rank(pct = True)

            # Create list of fields to append to subset
            theme_svi_list.append(prcnt_rank_name)
            field_list += e_key_list + ep_key_list + epl_key_list + [prcnt_rank_name]

    # Create total of theme svi columns
    theme_total_name = "SPL_{}".format(subset_key)
    pandas_df[theme_total_name] = pandas_df[theme_svi_list].sum(axis = 1)

    # Calculate SVI across all themes
    total_svi_name = "RPL_{}".format(subset_key)
    pandas_df[total_svi_name] = pandas_df[theme_total_name].rank(pct = True)

    # Select a subset of columns from pandas_csv
    columns = setup_dict["geoid_fields"] + field_list + [total_svi_name]
    subset = pandas_df.loc[:, columns]

    return subset, 1, 'No errors'


def join_table (output_path, table_name, input_feature_path, input_data_table, join_field):
    # Set ArcPy environment setting to use just field names and not table names
    arcpy.env.qualifiedFieldNames = False

    # Create complete path for output shapefile
    filename = r"{0}_{1}".format(table_name, os.path.split(input_feature_path)[1])
    path = os.path.join(output_path, os.path.splitext(filename)[0])
    comp_output_path = os.path.join(path, filename)

    # Create new directory to store shapefile elements in
    os.mkdir(path)

    # Join input table and input shapefile to create new temporary shapefile
    joined_table = arcpy.AddJoin_management(input_feature_path, join_field, input_data_table, join_field)

    # Copy features of temporary shapefile into permanent shapefile and store at generated path
    arcpy.CopyFeatures_management(joined_table, comp_output_path)

    return comp_output_path, 1, 'No errors'
