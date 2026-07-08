from __future__ import annotations

import contextlib
import io
import unittest

import scripts.rk1828_safe_runtime as safe_runtime


class Rk1828SafeRuntimeTests(unittest.TestCase):
    def test_stop_runtime_does_not_use_broad_pkill_f_regex(self) -> None:
        self.assertNotIn("pkill -TERM -f", safe_runtime.REMOTE_SCRIPT)
        self.assertNotIn("pkill -KILL -f", safe_runtime.REMOTE_SCRIPT)
        self.assertIn("kill_runtime_processes TERM", safe_runtime.REMOTE_SCRIPT)
        self.assertIn("kill_runtime_processes KILL", safe_runtime.REMOTE_SCRIPT)

    def test_runtime_steps_include_vendor_delay_windows(self) -> None:
        self.assertIn("sleep 2  # wait for /dev/pcie-rkep-* after insmod", safe_runtime.REMOTE_SCRIPT)
        self.assertIn("sleep 10  # wait for RK1828 after firmware download", safe_runtime.REMOTE_SCRIPT)

    def test_firmware_requires_explicit_danger_acknowledgement(self) -> None:
        parser = safe_runtime.build_parser()

        args = parser.parse_args(["firmware"])

        self.assertFalse(args.allow_firmware_hang)

    def test_firmware_direct_requires_explicit_danger_acknowledgement(self) -> None:
        args = safe_runtime.build_parser().parse_args(["firmware-direct"])

        self.assertFalse(args.allow_firmware_hang)

        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(3, safe_runtime.run_remote(args))

    def test_post_recovery_report_is_read_only(self) -> None:
        args = safe_runtime.build_parser().parse_args(["post-recovery-report"])

        self.assertEqual("post-recovery-report", args.action)
        self.assertIn("post_recovery_report() {", safe_runtime.REMOTE_SCRIPT)
        self.assertIn("rknn-smi info -l", safe_runtime.REMOTE_SCRIPT)
        report_body = safe_runtime.REMOTE_SCRIPT.split("post_recovery_report() {", 1)[1].split("\n}", 1)[0]
        self.assertNotIn("insmod", report_body)
        self.assertNotIn("/bin/pcie_upgrade_tool -s", report_body)
        self.assertNotIn("uf \"$firmware_path\"", report_body)

    def test_install_driver_service_only_loads_rkep_driver(self) -> None:
        args = safe_runtime.build_parser().parse_args(["install-driver-service"])

        self.assertEqual("install-driver-service", args.action)
        self.assertIn("install_driver_service() {", safe_runtime.REMOTE_SCRIPT)
        service_body = safe_runtime.REMOTE_SCRIPT.split("install_driver_service() {", 1)[1].split("\n}", 1)[0]
        self.assertIn("rk1828-rkep-load.service", service_body)
        self.assertIn("insmod", service_body)
        self.assertIn("daemon-reload", service_body)
        self.assertIn("enable rk1828-rkep-load.service", service_body)
        self.assertNotIn("rknn3_transfer_proxy", service_body)
        self.assertNotIn("/bin/pcie_upgrade_tool", service_body)
        self.assertNotIn("uf \"$firmware_path\"", service_body)

    def test_firmware_direct_uses_tmp_dir_without_proxy(self) -> None:
        parser = safe_runtime.build_parser()
        args = parser.parse_args(["firmware-direct"])

        self.assertEqual("firmware-direct", args.action)
        self.assertFalse(args.allow_firmware_hang)
        self.assertIn("firmware_direct() {", safe_runtime.REMOTE_SCRIPT)
        direct_body = safe_runtime.REMOTE_SCRIPT.split("firmware_direct() {", 1)[1].split("\n}", 1)[0]
        self.assertIn("refuse_if_proxy_running", direct_body)
        self.assertIn("mkdir -p /tmp/rk1828-fw", direct_body)
        self.assertIn('uf "$firmware_path" /tmp/rk1828-fw', direct_body)

    def test_test_device_is_read_only(self) -> None:
        args = safe_runtime.build_parser().parse_args(["test-device"])

        self.assertEqual("test-device", args.action)
        self.assertIn("test_device() {", safe_runtime.REMOTE_SCRIPT)
        test_body = safe_runtime.REMOTE_SCRIPT.split("test_device() {", 1)[1].split("\n}", 1)[0]
        self.assertIn('/bin/pcie_upgrade_tool -s "$device_id" td', test_body)
        self.assertNotIn("rknn3_transfer_proxy", test_body)
        self.assertNotIn(" uf ", test_body)
        self.assertNotIn(" rd", test_body)

    def test_read_vendor_requires_vendor_id_and_is_read_only(self) -> None:
        parser = safe_runtime.build_parser()
        args = parser.parse_args(["read-vendor", "--vendor-id", "0"])

        self.assertEqual("read-vendor", args.action)
        self.assertEqual("0", args.vendor_id)
        self.assertFalse(args.allow_loader_interaction)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(6, safe_runtime.run_remote(args))

        allowed_args = parser.parse_args(
            ["read-vendor", "--vendor-id", "0", "--allow-loader-interaction"]
        )
        self.assertTrue(allowed_args.allow_loader_interaction)
        self.assertIn("read_vendor() {", safe_runtime.REMOTE_SCRIPT)
        vendor_body = safe_runtime.REMOTE_SCRIPT.split("read_vendor() {", 1)[1].split("\n}", 1)[0]
        self.assertIn('/bin/pcie_upgrade_tool -s "$device_id" rvd "$vendor_id"', vendor_body)
        self.assertNotIn("rknn3_transfer_proxy", vendor_body)
        self.assertNotIn(" uf ", vendor_body)

    def test_reset_device_requires_explicit_danger_acknowledgement(self) -> None:
        args = safe_runtime.build_parser().parse_args(["reset-device"])

        self.assertFalse(args.allow_device_reset)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(4, safe_runtime.run_remote(args))

        allowed_args = safe_runtime.build_parser().parse_args(["reset-device", "--allow-device-reset"])
        self.assertTrue(allowed_args.allow_device_reset)

    def test_bootloader_direct_requires_explicit_danger_acknowledgement(self) -> None:
        args = safe_runtime.build_parser().parse_args(["bootloader-direct"])

        self.assertFalse(args.allow_bootloader_download)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(5, safe_runtime.run_remote(args))

        allowed_args = safe_runtime.build_parser().parse_args(
            ["bootloader-direct", "--allow-bootloader-download", "--bootloader-path", "/tmp/BOOT"]
        )
        self.assertTrue(allowed_args.allow_bootloader_download)
        self.assertEqual("/tmp/BOOT", allowed_args.bootloader_path)
        self.assertIn("bootloader_direct() {", safe_runtime.REMOTE_SCRIPT)
        bootloader_body = safe_runtime.REMOTE_SCRIPT.split("bootloader_direct() {", 1)[1].split("\n}", 1)[0]
        self.assertIn("refuse_if_proxy_running", bootloader_body)
        self.assertIn('/bin/pcie_upgrade_tool -s "$device_id" db "$bootloader_path"', bootloader_body)
        self.assertIn('/bin/pcie_upgrade_tool -s "$device_id" td', bootloader_body)
        self.assertNotIn(" uf ", bootloader_body)


if __name__ == "__main__":
    unittest.main()
