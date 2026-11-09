"""The three test browsers on this Mac, and the Safari rules every mode follows.

Ported from femto's harness (tests/harness/browsers.py at femto 65453b74); its rig notes in
tests/README.md hold the record of each mechanism. harness.behavior starts the sessions:

* Chrome Beta, headless (FEMTO_CHROME_BINARY names another binary).
* Firefox, headless (FEMTO_FIREFOX_BINARY). geckodriver needs --allow-system-access for the prefs
  the harness sets from the chrome context.
* Safari, through /usr/bin/safaridriver (FEMTO_SAFARIDRIVER), visible and serialized: one session at
  a time machine-wide (harness.locks), never while the user's own Safari runs, and only on an
  unlocked screen, since input never reaches a hidden page.
"""
import os
import subprocess
import time

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

CHROME_BINARY = os.environ.get("FEMTO_CHROME_BINARY", "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta")
FIREFOX_BINARY = os.environ.get("FEMTO_FIREFOX_BINARY", "/Applications/Firefox.app/Contents/MacOS/firefox")
SAFARIDRIVER = os.environ.get("FEMTO_SAFARIDRIVER", "/usr/bin/safaridriver")
WINDOW = (1800, 1000)          # Safari's window before a check sizes it


class BrowserError(Exception):
    """A browser cannot be started as the harness needs it."""


def _pgrep(pattern):
    return subprocess.run(["pgrep", "-fl", pattern], capture_output=True, text=True).stdout.splitlines()


def _kill_automation_safari():
    """Terminate Safari instances that safaridriver launched (they run with --automation). A session
    that died without quitting leaves its instance paired, and every new session is refused with
    "The Safari instance is already paired with a different session". The user's own Safari never
    carries --automation."""
    out = subprocess.run(["pgrep", "-f", "Safari.app/Contents/MacOS/Safari .*--automation"],
                         capture_output=True, text=True).stdout.split()
    for pid in out:
        subprocess.run(["kill", pid], capture_output=True)
    if out:
        time.sleep(3)
    return out


def users_safari_running():
    """The user's own Safari (no --automation): while it runs, safaridriver sessions never start
    (Safari 27.2, femto rig notes), so the harness refuses to start one."""
    return [line for line in _pgrep("Safari.app/Contents/MacOS/Safari( |$)") if "--automation" not in line]


def screen_front_app():
    """The frontmost app's name; "loginwindow" means the screen is locked."""
    try:
        asn = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True, timeout=5).stdout.strip()
        info = subprocess.run(["lsappinfo", "info", "-only", "name", asn], capture_output=True, text=True, timeout=5).stdout
        # macOS 27 prints `"loginwindow" ASN:0x0-0x2002: (in front)` plus a block; older releases
        # printed `"LSDisplayName"="Finder"`. The name is the last quoted string on the first line.
        quoted = (info.splitlines() or [""])[0].split('"')[1::2]
        return quoted[-1] if quoted else (info.strip() or asn)
    except Exception:
        return None


def _safari():
    from selenium.common.exceptions import SessionNotCreatedException
    from selenium.webdriver.safari.service import Service
    if users_safari_running():
        raise BrowserError("the user's own Safari is running; quit it (Cmd-Q) before a Safari run "
                           "(safaridriver sessions never start while it is open)")
    # The caller holds the machine-wide Safari lock, so no other harness session is live. An
    # automation instance left by a session that died keeps its windows, and a new session reusing
    # that instance opens its window behind them, without focus; start clean.
    _kill_automation_safari()
    try:
        d = webdriver.Safari(service=Service(executable_path=SAFARIDRIVER))
    except SessionNotCreatedException as e:
        if "already paired" not in str(e) or not _kill_automation_safari():
            raise
        d = webdriver.Safari(service=Service(executable_path=SAFARIDRIVER))
    try:
        d.set_window_rect(0, 0, WINDOW[0], WINDOW[1])
    except WebDriverException:
        pass
    return d
