from pydantic import BaseModel
class CIKLimits(BaseModel):
    isCount: bool = False
    count: int = 10