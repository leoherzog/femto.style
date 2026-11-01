// The selftest's worker script (control cross-origin-worker; the unchanged site never starts it). It
// fetches the fixture's own stylesheet under another host name (localhost instead of 127.0.0.1), a
// URL built at run time with no URL literal. A worker keeps its own network log, which no page's
// Resource Timing shows: the proxy's report-only CSP reports the load (tests/harness/proxy.py).
fetch(self.location.protocol + "//localhost:" + self.location.port + "/fixture.css").catch(function () {});
