"""
relay -> module( store  -> field worker
guard -> collet runnable and bild pattern (todo outsrc creation -> possible deploy dozens paralell (locally) -> later)


"""
from typing import Any

from qbrain.core.module_manager.create_runnable import create_runnable


def generate_main_function(
        scheduled_methods: list[dict],
        initial_inputs: list[str],
        xtrn_mods:dict[str, Any],
) -> str:
    """
    Programmatically creates a Python function 'main' from the scheduled method order.
    The methods are called sequentially, passing outputs as inputs where needed.

    Args:
        scheduled_methods: List of method dictionaries in execution order.
        initial_inputs: List of keys that are provided as initial arguments to 'main'.

    Returns:
        str: A string containing the Python definition of the 'main' function.
    """

    # 1. Start defining the main function signature
    # Arguments are the initial inputs (like 'mass', 'vev', etc.)
    # We use a set for initial inputs to ensure uniqueness and then sort for stable output.
    initial_args = sorted(list(set(initial_inputs)))

    # Function header: def main(input_a, input_b, ...):
    main_func_lines = [
        f"def main(*field_params):"
    ]

    # Set to track all variables (keys) available in the scope
    available_variables = set(initial_args)

    # List to store the final return keys
    final_returns = []

    # 2. Iterate through the scheduled methods and build the body
    for method_def in scheduled_methods:
        name = method_def['method_name']
        output_key = method_def.get('return_key')
        input_keys = method_def.get('parameters', [])

        # Check for missing variables (should not happen if scheduling was correct)
        if not set(input_keys).issubset(available_variables):
            # This should be handled, but for simplicity we assume the order is correct.
            raise ValueError(f"Scheduling error: Method {name} requires missing inputs.")

        # Format the call: output_key = method_name(input_1, input_2, ...)

        # 2a. Format the inputs for the call
        # We assume the called method exists in the same scope or is imported.
        call_inputs_str = ', '.join(input_keys)

        # 2b. Add the method call line
        if output_key:
            # Assign the result to the output variable name
            call_line = f"    {output_key} = {name}({call_inputs_str})"
            available_variables.add(output_key)
            final_returns.append(output_key)
        else:
            # If there is no return key (e.g., a function for logging/side effect)
            call_line = f"    {name}({call_inputs_str})"

        main_func_lines.append(call_line)

    # 3. Add the return statement
    # Return all intermediate calculated variables (the 'return_key' values)
    # If there are no calculated outputs, return the last output or None.
    if final_returns:
        return_line = f"    return {', '.join(final_returns)}"
    else:
        return_line = "    return None"

    main_func_lines.append(return_line)
    print("code string crated:", main_func_lines)
    # 4. Join all lines into the final program string
    return create_runnable(
        "\n".join(main_func_lines),
        eq_key="main",
        xtrn_mods=xtrn_mods
    )