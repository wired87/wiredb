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


"""
