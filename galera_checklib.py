import os
import json
import paramiko
import pymysql
from datetime import datetime

EVENTS_LOG = "node_events.log"
STATE_CACHE = "node_state_cache.json"

def log_node_event(node_label, ip, down_time=None, up_time=None):
    event = {
        "node_label": node_label,
        "ip": ip,
        "down_time": down_time,
        "up_time": up_time
    }
    with open(EVENTS_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")

def get_node_events():
    if not os.path.exists(EVENTS_LOG):
        return []
    events = []
    with open(EVENTS_LOG, "r") as f:
        for line in f:
            try:
                event = json.loads(line)
                # Calcula duración si existe
                if "down_time" in event and event.get("up_time"):
                    fmt = "%Y-%m-%d %H:%M:%S"
                    try:
                        down = datetime.strptime(event["down_time"], fmt)
                        up = datetime.strptime(event["up_time"], fmt)
                        duration = up - down
                        seconds = int(duration.total_seconds())
                        hours = seconds // 3600
                        minutes = (seconds % 3600) // 60
                        seconds = seconds % 60
                        event["duration_str"] = f"{hours}h {minutes}m {seconds}s"
                    except Exception:
                        event["duration_str"] = "-"
                else:
                    event["duration_str"] = "-"
                events.append(event)
            except Exception:
                continue
    # Opcional: mostrar el más reciente arriba
    events = sorted(events, key=lambda e: (e.get("down_time") or "") + (e.get("up_time") or ""), reverse=True)
    return events

def get_state_cache():
    if os.path.exists(STATE_CACHE):
        with open(STATE_CACHE, "r") as f:
            return json.load(f)
    return {}

def save_state_cache(cache):
    with open(STATE_CACHE, "w") as f:
        json.dump(cache, f)

def ssh_run_cmd(host, user, password, cmd):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=password, timeout=8)
        stdin, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode().strip()
        client.close()
        return output
    except Exception as e:
        return f"SSH Error: {e}"

def get_db_status(cfg):
    try:
        db = pymysql.connect(
            host=cfg['host'],
            user=cfg['db_user'],
            password=cfg['db_password'],
            connect_timeout=5
        )
        cur = db.cursor()
        cur.execute("SHOW STATUS LIKE 'wsrep_local_state_comment'")
        galera_state = cur.fetchone()
        galera_state = galera_state[1] if galera_state else "-"
        cur.execute("SHOW VARIABLES LIKE 'wsrep_on'")
        wsrep_on = cur.fetchone()
        wsrep_on = wsrep_on[1] if wsrep_on else "-"
        # Get users
        cur.execute("SELECT COUNT(*) FROM mysql.user")
        db_users = cur.fetchone()[0]
        # Get DB sizes
        sizes = {}
        if 'monitor_db' in cfg:
            dbs = [dbn.strip() for dbn in cfg['monitor_db'].split(",") if dbn.strip()]
            for dbn in dbs:
                cur.execute("""
                    SELECT ROUND(SUM(data_length + index_length)/1024/1024,2) as MB
                    FROM information_schema.tables WHERE table_schema=%s
                """, (dbn,))
                row = cur.fetchone()
                sizes[dbn] = (row[0] or 0)
        cur.close()
        db.close()
        return {
            "galera_state": galera_state,
            "wsrep_on": wsrep_on,
            "db_users": db_users,
            "db_sizes": sizes
        }
    except Exception as e:
        return {"error": str(e)}

def get_server_metrics(cfg):
    # SSH and get memory, disk, cpu
    try:
        out_mem = ssh_run_cmd(cfg['host'], cfg['ssh_user'], cfg['ssh_password'],
                              "free -m | awk '/Mem:/ {print $3,$2}'")
        used, total = out_mem.split()
        used, total = int(used), int(total)
        mem_str = f"{used}MB ({round(used/total*100,1)}%)"
    except:
        mem_str = "-"
    try:
        out_disk = ssh_run_cmd(cfg['host'], cfg['ssh_user'], cfg['ssh_password'],
                               "df -h --output=avail,pcent / | tail -1")
        disk_avail, disk_used = out_disk.strip().split()
        disk_str = f"{disk_avail} free ({disk_used} used)"
    except:
        disk_str = "-"
    try:
        # Promedio de 1 minuto de CPU, en %
        out_cpu = ssh_run_cmd(cfg['host'], cfg['ssh_user'], cfg['ssh_password'],
                              "top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'")
        cpu_pct = round(float(out_cpu.strip()),1)
        cpu_str = f"{cpu_pct}%"
    except:
        cpu_str = "-"
    return mem_str, cpu_str, disk_str

def get_cluster_status(configs):
    state_cache = get_state_cache()
    nodes = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for idx, cfg in enumerate(configs):
        node_label = cfg.get("node_label", f"N{idx+1}")
        ip = cfg.get("host")
        # Defaults
        status = "Problem"
        galera_state = "-"
        wsrep_on = "-"
        db_users = "-"
        db_sizes = "-"
        problems = []
        # Get DB status
        dbstat = get_db_status(cfg)
        if "error" in dbstat:
            problems.append(f"SQL: {dbstat['error']}")
        else:
            galera_state = dbstat.get("galera_state", "-")
            wsrep_on = dbstat.get("wsrep_on", "-")
            db_users = dbstat.get("db_users", "-")
            if 'db_sizes' in dbstat:
                db_sizes = "\n".join(f"{k}: {v} MB" for k,v in dbstat['db_sizes'].items())
            else:
                db_sizes = "-"
        # Health logic
        if galera_state == "Synced" and wsrep_on.upper() == "ON" and not problems:
            status = "OK"
            problems = ["No problems detected"]
        else:
            if wsrep_on.upper() != "ON":
                problems.append("wsrep_on is OFF")
            if galera_state != "Synced":
                problems.append(f"Galera state is {galera_state}")
        # Get system metrics
        memory, cpu, disk = get_server_metrics(cfg)
        # --- Eventos de Nodo
        prev = state_cache.get(ip, {"status": None, "last_down": None})
        prev_status = prev.get("status")
        if prev_status != status:
            if status == "Problem":
                # Nodo cayó
                log_node_event(node_label, ip, down_time=now_str)
                state_cache[ip] = {"status": status, "last_down": now_str}
            elif status == "OK" and prev_status == "Problem":
                # Nodo se recuperó
                log_node_event(node_label, ip, down_time=prev.get("last_down"), up_time=now_str)
                state_cache[ip] = {"status": status, "last_down": None}
            else:
                state_cache[ip] = {"status": status, "last_down": prev.get("last_down")}
        else:
            # No cambió el estado
            state_cache[ip] = {"status": status, "last_down": prev.get("last_down")}
        node = {
            "node_label": node_label,
            "ip": ip,
            "status": status,
            "galera_state": galera_state,
            "wsrep_on": wsrep_on,
            "db_users": db_users,
            "db_sizes": db_sizes,
            "memory": memory,
            "cpu": cpu,
            "disk": disk,
            "problems": "; ".join(problems)
        }
        nodes.append(node)
    save_state_cache(state_cache)
    return nodes

def repair_node(node_label, configs):
    """
    Intenta reparar el nodo identificado por node_label.
    Devuelve (ok, msg)
    """
    for cfg in configs:
        if cfg.get("node_label") == node_label or cfg.get("host") == node_label:
            try:
                resp = ssh_run_cmd(cfg['host'], cfg['ssh_user'], cfg['ssh_password'],
                                   "sudo systemctl restart mariadb")
                return True, f"Repair command executed: {resp}"
            except Exception as e:
                return False, f"Repair failed: {e}"
    return False, f"Node {node_label} not found."

