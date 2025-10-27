# sipcore/utils.py
import random
import string
from datetime import datetime, timezone

def gen_tag(n=8):
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))

def sip_date():
    # RFC 1123 date
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

