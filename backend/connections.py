# connections.py — in-memory log of active HTTP clients
# Each entry is keyed by IP address and updated on every request via
# main.py's before_request hook.  Stale entries are pruned lazily when
# get_all() is called, so no background cleanup thread is needed.

import ipaddress
import threading
from datetime import datetime, timedelta

_lock = threading.Lock()
_sessions = {}          # ip -> session dict
TIMEOUT = 60            # seconds with no request before a client is considered gone


def record(ip, user=None):
    """Create or refresh the session entry for *ip*.  Updates the username
    if one is now known (e.g. after a successful login on that IP)."""
    with _lock:
        now = datetime.now().isoformat()
        if ip in _sessions:
            _sessions[ip]["last_seen"] = now
            if user:
                _sessions[ip]["user"] = user
        else:
            _sessions[ip] = {
                "ip":         ip,
                "user":       user,
                "first_seen": now,
                "last_seen":  now,
                "is_private": _classify(ip),  # LAN or WAN badge
            }


def get_all():
    """Return all active sessions sorted by most-recently-seen.
    Entries that have been quiet for longer than TIMEOUT are removed first."""
    with _lock:
        cutoff = datetime.now() - timedelta(seconds=TIMEOUT)
        # Collect stale keys before mutating the dict
        stale = [ip for ip, s in _sessions.items()
                 if datetime.fromisoformat(s["last_seen"]) < cutoff]
        for ip in stale:
            del _sessions[ip]
        return sorted(_sessions.values(), key=lambda x: x["last_seen"], reverse=True)


def _classify(ip):
    """Return 'LAN' for private/loopback addresses, 'WAN' for everything else."""
    try:
        addr = ipaddress.ip_address(ip)
        return "LAN" if (addr.is_private or addr.is_loopback) else "WAN"
    except ValueError:
        return "LAN"
