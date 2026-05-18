import logging
import socket

from ..config import settings

logger = logging.getLogger(__name__)


def _send(command: str) -> bool:
    host = settings.ami_host
    port = settings.ami_port
    user = settings.ami_user
    password = settings.ami_password
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, port))
            s.recv(1024)
            s.send(f"Action: Login\r\nUsername: {user}\r\nSecret: {password}\r\n\r\n".encode())
            s.recv(1024)
            s.send(f"Action: Command\r\nCommand: {command}\r\n\r\n".encode())
            s.recv(4096)
            s.send(b"Action: Logoff\r\n\r\n")
        logger.info(f"AMI reload OK: {command}")
        return True
    except Exception as e:
        logger.warning(f"AMI reload failed ({command}): {e}")
        return False


def _db_action(action: str, family: str, key: str, val: str = "") -> bool:
    host = settings.ami_host
    port = settings.ami_port
    user = settings.ami_user
    password = settings.ami_password
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, port))
            s.recv(1024)
            s.send(f"Action: Login\r\nUsername: {user}\r\nSecret: {password}\r\n\r\n".encode())
            s.recv(1024)
            if action == "put":
                cmd = f"Action: DBPut\r\nFamily: {family}\r\nKey: {key}\r\nVal: {val}\r\n\r\n"
            else:
                cmd = f"Action: DBDel\r\nFamily: {family}\r\nKey: {key}\r\n\r\n"
            s.send(cmd.encode())
            s.recv(4096)
            s.send(b"Action: Logoff\r\n\r\n")
        return True
    except Exception as e:
        logger.warning(f"AMI DB action failed: {e}")
        return False


def reload_pjsip():       return _send("module reload res_pjsip")
def reload_dialplan():    return _send("dialplan reload")
def reload_queues():      return _send("module reload app_queue")
def reload_voicemail():   return _send("module reload app_voicemail")
def reload_followme():    return _send("module reload app_followme")
def reload_musiconhold(): return _send("module reload res_musiconhold")
def reload_manager():     return _send("manager reload")
def reload_ari():         return _send("module reload res_ari")
def reload_cdr():         return _send("module reload cdr_mysql")

def blacklist_add(number: str):    return _db_action("put", "blacklist", number, "1")
def blacklist_remove(number: str): return _db_action("del", "blacklist", number)
