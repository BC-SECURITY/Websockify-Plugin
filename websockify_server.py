import logging
from typing import override

import websockify

from empire.server.common import helpers
from empire.server.core.plugins import BasePlugin

log = logging.getLogger(__name__)


class Plugin(BasePlugin):
    @override
    def on_load(self, db):
        self.execution_enabled = False
        self.websockify_server = None
        self.websockify_proc = None
        self.settings_options = {
            "SourceHost": {
                "Description": "Address of the source host.",
                "Required": True,
                "Value": "0.0.0.0",
            },
            "SourcePort": {
                "Description": "Port on source host.",
                "Required": True,
                "Value": "5910",
            },
            "TargetHost": {
                "Description": "Address of the target host.",
                "Required": True,
                "Value": "",
            },
            "TargetPort": {
                "Description": "Port on target host.",
                "Required": True,
                "Value": "5900",
            },
        }

    @override
    def on_start(self, db):
        current_settings = self.current_settings(db)
        source_host = current_settings["SourceHost"]
        source_port = int(current_settings["SourcePort"])
        target_host = current_settings["TargetHost"]
        target_port = int(current_settings["TargetPort"])

        self.websockify_server = websockify.LibProxyServer(
            target_host=target_host,
            target_port=target_port,
            listen_host=source_host,
            listen_port=source_port,
        )

        self.websockify_proc = helpers.KThread(
            target=self.websockify_server.serve_forever
        )
        self.websockify_proc.daemon = True
        self.websockify_proc.start()

    @override
    def on_stop(self, db):
        # on_stop runs for every loaded plugin on shutdown, started or not,
        # so both handles may still be None.
        if self.websockify_server is not None:
            self.websockify_server.shutdown()
            self.websockify_server.server_close()
            self.websockify_server = None

        if self.websockify_proc is not None:
            self.websockify_proc.join(timeout=5)
            if self.websockify_proc.is_alive():
                log.warning("websockify thread did not exit within 5s")
            self.websockify_proc = None
