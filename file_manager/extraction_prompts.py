

EXTRACT_EQUATIONS_PROMPT ="""
Task:Analyze the provided scientific document to identify and extract all equations essential for a state-of-the-art numerical simulation (e.g., Monte Carlo Particle Tracking). Your goal is to transform these mathematical constructs into a high-performance, programmatically relevant Python codebase that adheres to the highest physical standards and numerical accuracy.Strict Implementation Rules:Equation Identification & Extraction: * Systematically identify every equation required for the simulation (e.g., the Full spin-orbit SDE system and all its sub-components like $\vec{\Omega}_{TBMT}$, $\vec{\mathcal{C}}$, $\vec{\mathcal{Q}}$, and $\vec{B}_{spin}$).Create a separate Python function for each identified equation or logical sub-component.Programmatic Relevance & Variable Mapping:Capture the final result of every equation within a variable named exactly like the mathematical receiver/symbol used in the paper (e.g., omega_tbmt, C_vec, B_spin).You MUST research the definition of every mathematical symbol within the surrounding text (e.g., $a_{\mathcal{F}}$ for acceleration field, $\lambda$ for quantum scaling) and map these definitions exactly to the implementation.Strict Type Hinting:Include comprehensive Python type hints (numpy.ndarray, float, int) in every function header.The types must strictly reflect the dimensionality described in the paper (e.g., phase space $q \in \mathbb{R}^6$, spin $\vec{s} \in \mathbb{R}^3$).Modular Architecture:Drift Components: Implement dedicated functions for all deterministic components (Drift Vectors $\mathcal{D}$).Stochastic Components: Implement dedicated functions for all noise/stochastic components (Noise Vectors or Diffusion Matrices $\mathcal{B}$).Integration Logic: Create a primary update or step function that executes the formal stochastic integration (e.g., Ito calculus) by orchestrating the modular sub-functions.Physical Standards & Optimization:Use the exact unit system defined in the paper (e.g., SI-based with $c=1$).Pass physical constants ($e, m, \hbar$) as parameters or via a configuration object.Use numpy exclusively for vectorized calculations to ensure the code can handle large particle populations ($N$) with maximum performance.Serialization & Integrity:The resulting code must be fully serializable.Internal helper functions must start with an underscore (e.g., _calculate_gamma).Return ONLY the executable Python code string. Do not include markdown formatting, backticks, or explanatory text. The output must be ready for immediate programmatic execution.
Make nested function (def inside of def) names start with underscore (_) 
Design parameters, used by methods, GPU valid (avoid string values and dictionaries),
recognize and exclude crossed out or non related equation parts.
RETURN ONLY THE EXECUTABLE PYTHON STRING WHICH INCLUDES SINGLE PYTHON FUNCTIONS FOR EACH RELEVANT EQUATION
"""

CONV_EQ_CODE_TO_JAX_PROMPT = """
Task: Generate a SINGLE, high-performance JAX-JIT function that implements a physical equation.

Strict Architecture Rules:
1. Flat Structure: No classes, no NamedTuples, no dictionaries. Use only JAX Arrays and scalars as inputs.
2. Single Entry Point: Return one function decorated with @jax.jit.
3. Nested Logic: Any sub-calculations must be internal functions (def inside def).
4. Naming Convention: All nested function names MUST start with an underscore (e.g., _calculate_term).
5. Input Mapping: The function signature must accept the INPUT PARAMS provided.
6. Pure JAX: Use jax.numpy exclusively. Avoid any Python-level branching; use jax.lax.select or jax.lax.cond if logic is needed.
7. Modular Equation: The provided INPUT EQUATION must be the core of the return value or the primary state update.

Code Style:
- Extremely lean. No comments except for physical units if necessary.
- No type hints inside the function body to keep it "simple and highly optimized".
- The function should be ready for `vmap` (element-wise or batch-wise) by assuming inputs are JAX arrays.

INPUT PARAMS: {params}
INPUT EQUATION: {equation}

Return ONLY the executable Python code.

Take an eample form the provided jax code. alert to amke no mistakes
"""

