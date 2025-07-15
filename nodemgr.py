import configparser

CFG = "servers.cnf"

def load_nodes():
    config = configparser.ConfigParser()
    config.read(CFG)
    nodes = []
    for section in config.sections():
        d = dict(config[section])
        d["id"] = section
        nodes.append(d)
    return nodes

def add_node(id, host, db_user, db_password, ssh_user, ssh_password, datadir):
    config = configparser.ConfigParser()
    config.read(CFG)
    if id in config.sections():
        return False
    config[id] = {
        "host": host,
        "db_user": db_user,
        "db_password": db_password,
        "ssh_user": ssh_user,
        "ssh_password": ssh_password,
        "datadir": datadir
    }
    with open(CFG, "w") as f:
        config.write(f)
    return True

def edit_node(id, host, db_user, db_password, ssh_user, ssh_password, datadir):
    config = configparser.ConfigParser()
    config.read(CFG)
    if id not in config.sections():
        return False
    config[id] = {
        "host": host,
        "db_user": db_user,
        "db_password": db_password,
        "ssh_user": ssh_user,
        "ssh_password": ssh_password,
        "datadir": datadir
    }
    with open(CFG, "w") as f:
        config.write(f)
    return True

def delete_node(id):
    config = configparser.ConfigParser()
    config.read(CFG)
    if id not in config.sections():
        return False
    config.remove_section(id)
    with open(CFG, "w") as f:
        config.write(f)
    return True

def get_node(id):
    config = configparser.ConfigParser()
    config.read(CFG)
    if id not in config.sections():
        return None
    return dict(config[id])

