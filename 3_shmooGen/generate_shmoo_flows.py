import csv
import os
import argparse
from datetime import datetime

def generate_shmoo_config(row):
    """Generate a shmoo flow configuration from a CSV row."""
    flow_name = row['Shmoo_flow_name']
    pattern_name = row['Pattern_Name']
    x_signal = row['X_signal']
    x_start = row['X_Voltage_Start']
    x_stop = row['X_Voltage_Stop']
    x_steps = row['X_Step']
    y_signal = row['Y_signal']
    y_start = row['Y_Voltage_Start']
    y_stop = row['Y_Voltage_Stop']
    y_steps = row['Y_Step']
    tracking_pattern = row['Tracking_Pattern']
    tracking_signal = row['Tracking_Signal']
    
    # Convert scientific notation to format like 20e-9
    y_start_formatted = f"{float(y_start):.0e}".replace("e-0", "e-")
    y_stop_formatted = f"{float(y_stop):.0e}".replace("e-0", "e-")
    
    # Construct the configuration string
    config = f"""shmoo {flow_name} {{
    target = {pattern_name}_NV;
    axis[X_axis] = {{
        resourceType  = specVariable;
        resourceName  = "Levels.DFT_Vtyp.DFT_Vtyp_specValue.{x_signal}";
        range.steps  = {x_steps};
        range.start  = {x_start};
        range.stop  = {x_stop};
    }};
    axis[Y_axis] = {{
        resourceType  = specVariable;
        resourceName = "Timings.debug_0517_m1.{pattern_name}.project_tim_specs.{y_signal}";
        range.steps  = {y_steps};
        range.start  = {y_start_formatted};
        range.stop  = {y_stop_formatted};
        tracking[temp]= {{
            resourceType  = specVariable;
            resourceName = "Timings.debug_0517_m1.{tracking_pattern}.project_tim_specs.{tracking_signal}";
            range.start  = {y_start_formatted};
            range.stop  = {y_stop_formatted};
        }};
    }};
}}
"""
    return config

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Generate shmoo flow configurations from a CSV file.")
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to the input CSV file (e.g., shmooinput.csv)"
    )
    args = parser.parse_args()
    
    # Input CSV file
    csv_file = args.input
    if not os.path.isfile(csv_file):
        print(f"Error: Input file '{csv_file}' does not exist.")
        return
    
    # Output directory
    output_dir = "shmoo_configs"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S CST")
    timestamp_file = datetime.now().strftime("%Y%m%d_%H%M")
    output_file = os.path.join(output_dir, f"shmoo_flows_{timestamp_file}.txt")
    
    # Read CSV and generate configurations
    configs = []
    try:
        with open(csv_file, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            # Strip whitespace from column names and handle BOM
            fieldnames = [name.strip() for name in reader.fieldnames]
            # Define required columns (underscore-separated)
            required_columns = [
                'Shmoo_flow_name', 'Pattern_Name', 'X_signal', 'X_Voltage_Start',
                'X_Voltage_Stop', 'X_Step', 'Y_signal', 'Y_Voltage_Start',
                'Y_Voltage_Stop', 'Y_Step', 'Tracking_Pattern', 'Tracking_Signal'
            ]
            # Check for missing columns
            missing_columns = [col for col in required_columns if col not in fieldnames]
            if missing_columns:
                print(f"Error: CSV file missing the following required columns: {missing_columns}")
                print(f"Actual CSV columns: {fieldnames}")
                print(f"Expected columns: {required_columns}")
                return
            # Update reader with stripped fieldnames
            reader.fieldnames = fieldnames
            for row in reader:
                config = generate_shmoo_config(row)
                configs.append(config)
                print(f"Processed configuration for {row['Shmoo_flow_name']}")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Write to single output file with timestamp
    with open(output_file, 'w') as out:
        out.write(f"# Generated on {timestamp}\n\n")
        out.write("\n\n".join(configs))
    
    print(f"All configurations written to {output_file}")

if __name__ == "__main__":
    main()