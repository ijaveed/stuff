#!/usr/bin/python3
import argparse
import json

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate Terraform import blocks.")
    parser.add_argument("--state-file", required=True, help="Path to the Terraform state file.")
    parser.add_argument("--modules-file", required=True, help="Path to the modules list file.")
    parser.add_argument("--output-file", required=True, help="Path to the output file for Terraform import blocks.")
    return parser.parse_args()

def load_modules_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read().strip()
            if not content:
                raise ValueError("Modules file is empty.")
            return [line.strip() for line in content.splitlines() if line.strip()]
    except FileNotFoundError as e:
        print(f"Error: File not found - {file_path}")
        exit(1)
    except ValueError as e:
        print(f"Error: {e} - {file_path}")
        exit(1)

def load_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read().strip()
            if not content:
                raise ValueError("File is empty.")
            return json.loads(content)
    except FileNotFoundError as e:
        print(f"Error: File not found - {file_path}")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON in file {file_path}. Check the file format.")
        print(f"Details: {e}")
        exit(1)
    except ValueError as e:
        print(f"Error: {e} - {file_path}")
        exit(1)

def find_resources_in_state(state_data, modules):
    """
    Finds resources in the Terraform state file that match the provided modules list,
    including nested modules, and includes the full attribute path in the `to` value.
    """
    resources_to_import = []
    excluded_types = {"aws_autoscaling_attachment"}  # Example of excluded resource types

    def traverse_modules(resources, namespace=""):
        for resource in resources:
            mode = resource.get("mode", "managed")  # Default mode is "managed"
            if mode != "managed":
                print(f"Skipping data resource: {namespace}{resource.get('type')}.{resource.get('name')}")
                continue  # Skip data resources

            if resource.get("type") in excluded_types:
                print(f"Skipping excluded resource type: {namespace}{resource.get('type')}")
                continue  # Skip excluded resource types

            resource_namespace = f"{namespace}{resource.get('module', '')}"
            if resource_namespace:
                resource_namespace += "."

            resource_type = resource.get("type")
            resource_name = resource.get("name")
            type_name = f"{resource_type}.{resource_name}"

            print(f"Checking resource: {type_name} in namespace: {resource_namespace}")

            # Check if the resource matches any of the specified modules
            is_matching_module = any(
                module in type_name or resource_namespace.startswith(module)
                for module in modules
            )

            if not is_matching_module:
                print(f"Resource {type_name} does not match any modules in the list.")
                continue

            print(f"Matched resource: {type_name}")

            for index, instance in enumerate(resource.get("instances", [])):
                index_key = instance.get("index_key")  # Retrieve the optional index_key
                attributes = instance.get("attributes", {})
                resource_id = attributes.get("id")

                if not resource_id:
                    print(f"No ID found for resource: {type_name}")
                    continue

                # Handle deeply nested attribute paths
                for attribute, value in attributes.items():
                    # Skip non-leaf attributes (dicts or lists)
                    if isinstance(value, (dict, list)):
                        continue

                    # Construct the full attribute path
                    full_name = (
                        f"{resource_namespace}{resource_type}[\"{index_key}\"].{attribute}"
                        if index_key
                        else f"{resource_namespace}{resource_type}.{resource_name}.{attribute}"
                    )

                    print(f"Adding resource: {full_name} with ID: {resource_id}")

                    resources_to_import.append({
                        "name": full_name.strip("."),
                        "id": resource_id,
                    })

    # Start traversing from the top level
    traverse_modules(state_data.get("resources", []))
    return resources_to_import

def generate_import_blocks(resources):
    blocks = []
    for resource in resources:
        if resource["id"]:
            block = f"import {{\n  to = \"{resource['name']}\"\n  id      = \"{resource['id']}\"\n}}\n"
            blocks.append(block)
    return blocks

def write_output_file(blocks, output_file):
    try:
        with open(output_file, 'w') as file:
            file.writelines(blocks)
        print(f"Terraform import blocks written to {output_file}")
    except Exception as e:
        print(f"Error writing to output file {output_file}: {e}")
        exit(1)

if __name__ == "__main__":
    args = parse_arguments()

    state_data = load_json_file(args.state_file)
    modules_list = load_modules_file(args.modules_file)

    resources = find_resources_in_state(state_data, modules_list)

    if not resources:
        print("No matching resources found in the state file for the provided modules list.")
        exit(0)

    blocks = generate_import_blocks(resources)

    if blocks:
        write_output_file(blocks, args.output_file)
    else:
        print("No import blocks to generate.")

