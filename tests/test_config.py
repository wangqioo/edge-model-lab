from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.lib import config


class LoadDevicesTests(unittest.TestCase):
    def test_local_device_override_merges_with_auth_override(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            devices_file = root / "devices.yaml"
            local_file = root / "devices.local.yaml"

            devices_file.write_text(
                textwrap.dedent(
                    """
                    devices:
                      orange-rk3588:
                        host: 150.158.146.192
                        port: 6280
                        user: orangepi
                        role: primary-deployment
                        platform: rk3588
                        board: Orange Pi 5 Plus
                        deployment_backend: docker
                        report: inventory/reports/orange.md
                    """
                ),
                encoding="utf-8",
            )
            local_file.write_text(
                textwrap.dedent(
                    """
                    auth:
                      orange-rk3588:
                        password_env: EDGE_ORANGE_RK3588_PASSWORD
                    devices:
                      orange-rk3588:
                        host: 192.168.1.52
                        port: 22
                    """
                ),
                encoding="utf-8",
            )

            with patch.object(config, "DEVICES_FILE", devices_file), patch.object(config, "LOCAL_FILE", local_file):
                device = config.load_devices()["orange-rk3588"]

        self.assertEqual(device.host, "192.168.1.52")
        self.assertEqual(device.port, 22)
        self.assertEqual(device.user, "orangepi")
        self.assertEqual(device.password_env, "EDGE_ORANGE_RK3588_PASSWORD")


if __name__ == "__main__":
    unittest.main()
