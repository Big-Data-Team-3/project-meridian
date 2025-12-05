from pydantic import BaseModel

class YFinanceLimits(BaseModel):
    isCount: bool = False
    count: int = 10

class YFinanceData(BaseModel):
    ticker: str
    data: dict

class YFinanceStockData(BaseModel):
    ticker: str
    data: dict

class YFinanceETFData(BaseModel):
    ticker: str
    data: dict

class YFinanceIndexData(BaseModel):
    ticker: str
    data: dict