from typing import List, Any

from pydantic import BaseModel


class JAXParameter(BaseModel):
    symbol: str
    value: Any
    jax_type: str
    rule_match: str

class ParameterList(BaseModel):
    parameters: List[JAXParameter]

# Convert to a dict for your prompt or use the class directly for response_schema
req_struct = ParameterList.model_json_schema()