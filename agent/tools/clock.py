import time
import threading
import datetime

# alarms and timers storage
alarms = []
timers = []

def get_current_time():
    try:
        now = datetime.datetime.now()
        return f"The current time is {now.strftime('%I:%M:%S %p')}"
    except Exception as e:
        return f"[ERROR] Error getting current time: {str(e)}"

def set_alarm(hour, minute, objective=""):
    # Validate input BEFORE starting thread
    try:
        hour = int(hour)
        minute = int(minute)
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError("Hour must be 0-23 and minute must be 0-59")
    except (ValueError, TypeError) as e:
        return f"[ERROR] Invalid time format: {str(e)}"
    
    def alarm_thread():
        try:
            while True:
                now = datetime.datetime.now()
                if now.hour == hour and now.minute == minute:
                    print(f"🔔 Alarm: {objective or 'Wake up!'}")
                    break
                time.sleep(10)  # Check every 10 seconds
        except Exception as e:
            print(f"[ERROR] Error in alarm thread: {str(e)}")
    
    try:
        threading.Thread(target=alarm_thread, daemon=True).start()
        alarms.append({"hour": hour, "minute": minute, "objective": objective})
        return f"Alarm set for {hour:02d}:{minute:02d} — {objective}"
    except Exception as e:
        return f"[ERROR] Error starting alarm thread: {str(e)}"

def set_timer(seconds, objective=""):
    # Validate input BEFORE starting thread
    try:
        seconds = int(seconds)
        if seconds < 0:
            raise ValueError("Seconds must be a non-negative integer")
    except (ValueError, TypeError) as e:
        return f"[ERROR] Invalid seconds format: {str(e)}"
    
    if seconds == 0:
        print(f"Timer Done: {objective or 'Time is up!'}")
        return f"Timer completed immediately — {objective}"
    
    def timer_thread():
        try:
            time.sleep(seconds)
            print(f"Timer Done: {objective or 'Time is up!'}")
        except Exception as e:
            print(f"[ERROR] Error in timer thread: {str(e)}")
    
    try:
        threading.Thread(target=timer_thread, daemon=True).start()
        timers.append({"seconds": seconds, "objective": objective})
        return f"Timer set for {seconds} seconds — {objective}"
    except Exception as e:
        return f"[ERROR] Error setting timer: {str(e)}"

def get_active_alarms():
    """Returns list of currently set alarms"""
    if not alarms:
        return "No active alarms"
    return alarms

def get_active_timers():
    """Returns list of currently running timers (note: this is just what was set, not remaining time)"""
    if not timers:
        return "No active timers"
    return timers

def clear_alarms():
    """Clear all alarms"""
    global alarms
    alarms.clear()
    return "All alarms cleared"

def clear_timers():
    """Clear timers list (note: won't stop running timers, just clears the record)"""
    global timers
    timers.clear()
    return "Timer list cleared"

def clock(args: dict):
    cmd_type = args.get("type")
    
    if cmd_type == "get_time":
        return get_current_time()
    elif cmd_type == "alarm":
        return set_alarm(args.get("hour"), args.get("minute"), args.get("objective", ""))
    elif cmd_type == "timer":
        return set_timer(args.get("seconds"), args.get("objective", ""))
    elif cmd_type == "get_active_alarms":
        return f"Active alarms: {get_active_alarms()}"
    elif cmd_type == "get_active_timers":
        return f"Active timers: {get_active_timers()}"
    elif cmd_type == "clear_alarms":
        return clear_alarms()
    elif cmd_type == "clear_timers":
        return clear_timers()
    else:
        return "Unknown clock command. Available: get_time, alarm, timer, list_alarms, list_timers, clear_alarms, clear_timers"