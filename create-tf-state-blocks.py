#!/usr/bin/python3
import json
import argparse

def parse_tf_plan(plan_json_file):
    """
    Parses the extracted Terraform plan JSON file to extract resources.
    """
    with open(plan_json_file, 'r') as file:
        plan_data = json.load(file)

    plan_resources = []
    for resource in plan_data.get('resource_changes', []):
        resource_type = resource.get('type')
        resource_name = resource.get('name')
        if resource_type and resource_name:
            plan_resources.append({
                "type": resource_type,
                "name": resource_name,
            })
    return plan_resources

def parse_tf_state(state_file):
    """
    Parses the Terraform state file to extract resources.
    """
    with open(state_file, 'r') as file:
        state_data = json.load(file)

    state_resources = {}
    for resource in state_data.get('resources', []):
        resource_type = resource.get('type')
        resource_name = resource.get('name')
        for instance in resource.get('instances', []):
            instance_id = instance.get('attributes', {}).get('id')
            if resource_type and resource_name and instance_id:
                key = f"{resource_type}.{resource_name}"
                state_resources[key] = instance_id
    return state_resources

def find_resources_in_state(state_data, modules):
    resources_to_import = []
    excluded_types = {"aws_autoscaling_attachment"}  # Example of excluded resource types

    for resource in state_data.get("resources", []):
        mode = resource.get("mode", "managed")  # Default mode is "managed"
        if mode != "managed":
            continue  # Skip data resources

        if resource.get("type") in excluded_types:
            continue  # Skip excluded resource types

        resource_namespace = resource.get("module", "")  # Module namespace if exists
        resource_type = resource.get("type")
        resource_name = resource.get("name")
        
        # Combine type and name to create the resource's identifier
        type_name = f"{resource_type}.{resource_name}"

        # Check if the resource matches any of the specified modules
        is_matching_module = any(
            module in type_name or (resource_namespace and resource_namespace.startswith(module))
            for module in modules
        )

        if not is_matching_module:
            continue

        # Process each instance of the resource
        for index, instance in enumerate(resource.get("instances", [])):
            index_key = instance.get("index_key")  # Retrieve the optional index_key
            attributes = instance.get("attributes", {})
            resource_id = attributes.get("id")

            # Special handling for certain resource types
            if resource_type == "aws_iam_role_policy_attachment":
                role = attributes.get("role")
                policy_arn = attributes.get("policy_arn")
                resource_id = f"{role}/{policy_arn}"
            elif resource_type == "aws_security_group_rule":
                security_group_id = attributes.get("security_group_id")
                rule_type = attributes.get("type")
                protocol = attributes.get("protocol")
                from_port = attributes.get("from_port")
                to_port = attributes.get("to_port")
                cidr_blocks = attributes.get("cidr_blocks", [])
                source_security_group_id = attributes.get("source_security_group_id", "")

                # Construct ID format
                if source_security_group_id:
                    resource_id = f"{security_group_id}_{rule_type}_{protocol}_{from_port}_{to_port}_self_{source_security_group_id}"
                else:
                    cidr_blocks_str = "_".join(cidr_blocks) if cidr_blocks else "_"
                    resource_id = f"{security_group_id}_{rule_type}_{protocol}_{from_port}_{to_port}_{cidr_blocks_str}"

            # Construct full resource name
            full_name = f"{resource_namespace}.{resource_type}[\"{index_key}\"]" if index_key else f"{resource_namespace}.{resource_type}.{resource_name}"

            # Add resource to the list
            resources_to_import.append({
                "name": full_name.strip("."),
                "id": resource_id,
            })

    return resources_to_import

def generate_import_blocks(resources):
    blocks = []
    for resource in resources:
        if resource["id"]:
            block = f"import {{\n  address = \"{resource['name']}\"\n  id      = \"{resource['id']}\"\n}}\n"
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

def main():
    parser = argparse.ArgumentParser(description="Generate Terraform import blocks from a state file and modules list.")
    parser.add_argument("--state-file", required=True, help="Path to the Terraform state file.")
    parser.add_argument("--modules-file", required=True, help="Path to the modules list file.")
    parser.add_argument("--output-file", required=True, help="Path to the output file for Terraform import blocks.")
    args = parser.parse_args()

    with open(args.modules_file, 'r') as file:
        modules_list = [line.strip() for line in file if line.strip()]

    state_data = parse_tf_state(args.state_file)
    resources = find_resources_in_state(state_data, modules_list)

    if not resources:
        print("No matching resources found in the state file for the provided modules list.")
        exit(0)

    blocks = generate_import_blocks(resources)

    if blocks:
        write_output_file(blocks, args.output_file)
    else:
        print("No import blocks to generate.")

if __name__ == "__main__":
    main()

