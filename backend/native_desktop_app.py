#!/usr/bin/env python3
"""
S.T.A.L.K.E.R. Anomaly 1.5.3 Studio — Native Desktop Application (Zero-Socket / No 127.0.0.1)
Author: EternalPain

Runs Anomaly Studio inside a native GTK3 + WebKit2 4.1 desktop window using the custom
in-process URI scheme `anomaly://studio/...` and a native UserContentManager IPC bridge
for POST/GET requests. Zero TCP/IP sockets or localhost ports are opened.

For Dev/Debug or macOS/Browser mode, use `backend/server.py` (or `./AnomalyStudio --web`).
"""
import base64
import json
import os
import sys
import urllib.parse
from pathlib import Path

ROOT = (
    Path(os.environ["ANOMALY_STUDIO_ROOT"]).resolve()
    if os.environ.get("ANOMALY_STUDIO_ROOT")
    else Path(__file__).resolve().parent.parent
)
sys.path.insert(0, str(ROOT / "backend"))

import server as studio_server  # noqa: E402


# Injected into `index.html` when running in Native `anomaly://studio/` mode so `fetch('/api/...')`
# with POST bodies and binary arrayBuffers work seamlessly over the custom scheme.
NATIVE_IPC_BRIDGE_JS = r"""
<script>
(function() {
  window.__ANOMALY_NATIVE_DESKTOP__ = true;
  const origFetch = window.fetch.bind(window);
  window.fetch = async function(input, init) {
    let url = typeof input === "string" ? input : (input && input.url ? input.url : String(input));
    const method = ((init && init.method) || (input && input.method) || "GET").toUpperCase();
    if (url.startsWith("/") && !url.startsWith("//")) {
      url = "anomaly://studio" + url;
    }
    if (method === "POST" && url.startsWith("anomaly://studio/")) {
      let rawBody = "";
      if (init && init.body != null) {
        rawBody = typeof init.body === "string" ? init.body : JSON.stringify(init.body);
      }
      const b64 = btoa(unescape(encodeURIComponent(rawBody)));
      const sep = url.includes("?") ? "&" : "?";
      const ipcUrl = url + sep + "__ipc_method=POST&__ipc_body_b64=" + encodeURIComponent(b64);
      return origFetch(ipcUrl, { method: "GET", headers: (init && init.headers) || {} });
    }
    return origFetch(url, init);
  };
})();
</script>
"""


def _handle_anomaly_uri_scheme(request) -> None:
    """Handles `anomaly://studio/<path>` completely in-process via `studio_server.dispatch_inprocess_request`."""
    import gi
    gi.require_version("WebKit2", "4.1")
    from gi.repository import Gio, GLib, WebKit2

    uri = request.get_uri() or "anomaly://studio/"
    parsed = urllib.parse.urlparse(uri)
    path = parsed.path or "/"
    qs_map = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)

    method = (request.get_http_method() or "GET").upper()
    body_bytes = b""

    if "__ipc_method" in qs_map:
        method = qs_map.pop("__ipc_method")[0].upper()
        b64_str = qs_map.pop("__ipc_body_b64", [""])[0]
        if b64_str:
            try:
                body_bytes = base64.b64decode(b64_str)
            except Exception:
                body_bytes = b""

    clean_query = urllib.parse.urlencode(qs_map, doseq=True)
    raw_path = f"{path}?{clean_query}" if clean_query else path

    status_code, content_type, payload = studio_server.dispatch_inprocess_request(method, raw_path, body_bytes)

    # Inject the native POST/GET fetch bridge into index.html
    if path in ("/", "/index.html") and content_type.startswith("text/html"):
        html_str = payload.decode("utf-8", errors="replace")
        html_str = html_str.replace("<head>", "<head>\n" + NATIVE_IPC_BRIDGE_JS, 1)
        payload = html_str.encode("utf-8")

    gbytes = GLib.Bytes.new(payload)
    stream = Gio.MemoryInputStream.new_from_bytes(gbytes)
    resp = WebKit2.URISchemeResponse.new(stream, len(payload))
    resp.set_status(status_code, "OK" if status_code < 400 else "Error")
    resp.set_content_type(content_type.split(";")[0].strip())
    request.finish_with_response(resp)


def run_native_gtk_app(self_test_ms: int = 0) -> int:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("WebKit2", "4.1")
    from gi.repository import GLib, Gtk, WebKit2

    ctx = WebKit2.WebContext.get_default()
    sec = ctx.get_security_manager()
    sec.register_uri_scheme_as_secure("anomaly")
    sec.register_uri_scheme_as_cors_enabled("anomaly")
    sec.register_uri_scheme_as_local("anomaly")
    ctx.register_uri_scheme("anomaly", _handle_anomaly_uri_scheme)

    win = Gtk.Window(title="S.T.A.L.K.E.R. Anomaly 1.5.3 Studio — Native Desktop Edition (Zero-Socket)")
    win.set_default_size(1600, 940)
    win.connect("destroy", Gtk.main_quit)

    settings = WebKit2.Settings()
    settings.set_enable_webgl(True)
    settings.set_enable_webaudio(True)
    settings.set_enable_developer_extras(True)
    settings.set_enable_write_console_messages_to_stdout(False)

    webview = WebKit2.WebView.new_with_context(ctx)
    webview.set_settings(settings)
    win.add(webview)

    webview.load_uri("anomaly://studio/index.html")
    win.show_all()

    if self_test_ms > 0:
        def _auto_close():
            Gtk.main_quit()
            return False
        GLib.timeout_add(self_test_ms, _auto_close)

    print("[Anomaly Studio v0.1.0-alpha] Running Native Desktop Window (scheme: anomaly://studio/, 0 network ports opened).", flush=True)
    Gtk.main()
    return 0


if __name__ == "__main__":
    test_ms = 0
    for arg in sys.argv[1:]:
        if arg.startswith("--self-test-ms="):
            test_ms = int(arg.split("=", 1)[1])
    sys.exit(run_native_gtk_app(self_test_ms=test_ms))
