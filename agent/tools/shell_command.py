import subprocess
import logging
from agent.llm import text_to_shell_command

logger = logging.getLogger(__name__)

def run_shell_command(command: str) -> str:
    """Execute shell command with comprehensive error handling"""
    try:
        if not command or not command.strip():
            return "No command provided."
        
        command = command.strip()
        logger.info(f"Executing shell command: {command}")
        
        # Additional safety checks
        dangerous_commands = [
            "rm -rf /", ":(){ :|:& };:", "mkfs", "dd if=/dev/", 
            "chmod -R 777 /", "chown -R", "> /dev/", "cat /dev/urandom"
        ]
        
        if any(danger in command.lower() for danger in dangerous_commands):
            logger.warning(f"Blocked extremely dangerous command: {command}")
            return "Command blocked for safety reasons. This could damage your system."
        
        output = subprocess.check_output(
            command,
            shell=True,
            stderr=subprocess.STDOUT,
            timeout=10,
            text=True
        )
        
        result = f"Command executed successfully:\n{output.strip()}"
        logger.info(f"Command completed: {command}")
        return result
    
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed (exit code {e.returncode}):\n{e.output.strip()}"
        logger.warning(f"Command failed: {command} - {error_msg}")
        return error_msg
    
    except subprocess.TimeoutExpired:
        error_msg = "Command timed out after 10 seconds."
        logger.warning(f"Command timeout: {command}")
        return error_msg
    
    except FileNotFoundError:
        error_msg = "Command not found. Please check if the program is installed."
        logger.warning(f"Command not found: {command}")
        return error_msg
    
    except PermissionError:
        error_msg = "Permission denied. You may need to run this with sudo or check file permissions."
        logger.warning(f"Permission denied for command: {command}")
        return error_msg
    
    except Exception as e:
        error_msg = f"Unexpected error running command: {str(e)}"
        logger.error(f"Unexpected error with command {command}: {e}")
        return error_msg

        
def linux_commands(message: str):
    try:
        if not message or not message.strip():
            return "Please provide a command description."
        
        logger.info(f"Generating shell command for: {message}")
        
        # Generate shell command using LLM
        try:
            shell_cmd = text_to_shell_command(message)
        except Exception as e:
            logger.error(f"Failed to generate shell command: {e}")
            return "I couldn't understand what command you want me to run. Please be more specific."
        
        if not shell_cmd or shell_cmd.strip() == "":
            return "I couldn't generate a command for that request. Please be more specific."
        
        logger.info(f"Generated shell command: {shell_cmd}")

        # Enhanced safety checks
        risky_patterns = [
            "rm", "reboot", "shutdown", "mkfs", "dd", "format", 
            "fdisk", "parted", "wipefs", "shred", ">/dev/", 
            "chmod 777", "chown -R", "kill -9", "killall"
        ]
        
        if any(pattern in shell_cmd.lower() for pattern in risky_patterns):
            logger.warning(f"Risky command detected: {shell_cmd}")
            return (f"Potentially risky command detected: `{shell_cmd}`\n"
                   f"This command could modify important files or system settings. "
                   f"Please run it manually if you're sure it's safe.")

        # Execute the command
        result = run_shell_command(shell_cmd)
        return result
        
    except Exception as e:
        logger.error(f"Error in linux_commands: {e}")
        return "I encountered an error processing your command request. Please try again."

