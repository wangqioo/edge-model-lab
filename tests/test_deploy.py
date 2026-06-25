from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.lib.config import Device


class DeployRoutingTests(unittest.TestCase):
    def test_rk3576_devices_use_python_service(self) -> None:
        from scripts.lib import deploy

        device = Device(
            id="linaro-rk3576",
            host="127.0.0.1",
            port=6276,
            user="linaro",
            role="rk3576-main-test",
            platform="rk3576",
            board="KICKPI K7",
            deployment_backend="systemd-venv",
            report="",
        )

        with patch.object(deploy, "deploy_rknn_service", return_value=0) as mock_service, patch.object(
            deploy, "run_rknn_smoke", return_value=0
        ) as mock_smoke:
            code = deploy.deploy_device(device)

        self.assertEqual(code, 0)
        mock_service.assert_called_once_with(device)
        mock_smoke.assert_not_called()

    def test_rk3576_devices_benchmark_python_service(self) -> None:
        from scripts.lib import deploy

        device = Device(
            id="linaro-rk3576",
            host="127.0.0.1",
            port=6276,
            user="linaro",
            role="rk3576-main-test",
            platform="rk3576",
            board="KICKPI K7",
            deployment_backend="systemd-venv",
            report="",
        )

        with patch.object(deploy, "bench_rknn_service", return_value=0) as mock_bench:
            code = deploy.bench_device(device)

        self.assertEqual(code, 0)
        mock_bench.assert_called_once_with(device, 20)

    def test_rk3588_device_uses_smoke(self) -> None:
        from scripts.lib import deploy

        device = Device(
            id="orange-rk3588",
            host="127.0.0.1",
            port=6280,
            user="orangepi",
            role="primary-deployment",
            platform="rk3588",
            board="Orange Pi 5 Plus",
            deployment_backend="docker",
            report="",
        )

        with patch.object(deploy, "load_assets", return_value={"rk3588_resnet18_lite2": object()}), patch.object(
            deploy, "run_rknn_smoke", return_value=0
        ) as mock_smoke, patch.object(deploy, "deploy_rknn_service", return_value=0) as mock_service:
            code = deploy.deploy_device(device)

        self.assertEqual(code, 0)
        mock_smoke.assert_called_once()
        mock_service.assert_not_called()

    def test_deploy_all_uses_routing(self) -> None:
        from scripts.lib import deploy

        fake_device = Device(
            id="one",
            host="127.0.0.1",
            port=1,
            user="user",
            role="role",
            platform="rk3576",
            board="board",
            deployment_backend="backend",
            report="",
        )

        with patch.object(deploy, "load_devices", return_value={"one": fake_device}), patch.object(
            deploy, "deploy_device", return_value=0
        ) as mock_deploy:
            code = deploy.deploy_all()

        self.assertEqual(code, 0)
        mock_deploy.assert_called_once_with(fake_device)

    def test_bench_all_uses_routing(self) -> None:
        from scripts.lib import deploy

        fake_device = Device(
            id="one",
            host="127.0.0.1",
            port=1,
            user="user",
            role="role",
            platform="rk3576",
            board="board",
            deployment_backend="backend",
            report="",
        )

        with patch.object(deploy, "load_devices", return_value={"one": fake_device}), patch.object(
            deploy, "bench_device", return_value=0
        ) as mock_bench:
            code = deploy.bench_all()

        self.assertEqual(code, 0)
        mock_bench.assert_called_once_with(fake_device)


if __name__ == "__main__":
    unittest.main()
