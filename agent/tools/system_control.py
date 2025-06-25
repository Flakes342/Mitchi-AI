import os
import sys
import psutil
import platform
import subprocess
import threading
import time
from datetime import datetime, timedelta

def get_system_info():
    """Get comprehensive system information"""
    try:
        info = {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": round(psutil.virtual_memory().total / (1024**3), 2),
                "available": round(psutil.virtual_memory().available / (1024**3), 2),
                "percent": psutil.virtual_memory().percent,
                "used": round(psutil.virtual_memory().used / (1024**3), 2)
            },
            "disk": {
                "total": round(psutil.disk_usage('/').total / (1024**3), 2),
                "used": round(psutil.disk_usage('/').used / (1024**3), 2),
                "free": round(psutil.disk_usage('/').free / (1024**3), 2),
                "percent": psutil.disk_usage('/').percent
            }
        }

        output = f""" 
                System Information: \n
                • OS: {info['system']} {info['release']} \n
                • Machine: {info['machine']} | Processor: {info['processor']} \n
                • Node: {info['node']} \n

                ⚡ Performance: \n
                • CPU Cores: {info['cpu_count']} | Usage: {info['cpu_percent']}% \n
                • RAM: {info['memory']['used']}GB / {info['memory']['total']}GB ({info['memory']['percent']}%) \n
                • Disk: {info['disk']['used']}GB / {info['disk']['total']}GB ({info['disk']['percent']}%)
                """.strip()
        
        return output
        
    except Exception as e:
        return f"[ERROR] Failed to get system info: {str(e)}"

def get_running_processes():
    """List running processes"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sorting by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
        
        output = "Top Processes (by CPU usage):\n"
        for i, proc in enumerate(processes[:10]):
            cpu = proc['cpu_percent'] or 0
            mem = proc['memory_percent'] or 0
            output += f"{i+1:2d}. {proc['name']:<20} | PID: {proc['pid']:<8} | CPU: {cpu:5.1f}% | MEM: {mem:5.1f}%\n"
        
        return output
        
    except Exception as e:
        return f"[ERROR] Failed to get processes: {str(e)}"

def kill_process(pid):
    """Kill process by PID or name"""
    try:
        killed = []
        
        # Try as PID first
        try:
            pid = int(pid)
            proc = psutil.Process(pid)
            proc_name = proc.name()
            proc.terminate()
            proc.wait(timeout=5)
            killed.append(f"{proc_name} (PID: {pid})")
        except psutil.NoSuchProcess:
            return f"[ERROR] Process with PID {pid} not found"
        except psutil.AccessDenied:
            return f"[ERROR] Access denied to kill process {pid}"
        except ValueError:
            return f"[ERROR] Invalid PID format: {pid}"
        except Exception as e:
            return f"[ERROR] Failed to kill process {pid}: {str(e)}"
        
        if killed:
            return f"Killed processes: {', '.join(killed)}"
        else:
            return f"[ERROR] No processes found matching '{pid}'"
            
    except Exception as e:
        return f"[ERROR] Failed to kill process: {str(e)}"

def immediate_action(action):
    """Immediate shutdown/restart/logout"""
    try:
        if action == "shutdown":
            os.system("sudo shutdown -h now")
            return "Shutting down immediately..."
        elif action == "restart":
            os.system("sudo reboot")
            return "Restarting immediately..."
        elif action == "logout":
            os.system("pkill -KILL -u $USER")
            return "Logging out..."
        elif action == "sleep":
            os.system("sudo systemctl suspend")
            return "Going to sleep..."
        elif action == "hibernate":
            os.system("sudo systemctl hibernate")
            return "Hibernating..."
        else:
            return "[ERROR] Unknown action. I can shutdown, restart, logout, sleep, hibernate"
    except Exception as e:
        return f"[ERROR] Failed to perform {action}: {str(e)}"

def get_system_temperature():
    """Get system temperature sensors"""
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return "No temperature sensors detected"
        
        output = "System Temperature:\n"
        for name, entries in temps.items():
            output += f"\n{name}:\n"
            for entry in entries:
                temp_c = entry.current
                output += f"  {entry.label or 'Sensor'}: {temp_c:.1f}°C\n"
        
        return output.strip()
        
    except Exception as e:
        return f"[ERROR] Failed to get temperature: {str(e)}"

def control_volume(action, value=None):
    """Control system volume"""
    try:
        if action == "get":
            # Get current volume
            result = subprocess.run(["amixer", "get", "Master"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Parsing volume from amixer output
                lines = result.stdout.split('\n')
                for line in lines:
                    if '[' in line and '%' in line:
                        volume = line.split('[')[1].split('%')[0]
                        muted = '[off]' in line
                        status = "Muted" if muted else "Unmuted"
                        return f"Volume: {volume}% ({status})"
            return "Volume: Unable to detect"

        elif action == "set":
            if value is None:
                return "[ERROR] Please specify volume level (0-100)"
            try:
                vol = int(value)
                if not 0 <= vol <= 100:
                    return "[ERROR] Volume must be between 0-100"
            except ValueError:
                return "[ERROR] Volume must be a number"

            
            result1 = subprocess.run(["amixer", "set", "Master", "unmute"], capture_output=True, text=True, timeout=10)
            if result1.returncode == 0:
                result2 = subprocess.run(["amixer", "set", "Master", f"{vol}%"], capture_output=True, text=True, timeout=10)
                if result2.returncode == 0:
                    return f"Volume set to {vol}%"
                else:
                    return f"[ERROR] Failed to set volume: {result.stderr}"
            else:
                return f"[ERROR] Failed to unmute before setting volume: {result1.stderr}"
                
        elif action == "mute":
            result = subprocess.run(["amixer", "set", "Master", "mute"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return "Volume muted"
            else:
                return f"[ERROR] Failed to mute: {result.stderr}"
                
        elif action == "unmute":
            result = subprocess.run(["amixer", "set", "Master", "unmute"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return "Volume unmuted"
            else:
                return f"[ERROR] Failed to unmute: {result.stderr}"
                
        elif action == "up":
            amount = value or "5"
            result1 = subprocess.run(["amixer", "set", "Master", "unmute"], capture_output=True, text=True, timeout=10)
            if result1.returncode == 0:
                result2 = subprocess.run(["amixer", "set", "Master", f"{amount}%+"], capture_output=True, text=True, timeout=10)
                if result2.returncode == 0:
                    return f"Volume increased by {amount}%"
                else:
                    return f"[ERROR] Failed to increase volume: {result.stderr}"
            else:
                return f"[ERROR] Failed to unmute before increasing volume: {result1.stderr}"
                
        elif action == "down":
            amount = value or "5"
            result1 = subprocess.run(["amixer", "set", "Master", "unmute"], capture_output=True, text=True, timeout=10)
            if result1.returncode == 0:
                result2 = subprocess.run(["amixer", "set", "Master", f"{amount}%-"], capture_output=True, text=True, timeout=10)
                if result2.returncode == 0:
                    return f"Volume decreased by {amount}%"
                else:
                    return f"[ERROR] Failed to decrease volume: {result.stderr}"
            else:
                return f"[ERROR] Failed to unmute before decreasing volume: {result1.stderr}"
        else:
            return "[ERROR] Unknown volume action. Use: get, set, mute, unmute, up, down"
            
    except Exception as e:
        return f"[ERROR] Volume control failed: {str(e)}"



def system_control(args: dict):
    """Main system control function"""
    cmd_type = args.get("type")
    
    if cmd_type == "get_system_info":
        return get_system_info()

    elif cmd_type == "processes":
        return get_running_processes()

    elif cmd_type == "kill_process":
        pid = args.get("process", "")
        if not pid:
            return "[ERROR] Please specify process PID"
        return kill_process(pid)

    elif cmd_type == "immediate_action":
        action = args.get("action")
        return immediate_action(action)

    elif cmd_type == "get_system_temperature":
        return get_system_temperature()

    elif cmd_type == "volume":
        action = args.get("action", "get")
        value = args.get("value")
        return control_volume(action, value)

    # elif cmd_type == "brightness":
    #     action = args.get("action", "get")
    #     value = args.get("value")
    #     return control_brightness(action, value)

    # elif cmd_type == "media":
    #     action = args.get("action", "status")
    #     return control_media(action)

    else:
        return """[ERROR] Unknown system control command. Please specify a valid type.
        """