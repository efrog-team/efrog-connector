from datetime import datetime
from fastapi import HTTPException
from ntplib import NTPClient

def convert_and_validate_datetime(date: str, field_name: str = "") -> datetime:
    try:
        return datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    except:
        raise HTTPException(status_code=400, detail=f"{field_name if field_name != '' else 'Datetime'} either has an invalid format or is invalid itself")

def get_current_unix_time() -> int:
    for _ in range(0, 10):
        try:
            return int(NTPClient().request('pool.ntp.org').tx_time)
        except:
            pass
    raise HTTPException(status_code=500, detail="Internal Server Error")

def get_current_utc_datetime() -> datetime:
    return datetime.fromtimestamp(float(get_current_unix_time()))