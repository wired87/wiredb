
def xtract_params_prompt(
        req_struct, instructions, content:str or bytes, user_params
):
    return f"""
You are a JAX data type specialist. Your task is to extract all parameters 
from the provided LaTeX content and classify them strictly according to the 
following scientific notation rules.

### INPUT DATA
Input structure: Raw document content (LaTeX/Markdown).
Required Output JSON structure:
{req_struct}

### CLASSIFICATION RULES (GOLD STANDARD):
1. Scalar Float (float):
   - Lower-case Greek letters (e.g., $\alpha, \beta, \rho, \phi, \sigma$).
   - Lower-case Latin letters ($x, y, z, t, f$) when numerical assignments are present.

2. Integer (int):
   - Typical indices and counting variables ($i, j, n, k, L, N, M$) when recognizable as integers.

3. Vector / Array (jnp.array):
   - Bold lower-case letters ($\mathbf{{v}}, \mathbf{{x}}$).
   - Variables with vector arrows ($\vec{{a}}, \vec{{E}}$) or underlines ($underline{{x}}$).

4. Matrix (jnp.array):
   - Upper-case Latin letters ($A, B, C$).
   - Bold upper-case letters ($\mathbf{{M}}, \mathbf{{K}}, \mathbf{{H}}$).
   - Often identifiable by double indices (e.g., $M_{{ij}}$).

5. Set / List (list):
   - Enumerations within curly braces {{1, 2, 3}}.

### TASK:
Create a JSON array that contains the following for each parameter found:

MARK:
if you find a param that already exists within the following struct (double entry), exclude it from your response.

If a value is not explicitly assigned in the text (e.g., only the formula exists), set "value": "null".
Return ONLY valid JSON.

### USER INSTRUCTIONS:
{instructions}

### USERS PARAMS
{user_params}

### INPUT CONTENT:
{content}
"""
