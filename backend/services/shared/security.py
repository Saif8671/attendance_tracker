import hashlib

def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()
