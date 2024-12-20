import json
import subprocess


def extract_plan_json(plan_file, extracted_json_file):
    """
    Extracts the Terraform plan JSON from a ZIP or plan file using `terraform show`.
    """
    try:
        with open(extracted_json_file, "w") as json_output:
            subprocess.run(["terraform", "show", "-json", plan_file], stdout=json_output, check=True)
        print(f"Terraform plan converted to JSON: {extracted_json_file}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error converting plan file to JSON: {e}")


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


def generate_import_blocks(plan_resources, state_resources):
    """
    Generate Terraform import { ... } blocks for resources found in both the plan and state.
    """
    import_blocks = []

    for resource in plan_resources:
        resource_type = resource["type"]
        resource_name = resource["name"]
        key = f"{resource_type}.{resource_name}"

        if key in state_resources:
            instance_id = state_resources[key]
            block = generate_import_block(resource_type, resource_name, instance_id)
            import_blocks.append(block)
        else:
            print(f"Warning: Resource {key} not found in state file.")

    return import_blocks


def generate_import_block(resource_type, resource_name, instance_id):
    """
    Generate a single `import { ... }` block for a resource.
    """
    return f"""import {{
  address = "{resource_type}.{resource_name}"
  id      = "{instance_id}"
}}"""


def main(plan_file, state_file, output_file):
    """
    Main function to extract the plan, parse files, and generate `import { ... }` blocks.
    """
    extracted_json_file = "temp_plan.json"

    # Step 1: Convert plan to JSON
    try:
        extract_plan_json(plan_file, extracted_json_file)
    except Exception as e:
        print(f"Error processing the plan file: {e}")
        return

    # Step 2: Parse the plan and state files
    plan_resources = parse_tf_plan(extracted_json_file)
    state_resources = parse_tf_state(state_file)

    # Step 3: Generate import blocks
    import_blocks = generate_import_blocks(plan_resources, state_resources)

    # Step 4: Write the blocks to an output file
    with open(output_file, 'w') as file:
        file.write("\n\n".join(import_blocks))

    print(f"Terraform `import {}` blocks written to '{output_file}'.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Terraform `import {}` blocks from a plan and state file.")
    parser.add_argument("--plan", required=True, help="Path to the Terraform plan ZIP or binary file.")
    parser.add_argument("--state", required=True, help="Path to the Terraform state JSON file.")
    parser.add_argument("--output", required=True, help="Path to the output file for Terraform `import {}` blocks.")

    args = parser.parse_args()
    main(args.plan, args.state, args.output)

