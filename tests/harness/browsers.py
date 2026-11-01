"""WebDriver sessions for the three test browsers, and the mechanisms the rig depends on.

Ported from femto's harness (tests/harness/browsers.py at femto 65453b74); its rig notes in
tests/README.md hold the record of each mechanism.

* Chrome Beta, headless. prefers-color-scheme through CDP Emulation.setEmulatedMedia, which also
  applies inside same-origin iframes. Focus emulation keeps :focus working in background tabs.
* Firefox, headless. prefers-color-scheme through the content override pref
  layout.css.prefers-color-scheme.content-override (0 dark, 1 light, 2 system, 3 browser theme),
  set at runtime from the chrome context. geckodriver needs --allow-system-access for that. The
  change reaches content asynchronously, so set_media() polls until the host page sees it.
* Safari, through /usr/bin/safaridriver, visible and serialized. No emulation: the OS appearance is
  detected and only that media leg runs; data-theme legs still run. Pointer and keyboard input need
  a visible, focused window (an unlocked screen); interactive() reports whether that holds.

Each session opens the host page of its own proxy (harness.proxy), so both sides of a comparison
load into a same-origin iframe.
"""
import contextlib
import os
import subprocess
import time

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from .paths import HARNESS_PREFIX

CHROME_BINARY = os.environ.get("FEMTO_CHROME_BINARY", "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta")
FIREFOX_BINARY = os.environ.get("FEMTO_FIREFOX_BINARY", "/Applications/Firefox.app/Contents/MacOS/firefox")
SAFARIDRIVER = os.environ.get("FEMTO_SAFARIDRIVER", "/usr/bin/safaridriver")
WINDOW = (1800, 1000)          # top-level window; the iframe sets the tested width
FRAME_HEIGHT = 800             # document viewport height in every browser
PARK = (6, 6)                  # pointer parking spot on the host page strip, outside the iframe
BROWSERS = ("chrome", "firefox", "safari")
FF_SCHEME_PREF = "layout.css.prefers-color-scheme.content-override"
FF_SCHEME_VALUES = {"dark": 0, "light": 1}


class RigError(Exception):
    """A rig mechanism did not behave as verified; the cell cannot be trusted."""


_LIVE = set()   # sessions not yet quit; quit_all() ends them when a run unwinds early


def quit_all():
    """End every session still open when a run unwinds early (a worker may be mid-command)."""
    for sess in list(_LIVE):
        sess.quit(force=True)


def _chrome():
    o = webdriver.ChromeOptions()
    o.binary_location = CHROME_BINARY
    for a in ("--headless", f"--window-size={WINDOW[0]},{WINDOW[1]}", "--force-device-scale-factor=1",
              "--no-first-run", "--no-default-browser-check", "--disable-search-engine-choice-screen",
              "--force-color-profile=srgb", "--hide-scrollbars", "--disable-background-timer-throttling",
              "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows"):
        o.add_argument(a)
    return webdriver.Chrome(options=o)


def _firefox():
    from selenium.webdriver.firefox.service import Service
    o = webdriver.FirefoxOptions()
    o.binary_location = FIREFOX_BINARY
    o.add_argument("-headless")
    o.add_argument(f"--width={WINDOW[0]}")
    o.add_argument(f"--height={WINDOW[1]}")
    o.set_preference(FF_SCHEME_PREF, FF_SCHEME_VALUES["light"])
    o.set_preference("layout.css.devPixelsPerPx", "1.0")
    # System font fallback runs asynchronously by default: for about 2 s after startup, text that
    # needs a fallback face (the oracle's italic Arabic cite on /docs/rtl) is laid out with a
    # provisional face, 83.5 px wide instead of 80.45 px (tests/README.md, Rig notes, Firefox).
    o.set_preference("gfx.font_rendering.fallback.async", False)
    return webdriver.Firefox(options=o, service=Service(service_args=["--allow-system-access"]))


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
        raise RigError("the user's own Safari is running; quit it (Cmd-Q) before a Safari run "
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


class Session:
    """One browser, one host page on one proxy, many document loads."""

    def __init__(self, browser: str, proxy, log):
        if browser not in BROWSERS:
            raise ValueError(f"unknown browser {browser}")
        self.browser, self.proxy, self.base, self.log = browser, proxy, proxy.base, log
        t0 = time.time()
        from .locks import driver_start
        with driver_start(f"{browser} session", log):
            self.driver = {"chrome": _chrome, "firefox": _firefox, "safari": _safari}[browser]()
        _LIVE.add(self)
        self.launch_s = round(time.time() - t0, 2)
        try:
            self._setup()
        except Exception:
            self.quit()
            raise

    def _setup(self):
        caps = self.driver.capabilities
        self.version = caps.get("browserVersion")
        self.driver_version = ((caps.get("chrome") or {}).get("chromedriverVersion", "").split(" ")[0]
                               or caps.get("moz:geckodriverVersion") or "safaridriver")
        # Safari computes the style of a closed <details>' content anew for every getPropertyValue()
        # (about 0.07 ms a call on Safari 27.2), so collecting /docs/css-variables, whose code samples
        # sit in closed details (4,358 spans), takes about two minutes a side there; Chrome and
        # Firefox take about a second (tests/README.md, Rig notes, Safari).
        script_s = 600 if self.browser == "safari" else 120
        self.driver.set_script_timeout(script_s)
        self.driver.set_page_load_timeout(60)
        # Fail a hung command (a modal sheet in Safari, say) a minute after the script timeout,
        # instead of urllib3's 120 s default; the runner then restarts the session.
        self.client_timeout = script_s + 60
        try:
            self.driver.command_executor.client_config.timeout = self.client_timeout
        except AttributeError:
            pass
        self.media = None
        self.pseudos = None
        if self.browser == "chrome":
            self.driver.execute_cdp_cmd("Emulation.setFocusEmulationEnabled", {"enabled": True})
        self.open_host()
        st = self.host_status()
        self.os_scheme = "dark" if st["dark"] else "light"
        self.host = st

    # -- host page and scripts ------------------------------------------------------------
    def open_host(self):
        self.driver.get(self.base + HARNESS_PREFIX + "host.html")
        if not self.driver.execute_script("return !!window.H"):
            raise RigError("host page did not load differ.js")

    def js(self, fn: str, *args):
        return self.driver.execute_script(f"return H.{fn}.apply(null, arguments)", *args)

    def ajs(self, fn: str, *args):
        script = (f"const done = arguments[arguments.length - 1];"
                  f"H.{fn}.apply(null, Array.prototype.slice.call(arguments, 0, -1))"
                  f".then(done, e => done({{errors: ['in-page exception: ' + (e && e.stack || e)]}}));")
        return self.driver.execute_async_script(script, *args)

    @contextlib.contextmanager
    def in_frame(self):
        """Run WebDriver commands inside the document iframe (for Python-level readiness hooks)."""
        self.driver.switch_to.frame(self.driver.find_element(By.ID, "frame"))
        try:
            yield self.driver
        finally:
            self.driver.switch_to.default_content()

    def host_status(self):
        return self.js("hostStatus")

    def interactive(self) -> tuple[bool, str]:
        """Whether pointer and keyboard input reach the page (Safari needs a visible, focused window)."""
        if self.browser != "safari":
            return True, ""
        st = self.host_status()
        if st["visibility"] == "visible" and not st["hasFocus"]:
            # Each load replaces the iframe; when the old iframe held focus, Safari leaves the host
            # document without focus although the window is key. window.focus() gives it back; it
            # cannot make a window key behind another app or a lock screen.
            self.driver.execute_script("window.focus()")
            st = self.host_status()
        if st["visibility"] != "visible" or not st["hasFocus"]:
            try:
                self.driver.switch_to.window(self.driver.current_window_handle)
                time.sleep(0.3)
                self.driver.execute_script("window.focus()")
                st = self.host_status()
            except WebDriverException:
                pass
        if st["visibility"] != "visible" or not st["hasFocus"]:
            return False, (f"Safari window is not visible and focused (visibilityState={st['visibility']}, "
                           f"hasFocus={st['hasFocus']}); the screen may be locked. Interactive input needs an "
                           "unlocked screen with the Safari automation window in front.")
        return True, ""

    # -- color scheme ---------------------------------------------------------------------
    def set_media(self, media: str):
        """Make prefers-color-scheme report `media` inside the document iframe."""
        if media == self.media:
            return
        if self.browser == "chrome":
            self.driver.execute_cdp_cmd("Emulation.setEmulatedMedia",
                                        {"features": [{"name": "prefers-color-scheme", "value": media}]})
        elif self.browser == "firefox":
            with self.driver.context(self.driver.CONTEXT_CHROME):
                self.driver.execute_script(
                    f"Services.prefs.setIntPref('{FF_SCHEME_PREF}', {FF_SCHEME_VALUES[media]})")
            want = media == "dark"
            deadline = time.time() + 10
            while self.driver.execute_script("return matchMedia('(prefers-color-scheme: dark)').matches") != want:
                if time.time() > deadline:
                    raise RigError(f"Firefox did not apply {FF_SCHEME_PREF}={FF_SCHEME_VALUES[media]}")
                time.sleep(0.05)
        else:
            if media != self.os_scheme:
                raise RigError(f"Safari cannot emulate prefers-color-scheme: {media}; the OS scheme is {self.os_scheme}")
        self.media = media

    # -- input (rig checks; the behavior mode will drive widgets with these) ----------------
    def _pointer(self, x, y, down=False, up=False):
        ab = ActionBuilder(self.driver, duration=0)
        ab.pointer_action.move_to_location(int(x), int(y))
        if down:
            ab.pointer_action.pointer_down()
        if up:
            ab.pointer_action.pointer_up()
        ab.perform()

    def move(self, x, y):
        self._pointer(x, y)

    def press(self, x, y):
        self._pointer(x, y, down=True)

    def release(self, x, y):
        self._pointer(x, y, up=True)

    def park(self):
        self._pointer(*PARK)

    def tab(self, shift=False):
        """A real Tab keypress. Safari moves to links and buttons only with Option held."""
        ac = ActionChains(self.driver, duration=0)
        mods = ([Keys.SHIFT] if shift else []) + ([Keys.ALT] if self.browser == "safari" else [])
        for m in mods:
            ac.key_down(m)
        ac.send_keys(Keys.TAB)
        for m in reversed(mods):
            ac.key_up(m)
        ac.perform()

    def reset_input(self):
        try:
            ActionBuilder(self.driver).clear_actions()
        except WebDriverException:
            pass

    # -- screenshots ----------------------------------------------------------------------
    def frame_png(self) -> bytes:
        return self.driver.find_element(By.ID, "frame").screenshot_as_png

    def quit(self, force=False):
        """End the session and stop the driver process and, for Safari, its automation instance (the
        caller holds the Safari lock, so no other harness session uses one). force: the browser
        stopped answering (a command timed out), so the quit request gets 10 s."""
        _LIVE.discard(self)
        if force:
            try:
                self.driver.command_executor.client_config.timeout = 10
            except AttributeError:
                pass
        else:
            try:
                if self.browser == "firefox":
                    with self.driver.context(self.driver.CONTEXT_CHROME):
                        self.driver.execute_script(f"Services.prefs.clearUserPref('{FF_SCHEME_PREF}')")
            except Exception:
                pass
        try:
            self.driver.quit()
        except Exception:
            pass
        proc = getattr(getattr(self.driver, "service", None), "process", None)
        if proc is not None and proc.poll() is None:
            proc.kill()
        if self.browser == "safari":
            # safaridriver leaves its --automation Safari running after a clean quit too (seen on
            # 2026-10-30, Safari 27.2); the caller holds the Safari lock, so it is this session's.
            _kill_automation_safari()
