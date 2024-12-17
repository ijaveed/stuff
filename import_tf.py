import argparse
import json
import subprocess

def parse_arguments():
    parser = argparse.ArgumentParser(description="Terraform resource importer.")
    parser.add_argument("--state-file", required=True, help="Path to the Terraform state file.")
    parser.add_argument("--modules-file", required=True, help="Path to the modules list file.")
    parser.add_argument("--dry-run", action="store_true", help="Enable dry-run mode to preview commands.")
    return parser.parse_args()

def load_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading file {file_path}: {e}")
        exit(1)

def find_resources_in_state(state_data, modules):
    resources_to_import = []

    for resource in state_data.get("resources", []):
        module_name = resource.get("module")
        if module_name and module_name in modules:
            for instance in resource.get("instances", []):
                resources_to_import.append({
                    "module": module_name,
                    "type": resource.get("type"),
                    "name": resource.get("name"),
                    "id": instance.get("attributes", {}).get("id"),
                })
    
    return resources_to_import

def generate_import_commands(resources):
    commands = []
    for resource in resources:
        if resource["id"]:
            address = f"{resource['module']}.{resource['type']}.{resource['name']}"
            command = f"terraform import {address} {resource['id']}"
            commands.append(command)
    return commands

def execute_commands(commands, dry_run):
    for command in commands:
        if dry_run:
            print(f"[DRY-RUN] Command: {command}")
        else:
            print(f"Executing: {command}")
            result = subprocess.run(command, shell=True)
            if result.returncode != 0:
                print(f"Command failed: {command}")

if __name__ == "__main__":
    args = parse_arguments()

    state_data = load_json_file(args.state_file)
    modules_list = load_json_file(args.modules_file)

    resources = find_resources_in_state(state_data, modules_list)

    if not resources:
        print("No matching resources found in the state file for the provided modules list.")
        exit(0)

    commands = generate_import_commands(resources)

    if commands:
        execute_commands(commands, args.dry_run)
    else:
        print("No import commands to execute.")



