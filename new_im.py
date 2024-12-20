#!/usr/bin/python3
import json
import subprocess

def extract_plan_json(plan_file, output_file):
    """
    Extracts the Terraform plan JSON from a ZIP or plan file using `terraform show`.
    """
    try:
        with open(output_file, "w") as json_output:
            subprocess.run(["terraform", "show", "-json", plan_file], stdout=json_output, check=True)
        print(f"Terraform plan converted to JSON: {output_file}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error converting plan file to JSON: {e}")

def filter_resources(plan_json_file, resource_types=None, resource_names=None, actions=None):
    """
    Filters resources from the Terraform plan JSON based on type, name, and actions.
    """
    with open(plan_json_file, 'r') as file:
        plan_data = json.load(file)

    # Extract resource changes
    resource_changes = plan_data.get('resource_changes', [])
    filtered_resources = []

    for resource in resource_changes:
        resource_type = resource.get('type')
        resource_name = resource.get('name')
        change_actions = resource.get('change', {}).get('actions', [])
        
        if resource_types and resource_type not in resource_types:
            continue
        if resource_names and resource_name not in resource_names:
            continue
        if actions and not any(action in actions for action in change_actions):
            continue

        filtered_resources.append({
            "type": resource_type,
            "name": resource_name,
            "actions": change_actions,
        })

    return filtered_resources

def main(plan_file, output_json, resource_types=None, resource_names=None, actions=None):
    """
    Main function to process the plan file and extract filtered resources.
    """
    plan_json = "temp_plan.json"

    # Step 1: Convert plan to JSON
    extract_plan_json(plan_file, plan_json)

    # Step 2: Filter resources
    filtered_resources = filter_resources(plan_json, resource_types, resource_names, actions)

    # Step 3: Output filtered resources
    with open(output_json, 'w') as file:
        json.dump(filtered_resources, file, indent=4)

    print(f"Filtered resources written to '{output_json}'.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract specific resources from a Terraform plan.")
    parser.add_argument("--plan", required=True, help="Path to the Terraform plan ZIP or binary file.")
    parser.add_argument("--output", required=True, help="Path to the output JSON file for filtered resources.")
    parser.add_argument("--types", nargs="*", help="Filter by resource types (e.g., aws_instance, google_compute_instance).")
    parser.add_argument("--names", nargs="*", help="Filter by resource names (e.g., my_instance, db_server).")
    parser.add_argument("--actions", nargs="*", help="Filter by actions (e.g., create, update, delete).")

    args = parser.parse_args()
    main(args.plan, args.output, args.types, args.names, args.actions)

