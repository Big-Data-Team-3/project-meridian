from secedgar import filings, FilingType, CompanyFilings, DailyFilings, QuarterlyFilings, ComboFilings
from secedgar.cik_lookup import get_cik_map
import json
from datetime import date
from models import CIKLimits

# region CIK Mapping
def get_cik_mapping(cik_limits: CIKLimits = CIKLimits()):
    if cik_limits.isCount:
        cik_map=dict(list(get_cik_map(user_agent="Example (email@example.com)")["ticker"].items())[:cik_limits.count])
    else:
        cik_map=dict(list(get_cik_map(user_agent="Example (email@example.com)")["ticker"].items()))
    return cik_map

def save_cik_mapping(cik_mapping: dict, file_path: str = "cik_mapping.json"):
    with open(file_path, "w") as f:
        json.dump(cik_mapping, f)

# endregion CIK Mapping

# region Filing Retrieval
def extract_daily_filings(date: date, user_agent: str = "SEC EDGAR Client (email@example.com)"):
    '''
    Get daily filings for a given date
    Args:
        date (date): date
        user_agent (str): user agent
    Returns:
        daily_filings (DailyFilings): daily filings
    '''
    daily_filings = filings(start_date=date,
                            end_date=date,
                            user_agent=user_agent)
    daily_filings.save(f"data/daily_filings/{date.strftime('%Y-%m-%d')}")
# endregion Filing Retrieval

if __name__ == "__main__":
    print("Getting CIK mapping...")
    cik_mapping = get_cik_mapping(CIKLimits(isCount=True, count=10))
    print("Saving CIK mapping to cik_mapping.json...")
    save_cik_mapping(cik_mapping, "cik_mapping.json")
    print("CIK mapping saved to cik_mapping.json")
    print("Getting daily filings for 2025-12-01...")
    daily_filings = extract_daily_filings(date(2025, 12, 1))
    print("Daily filings saved to data/daily_filings/2025-12-01")