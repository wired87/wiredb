GRAPH_LINK_PROMPT = """
Extract all fields that INTERACT with each other in the given research text.

DEFINITION OF INTERACTION:
- Any term where multiple fields multiply.
- Derivative couplings.
- Gauge interactions.
- Yukawa terms.
- Scalar potential terms.
- Field-strength dependencies.
- Mixing or mass-mixing.

REQUIREMENTS:
- Return only FIELD NAMES (no parameters, no constants).
- Do not include derivatives as separate fields.
- Do not include indices.
- Remove duplicates.
- Include synthetic fields if they appear.

OUTPUT FORMAT (JSON):
{
  "graph_links": ["field1", "field2", ...]
}
"""
FULL_EXTRACTION_PROMPT = """
Perform a structured physics-paper extraction.

TASKS:

1) Equations
- Extract all equations.
- Convert to valid Python code.
- Format: 
  "equations": [ {"original": "...", "python": "..."} ]

2) Parameters
- Extract all physical parameters (masses, couplings, constants).
- Format:
  "parameters": [ {"name": "...", "type": "..."} ]

3) Center Field
- Identify the main field.
- Compare with allowed_fields (provided externally).
- If match, return matched name; else synthetic field.
- Format:
  "center_field": "<name>"

4) Graph Links
- Extract all interacting fields.
- Return unique field names only.
- Format:
  "graph_links": ["...", "..."]

Return final structured result as JSON.
"""
CENTER_FIELD_PROMPT = """
Identify the MAIN FIELD discussed in the provided research text.

YOU MUST:
1. Detect all fields: scalar, fermion, gauge, tensor, synthetic fields.
2. Determine which field is the central object of the analysis.
   Criteria:
   - Appears in key equations frequently.
   - Appears in mass, interaction, or kinetic terms.
   - Mentioned as "we study", "the model contains", "the field", etc.

3. Compare the inferred field name to the list 'allowed_fields'.
   Provided externally.

BEHAVIOR:
- If a match exists → return that canonical field name.
- If no match → return the inferred field name and treat it as synthetic.

OUTPUT FORMAT (JSON):
{
  "center_field": "<name>"
}
"""
PARAMETER_PROMPT = """
Extract ALL physical parameters from the provided research text.

DEFINITION OF PARAMETERS:
- Couplings (g, y, λ, κ, etc.)
- Mass terms (m, m_phi, m_psi, etc.)
- Charges, constants, mixing angles
- Cutoff scales, vacuum expectation values (vev)
- Anything declared as: "parameter", "constant", "coupling", "mass", "coefficient".

RULES:
- NO fields (psi, phi, A_mu, etc.) unless explicitly defined as constants.
- NO indices.
- Return each parameter with a short type description (1–4 words).
- Keep original symbol exactly.

OUTPUT FORMAT (JSON):
{
  "parameters": [
    { "name": "<symbol>", "type": "<short type description>" }
  ]
}
"""

EQUATION_PROMPT = """
Extract ALL mathematical equations from the provided research text.

REQUIREMENTS:
- Detect inline and block equations.
- Parse LaTeX, text equations, or mixed notation.
- Convert each extracted equation into valid Python code.
- Prefer sympy where structure matters (symbols, derivatives, Greek letters).
- Use simple python arithmetic when expressions are straightforward.
- Preserve indices by converting them into explicit symbol names:
  Example: A_mu -> A_mu, F_{mu,nu} -> F_mu_nu
- Ignore natural-language explanations.
- Do not drop terms.

OUTPUT FORMAT (JSON):
{
  "equations": [
    { "original": "<raw text>", "python": "<python code>" }
  ]
}
"""
