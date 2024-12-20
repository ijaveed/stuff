#!/usr/bin/python3
def find_resources_in_state(state_data, modules):
    resources_to_import = []
    excluded_types = {"aws_autoscaling_attachment"}  # Example of excluded resource types

    for resource in state_data.get("resources", []):
        mode = resource.get("mode", "managed")  # Default mode is "managed"
        if mode != "managed":
            print(f"Skipping data resource: {resource.get('type')}.{resource.get('name')}")
            continue  # Skip data resources

        if resource.get("type") in excluded_types:
            print(f"Skipping excluded resource type: {resource.get('type')}")
            continue  # Skip excluded resource types

        resource_namespace = resource.get("module", "")  # Module namespace if exists
        resource_type = resource.get("type")
        resource_name = resource.get("name")

        # Combine type and name to create the resource's identifier
        type_name = f"{resource_type}.{resource_name}"

        print(f"Checking resource: {type_name} in namespace: {resource_namespace}")

        # Check if the resource matches any of the specified modules
        is_matching_module = any(
            module in type_name or (resource_namespace and resource_namespace.startswith(module))
            for module in modules
        )

        if not is_matching_module:
            print(f"Resource {type_name} does not match any modules in the list.")
            continue

        print(f"Matched resource: {type_name}")

        # Process each instance of the resource
        for index, instance in enumerate(resource.get("instances", [])):
            index_key = instance.get("index_key")  # Retrieve the optional index_key
            attributes = instance.get("attributes", {})
            resource_id = attributes.get("id")

            if not resource_id:
                print(f"No ID found for resource: {type_name}")
                continue

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

            print(f"Adding resource: {full_name} with ID: {resource_id}")

            # Add resource to the list
            resources_to_import.append({
                "name": full_name.strip("."),
                "id": resource_id,
            })

    return resources_to_import

