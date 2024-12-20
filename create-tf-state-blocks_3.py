#!/usr/bin/python3

import json
import sys

def generate_import_blocks(state_file, resources_file, output_file):
    """
    Generates Terraform import block statements from a state file and a list of resources.

    Args:
        state_file (str): Path to the Terraform state file.
        resources_file (str): Path to the file containing the list of resources to import.
        output_file (str): Path to the output file for the import block statements.
    """

    try:
        with open(state_file, 'r') as f:
            state_data = json.load(f)

        with open(resources_file, 'r') as f:
            required_resources = [line.strip() for line in f if line.strip()]

        import_blocks = []

        # Keep track of handled resources to avoid duplicates from modules with for_each
        handled_resources = set()

        for resource in state_data['resources']:
            resource_type = resource['type']
            resource_name = resource['name']
            module_prefix = resource.get('module', '')  # Get module prefix or empty string
            if module_prefix:
                module_prefix += "."
            resource_address = f"{module_prefix}{resource_type}.{resource_name}"

            if resource_address in required_resources and resource_address not in handled_resources:
                instances = resource['instances']
                for instance in instances:
                    attributes = instance['attributes']
                    if resource_type == "aws_security_group_rule":
                        import_id = generate_security_group_rule_id(attributes)
                    else:
                        import_id = attributes['id']

                    import_block = f"""
import {{
  to = {resource_address}
  id = "{import_id}"
}}
"""
                    import_blocks.append(import_block)
                    handled_resources.add(resource_address)  # Mark resource as handled

        with open(output_file, 'w') as f:
            f.writelines(import_blocks)

    except FileNotFoundError:
        print("Error: State file or resources file not found.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in the state file.")
    except KeyError as e:
        print(f"Error: Missing key in state file: {e}")


def generate_security_group_rule_id(attributes):
    """
    Generates the import ID for an aws_security_group_rule resource.

    Args:
        attributes (dict): Attributes of the security group rule.

    Returns:
        str: The import ID.
    """
    try:
        return "_".join([
            attributes['security_group_id'],
            attributes['type'],
            attributes['protocol'],
            str(attributes['from_port']),
            str(attributes['to_port']),
            ",".join(attributes['cidr_blocks']),
            ",".join(attributes['ipv6_cidr_blocks']),
            ",".join(attributes['prefix_list_ids']),
            attributes['description'],
            str(attributes['self']).lower(),
            attributes['source_security_group_id']
        ])
    except KeyError as e:
        print(f"Error: Missing key in security group rule attributes: {e}")
        return ""

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <state_file> <resources_file> <output_file>")
        sys.exit(1)

    state_file = sys.argv[1]
    resources_file = sys.argv[2]
    output_file = sys.argv[3]

    generate_import_blocks(state_file, resources_file, output_file)
