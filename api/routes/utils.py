from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def parse_option_date(symbol):
    # Find where the date part starts (first digit after letters)
    date_start = 0
    for i, char in enumerate(symbol):
        if char.isdigit():
            date_start = i
            break
    
    # Extract the date portion (always 6 digits: YYMMDD)
    date_portion = symbol[date_start:date_start+6]
    
    # Get month and date
    month = date_portion[2:4]  # 3rd and 4th characters
    date = date_portion[4:6]   # 5th and 6th characters
    
    return month, date

def check_option_expiry(month, date):
    # Get current date in ET
    current_et = datetime.now(ZoneInfo("America/New_York"))
    current_month = int(current_et.strftime("%m"))
    current_date = int(current_et.strftime("%d"))
    
    # Convert input month and date to integers
    option_month = int(month)
    option_date = int(date)
    
    print(f"Checking expiry - Current: {current_month}/{current_date}, Option: {option_month}/{option_date}")
    
    # Compare dates
    if current_month > option_month:
        # print("Option expired: Current month is later than option month")
        return False
    elif current_month < option_month:
        # print("Option valid: Current month is earlier than option month")
        return True
    else:  # Same month
        if current_date > option_date:
            # print("Option expired: Same month but current date is later")
            return False
        else:
            # print("Option valid: Same month and current date is not later")
            return True
