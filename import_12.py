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
    resources_to_import = []
    excluded_types = {"aws_autoscaling_attachment"}  # aws_security_group_rule included back

    for resource in state_data.get("resources", []):
        mode = resource.get("mode", "managed")  # Default mode is "managed"
        if mode != "managed":
            continue  # Skip data resources

        if resource.get("type") in excluded_types:
            continue  # Skip excluded resource types

        resource_namespace = resource.get("module", "")

        # Process only resources belonging to the listed modules/namespaces
        if not any(resource_namespace.startswith(m) or resource["type"].startswith(m) for m in modules):
            continue

        if resource_namespace:
            resource_namespace = resource_namespace + "."
        resource_name = resource.get("name")

        for index, instance in enumerate(resource.get("instances", [])):
            index_key = instance.get("index_key")  # Retrieve the optional index_key
            if index_key:
                # Use indexed rule name
                full_name = f"{resource_namespace}{resource['type']}[\"{index_key}\"]"
            else:
                # Use rule name directly
                full_name = f"{resource_namespace}{resource_name}"

            # Special case for aws_iam_role_policy_attachment to use 'role/policy_arn' as id
            attributes = instance.get("attributes", {})
            resource_id = attributes.get("id")
            if resource.get("type") == "aws_iam_role_policy_attachment":
                role = attributes.get("role")
                policy_arn = attributes.get("policy_arn")
                resource_id = f"{role}/{policy_arn}"
            # Special case for aws_security_group_rule to format id properly
            elif resource.get("type") == "aws_security_group_rule":
                security_group_id = attributes.get("security_group_id")
                rule_type = attributes.get("type")  # ingress or egress
                protocol = attributes.get("protocol")
                from_port = attributes.get("from_port")
                to_port = attributes.get("to_port")
                cidr_blocks = attributes.get("cidr_blocks", [])
                source_security_group_id = attributes.get("source_security_group_id", "")

                # Handle source_security_group_id imports
                if source_security_group_id:
                    resource_id = f"{security_group_id}_{rule_type}_{protocol}_{from_port}_{to_port}_self_{source_security_group_id}"
                    resources_to_import.append({
                        "name": full_name,
                        "id": resource_id,
                    })

                # Handle cidr_blocks imports separately
                for cidr in cidr_blocks:
                    resource_id = f"{security_group_id}_{rule_type}_{protocol}_{from_port}_{to_port}_{cidr}"
                    resources_to_import.append({
                        "name": full_name,
                        "id": resource_id,
                    })

    return resources_to_import

def generate_import_blocks(resources):
    blocks = []
    for resource in resources:
        if resource["id"]:
            block = f"import {{\n  to = {resource['name']}\n  id = \"{resource['id']}\"\n}}\n"
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

