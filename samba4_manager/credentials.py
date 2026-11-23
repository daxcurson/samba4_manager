"""Per-session storage of the Samba credentials typed at login.

The application talks to Samba with the credentials of the person using it,
so it has to keep them between requests. They are kept here, in the server's
memory only:

* each login gets its own random token, which is the only thing stored in
  the browser (inside the signed session cookie);
* entries expire after a period of inactivity;
* nothing is written to disk, so restarting the application logs everyone
  out.

Because the store lives in process memory, the application must run as a
single process (any number of threads is fine), as waitress does.
"""
import secrets
import threading
import time


class StoredCredentials(object):
    """Credentials of one logged-in user."""

    __slots__ = ('username', 'password', 'last_used')

    def __init__(self, username, password, now):
        self.username = username
        self.password = password
        self.last_used = now

    def __repr__(self):
        # Never show the password, e.g. in tracebacks or debug output.
        return '<StoredCredentials username=%r>' % self.username


class CredentialStore(object):
    """Thread-safe map from session token to the credentials of that session."""

    def __init__(self, timeout=1800, clock=time.monotonic):
        """``timeout`` is the inactivity period, in seconds, after which a
        session's credentials are forgotten."""
        self.timeout = timeout
        self._clock = clock
        self._entries = {}
        self._lock = threading.Lock()

    def add(self, username, password):
        """Store credentials for a new session and return its token."""
        token = secrets.token_urlsafe(32)
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            self._entries[token] = StoredCredentials(username, password, now)
        return token

    def get(self, token):
        """Return the credentials for ``token``, or None if it is unknown or
        expired. A successful lookup counts as activity."""
        if not token:
            return None
        with self._lock:
            now = self._clock()
            entry = self._entries.get(token)
            if entry is None:
                return None
            if now - entry.last_used > self.timeout:
                del self._entries[token]
                return None
            entry.last_used = now
            return entry

    def remove(self, token):
        """Forget the credentials for ``token`` (used at logout)."""
        if not token:
            return
        with self._lock:
            self._entries.pop(token, None)

    def __len__(self):
        with self._lock:
            return len(self._entries)

    def _purge_expired(self, now):
        expired = [token for token, entry in self._entries.items()
                   if now - entry.last_used > self.timeout]
        for token in expired:
            del self._entries[token]
