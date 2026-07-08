from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.lib.config import Device
from scripts.lib.rkllm_conversion import ConversionCheck


class CliTests(unittest.TestCase):
    def test_models_filter_accepts_rk1828_assets(self) -> None:
        from scripts.lib import cli

        with patch.object(cli, "_print_asset_table", return_value=None) as mock_print:
            code = cli.run(["models", "--platform", "rk1828"])

        self.assertEqual(code, 0)
        mock_print.assert_called_once_with(platform="rk1828")


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

        with patch.object(deploy, "deploy_rknn_service", return_value=0) as mock_service, patch.object(
            deploy, "run_rknn_smoke", return_value=0
        ) as mock_smoke:
            code = deploy.deploy_device(device)

        self.assertEqual(code, 0)
        mock_service.assert_called_once_with(device)
        mock_smoke.assert_not_called()

    def test_deploy_all_uses_routing(self) -> None:
        from scripts.lib import deploy

        rk3576_device = Device(
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
        rk3588_device = Device(
            id="two",
            host="127.0.0.1",
            port=2,
            user="user",
            role="role",
            platform="rk3588",
            board="board",
            deployment_backend="backend",
            report="",
        )

        with patch.object(deploy, "load_devices", return_value={"one": rk3576_device, "two": rk3588_device}), patch.object(
            deploy, "deploy_device", return_value=0
        ) as mock_deploy:
            code = deploy.deploy_all()

        self.assertEqual(code, 0)
        mock_deploy.assert_any_call(rk3576_device)
        mock_deploy.assert_any_call(rk3588_device)
        self.assertEqual(mock_deploy.call_count, 2)

    def test_bench_all_uses_routing(self) -> None:
        from scripts.lib import deploy

        rk3576_device = Device(
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
        rk3588_device = Device(
            id="two",
            host="127.0.0.1",
            port=2,
            user="user",
            role="role",
            platform="rk3588",
            board="board",
            deployment_backend="backend",
            report="",
        )

        with patch.object(deploy, "load_devices", return_value={"one": rk3576_device, "two": rk3588_device}), patch.object(
            deploy, "bench_device", return_value=0
        ) as mock_bench:
            code = deploy.bench_all()

        self.assertEqual(code, 0)
        mock_bench.assert_any_call(rk3576_device)
        mock_bench.assert_any_call(rk3588_device)
        self.assertEqual(mock_bench.call_count, 2)

    def test_llm_deploy_routes_to_taishanpi(self) -> None:
        from scripts.lib import deploy

        device = Device(
            id="lckfb-rk3576",
            host="127.0.0.1",
            port=6277,
            user="lckfb",
            role="low-memory-validation",
            platform="rk3576",
            board="LCKFB TaishanPi 3M",
            deployment_backend="systemd-venv",
            report="",
        )

        with patch.object(deploy, "deploy_rkllm_device", return_value=0) as mock_llm:
            code = deploy.deploy_llm_device(device)

        self.assertEqual(code, 0)
        mock_llm.assert_called_once_with(device)

    def test_llm_deploy_routes_to_linaro_rk3576(self) -> None:
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

        with patch.object(deploy, "deploy_rkllm_device", return_value=0) as mock_llm:
            code = deploy.deploy_llm_device(device)

        self.assertEqual(code, 0)
        mock_llm.assert_called_once_with(device)

    def test_llm_deploy_routes_to_orange_rk3588(self) -> None:
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

        with patch.object(deploy, "deploy_rk3588_rkllm_text_smoke", return_value=0) as mock_llm:
            code = deploy.deploy_llm_device(device)

        self.assertEqual(code, 0)
        mock_llm.assert_called_once_with(device)

    def test_rk3588_qwen3_vl_smoke_requires_orange_target(self) -> None:
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

        code = deploy.run_rk3588_qwen3_vl_smoke(device)

        self.assertEqual(code, 2)

    def test_rk3588_qwen3_vl_smoke_runs_existing_board_deployment(self) -> None:
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

        with patch.object(deploy, "run_ssh", return_value=(0, "rkllm init success\nrobot: ok\n")) as mock_ssh:
            code = deploy.run_rk3588_qwen3_vl_smoke(device)

        self.assertEqual(code, 0)
        remote_command = mock_ssh.call_args.args[1]
        self.assertIn("/home/orangepi/edge-model-lab/qwen3-vl-rk3588", remote_command)
        self.assertIn("RKNPU driver: v0.9.8", remote_command)
        self.assertIn("sudo -S", remote_command)
        self.assertIn("qwen3-vl-4b-instruct_w8a8_rk3588.rkllm", remote_command)
        self.assertIn("printf '0\\n'", remote_command)

    def test_rkllm_conversion_check_reports_missing_source_model_files(self) -> None:
        from scripts.lib import rkllm_conversion

        with TemporaryDirectory() as temp_name, patch.object(
            rkllm_conversion, "DEFAULT_QWEN3_VL_4B_HF_PATH", Path(temp_name) / "missing-source"
        ):
            checks = rkllm_conversion.collect_rk3588_qwen3_vl_conversion_checks()
            source_check = next(check for check in checks if check.name == "Qwen3-VL-4B HuggingFace source")

        self.assertEqual(source_check.status, "missing")
        self.assertIn("model-00001-of-00002.safetensors", source_check.detail)

    def test_rkllm_conversion_check_exit_code_reflects_missing_items(self) -> None:
        from scripts.lib import rkllm_conversion

        checks = [
            ConversionCheck("one", "ok", "ready"),
            ConversionCheck("two", "missing", "not ready"),
        ]

        with patch.object(rkllm_conversion, "collect_rk3588_qwen3_vl_conversion_checks", return_value=checks):
            code = rkllm_conversion.print_rk3588_qwen3_vl_conversion_check()

        self.assertEqual(code, 1)

    def test_prepare_rk3588_qwen3_vl_workspace_creates_expected_files(self) -> None:
        from scripts.lib import rkllm_conversion

        with TemporaryDirectory() as temp_name:
            workspace = Path(temp_name) / "workspace"
            rkllm_conversion.prepare_rk3588_qwen3_vl_workspace(workspace)

            self.assertTrue((workspace / "environment.yml").exists())
            self.assertTrue((workspace / "README.md").exists())
            wheels = list((workspace / "wheels").glob("rkllm_toolkit-*.whl"))
            self.assertTrue(wheels)
            self.assertTrue((workspace / "qwen3_vl_4b_rk3588" / "export" / "export_rkllm.py").exists())

    def test_prepare_rk3588_qwen3_vl_workspace_adds_qwen3_helpers(self) -> None:
        from scripts.lib import rkllm_conversion

        with TemporaryDirectory() as temp_name:
            workspace = Path(temp_name) / "workspace"
            rkllm_conversion.prepare_rk3588_qwen3_vl_workspace(workspace)

            demo = workspace / "qwen3_vl_4b_rk3588"
            input_helper = demo / "data" / "make_input_embeds_for_quantize_qwen3.py"
            run_helper = demo / "run-qwen3-vl-rk3588-export.sh"

            self.assertTrue(input_helper.exists())
            self.assertIn("Qwen3VLForConditionalGeneration", input_helper.read_text(encoding="utf-8"))
            self.assertTrue(run_helper.exists())
            run_helper_text = run_helper.read_text(encoding="utf-8")
            self.assertIn("rkllm123-py310", run_helper_text)
            self.assertIn("SCRIPT_DIR=", run_helper_text)
            self.assertIn('WORKSPACE=${WORKSPACE:-"$SCRIPT_DIR"}', run_helper_text)
            self.assertIn("MAX_CONTEXT=${MAX_CONTEXT:-1024}", run_helper_text)
            self.assertIn("export/export_rkllm_qwen3_context.py", run_helper_text)
            self.assertIn("--max_context \"$MAX_CONTEXT\"", run_helper_text)

            rkllm_context_export = demo / "export" / "export_rkllm_qwen3_context.py"
            self.assertTrue(rkllm_context_export.exists())
            rkllm_context_export_text = rkllm_context_export.read_text(encoding="utf-8")
            self.assertIn("parser.add_argument(\"--max_context\"", rkllm_context_export_text)
            self.assertIn("max_context=args.max_context", rkllm_context_export_text)
            self.assertIn("llm.export_rkllm(args.savepath)", rkllm_context_export_text)

            img_encoder = demo / "deploy" / "src" / "img_encoder.cpp"
            if not img_encoder.exists():
                img_encoder = demo / "src" / "img_encoder.cpp"
            img_encoder_text = img_encoder.read_text(encoding="utf-8")
            self.assertIn("std::vector<float> img_vec(img_vec_len);", img_encoder_text)
            self.assertIn("rknn_app_ctx.io_num.n_output", img_encoder_text)
            self.assertIn("img_vec.data()", img_encoder_text)

    def test_download_qwen3_vl_source_writes_manifest_and_skips_existing_files(self) -> None:
        from scripts.lib import rkllm_conversion

        with TemporaryDirectory() as temp_name:
            target = Path(temp_name)
            test_sizes = {name: len("existing") for name in rkllm_conversion.QWEN3_VL_4B_HF_FILES}
            for name in test_sizes:
                (target / name).write_text("existing", encoding="utf-8")

            with patch.object(rkllm_conversion, "QWEN3_VL_4B_HF_FILE_SIZES", test_sizes), patch.object(
                rkllm_conversion, "_curl_download"
            ) as mock_curl, patch.object(rkllm_conversion, "_download_chunked") as mock_chunked:
                rkllm_conversion.download_qwen3_vl_4b_source(target)

            mock_curl.assert_not_called()
            mock_chunked.assert_not_called()
            manifest = (target / "download-manifest.txt").read_text(encoding="utf-8")
            self.assertIn("Qwen/Qwen3-VL-4B-Instruct", manifest)
            self.assertTrue((target / "SOURCE.md").exists())

    def test_download_qwen3_vl_source_uses_chunked_download_for_large_files(self) -> None:
        from scripts.lib import rkllm_conversion

        with TemporaryDirectory() as temp_name:
            target = Path(temp_name)
            test_files = ("small.json", "large.safetensors")
            test_sizes = {"small.json": 4, "large.safetensors": 4096}

            def fake_curl(destination: Path, _url: str, _range_header: str | None = None) -> None:
                destination.write_bytes(b"x" * test_sizes[destination.name])

            def fake_chunked(destination: Path, _url: str, total_size: int, _chunk_size: int, _workers: int) -> None:
                destination.write_bytes(b"x" * total_size)

            with patch.object(rkllm_conversion, "QWEN3_VL_4B_HF_FILES", test_files), patch.object(
                rkllm_conversion, "QWEN3_VL_4B_HF_FILE_SIZES", test_sizes
            ), patch.object(rkllm_conversion, "CHUNKED_DOWNLOAD_THRESHOLD_BYTES", 1024), patch.object(
                rkllm_conversion, "_curl_download", side_effect=fake_curl
            ) as mock_curl, patch.object(rkllm_conversion, "_download_chunked", side_effect=fake_chunked) as mock_chunked:
                rkllm_conversion.download_qwen3_vl_4b_source(target, chunk_size=1024, workers=2)

            self.assertEqual(mock_curl.call_count, 1)
            self.assertEqual(mock_chunked.call_count, 1)
            self.assertEqual((target / "large.safetensors").stat().st_size, 4096)


if __name__ == "__main__":
    unittest.main()
