# RK1828K Bring-Up Lessons

This is the cleaned-up operating knowledge from the RK1828K debug session. It
keeps the useful conclusions and removes the dead ends from the chronological
experiment logs.

## Final Diagnosis

The RK1828K board, power, PCIe link, and `rknn3_rk1820.img` firmware path were
not the root cause.

The real blocker was the host-side `pcie-rkep.ko` driver. The vendor source was
close, but not directly compatible with the Orange Pi 5 Plus
`6.1.43-rockchip-rk3588` kernel and RKNN3 `1.0.4` userspace.

The working fix was an adapted vendor RKEP module:

```text
source: vendor rknn_install_without_model(1).tar.gz / rknn/driver/pcie-rkep
kernel tree: /home/wq/edge-tools/orangepi-kernel/linux-orangepi-6.1.43-full
kernel commit: 752c0d0a12fdce201da45852287b48382caa8c0f
DRV_VERSION: 0x00030301
disabled: PCIE_EP_RESET_CTRL external PM reset call missing from Orange Pi 6.1.43
kept: PCIE_EP_RESET_SLOT using rkep_ep_slot_reset()
module sha256: 58b4cd6664953d560aa8fc72b6295caec2634793ba17246f32e66108fcb913b2
installed: /usr/lib/modules/pcie-rkep.ko
backup: /root/pcie-rkep-before-vendor-adapted-20260708-133536.ko
```

After this driver was loaded, full firmware download succeeded and `rknn-smi`
reported the device online:

```text
Device 0 Status: Online
Health: OK
Chip Name: RK1828
Bus-Id: 0000:01:00.0
Memory: 32 / 5120 MB
```

## Useful Debug Sequence

Do not start with model tests. Bring the stack up in layers:

```text
12V power and PCIe enumeration
-> pcie-rkep driver and /dev node
-> pcie_upgrade_tool td
-> firmware download
-> rknn-smi Online
-> transfer proxy devices
-> model load/init
-> real inference
```

The important distinction is that PCIe enumeration is not enough. A broken RKEP
driver can still expose `/dev/pcie-rkep-*` while failing later during firmware
download or SMI/proxy interaction.

## Known Good Manual Bring-Up

This is now a recovery path, not the normal day-to-day path. The normal path is
the auto-start service in the next section.

Keep the vendor services disabled:

```bash
systemctl disable rknn3.service rknn-mdns.service
```

Manual sequence after a clean boot:

```bash
killall rknn3_transfer_proxy 2>/dev/null || true
killall pcie_upgrade_tool 2>/dev/null || true

rmmod pcie_rkep 2>/dev/null || true
insmod /usr/lib/modules/pcie-rkep.ko

pcie_upgrade_tool -s 0000:01:00.0 td
pcie_upgrade_tool -s 0000:01:00.0 uf /lib/firmware/rknn3_rk1820.img /tmp/rk1828-fw

RKNN3_NETWORK_SOCKET_FILE=/tmp/rk-mdns.ini \
  nohup /bin/rknn3_transfer_proxy >/tmp/rknn3-transfer-proxy.log 2>&1 &

rknn-smi info
rknn3_transfer_proxy devices
```

Expected working signs:

```text
pcie_upgrade_tool td:
  Soc=rk1820 Addr=0000:01:00.0 Mode=MaskROM [1d87:182a]
  Testing device OK

firmware:
  Downloading bootloader OK
  Running ddr code...OK
  Running subsoc_os code...OK
  Downloading firmware OK

rknn-smi:
  Status Online
  Chip Name RK1828
  Bus-Id 0000:01:00.0

proxy:
  0000:01:00.0 b98e6c51 PCIE
```

## Automatic Bring-Up

The working boot path is controlled by these files:

```text
repo source:
  deploy/systemd/rk1828/rk1828-runtime-start
  deploy/systemd/rk1828/rk1828-runtime.service

installed on RK3588 host:
  /usr/local/sbin/rk1828-runtime-start
  /etc/systemd/system/rk1828-runtime.service
```

Enabled services:

```bash
systemctl enable rk1828-rkep-load.service rk1828-runtime.service
systemctl disable rknn3.service rknn-mdns.service
```

Boot order:

```text
rk1828-rkep-load.service
-> load adapted /usr/lib/modules/pcie-rkep.ko
-> create /dev/pcie-rkep-0000:01:00.0
-> rk1828-runtime.service
-> verify adapted driver sha256
-> download /lib/firmware/rknn3_rk1820.img with pcie_upgrade_tool
-> exec /bin/rknn3_transfer_proxy in the systemd cgroup
```

The runtime script deliberately checks the adapted driver hash before touching
the RK1828K:

```text
58b4cd6664953d560aa8fc72b6295caec2634793ba17246f32e66108fcb913b2
```

This prevents a vendor reinstall from silently replacing the working driver
with an incompatible one.

Reboot verification on 2026-07-08:

```text
system boot: 2026-07-08 21:38 CST
rk1828-runtime.service: active (running), enabled
rknn3.service: disabled, inactive
rknn-mdns.service: disabled, inactive
rknn-smi: Device 0 Online, Health OK, Chip RK1828, Bus-Id 0000:01:00.0
memory: 32 / 5120 MB
proxy: 0000:01:00.0 b98e6c51 PCIE
```

Normal status checks:

```bash
systemctl status rk1828-runtime.service --no-pager -l
journalctl -u rk1828-runtime.service -n 120 --no-pager
rknn-smi info
rknn3_transfer_proxy devices
```

The existing guarded wrapper still works with the service running:

```bash
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py smi
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py devices
EDGE_ORANGE_RK3588_PASSWORD=orangepi ./scripts/rk1828_safe_runtime.py vision-smoke
```

`vision-smoke` is expected to end at `Failed to open input numpy file: none`;
the important proof is before that:

```text
rknn3_init success
rknn3_load_model_from_data success
Core number: 8
rknn3_model_init success
```

## Local Chat Service

The user-facing local AI chat stack has two more services on the RK3588 host:

```text
rkllm3-server.service
-> serves Qwen3-VL on http://127.0.0.1:8899/v1

rkclaw-web.service
-> serves RKClaw Chat on http://0.0.0.0:8888
-> calls RKCLAW_BASE_URL=http://127.0.0.1:8899/v1
```

FRP maps the public TCP port to the RKClaw web service:

```text
150.158.146.192:6288 -> orangepi5plus 127.0.0.1:8888
```

On 2026-07-08 after a reboot, FRP was active and the public port accepted TCP,
but `127.0.0.1:8888` and `127.0.0.1:8899` were not listening. That produced an
HTTP "empty reply from server" on `http://150.158.146.192:6288/`. The root
cause was that the RK1828 runtime service was enabled, but the model server and
RKClaw web UI were only manual `nohup` scripts and had no boot-time unit.

The fixed services are tracked in:

```text
deploy/systemd/rk1828/rkllm3-server.service
deploy/systemd/rk1828/rkclaw-web.service
```

Installed paths on the RK3588 host:

```text
/etc/systemd/system/rkllm3-server.service
/etc/systemd/system/rkclaw-web.service
```

Normal status checks:

```bash
systemctl status rk1828-runtime.service rkllm3-server.service rkclaw-web.service frpc.service --no-pager -l
ss -lntp | grep -E ':8888|:8899'
curl -sS http://127.0.0.1:8888/api/health
curl -sS http://127.0.0.1:8899/v1/models
curl -sS http://150.158.146.192:6288/api/health
```

Expected health result:

```json
{"ok":true,"model_base":"http://127.0.0.1:8899/v1"}
```

Minimal model smoke:

```bash
curl -sS --max-time 60 http://127.0.0.1:8899/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3-vl","messages":[{"role":"user","content":"你好，用一句话回答。"}],"max_tokens":16}'
```

Minimal RKClaw web API smoke:

```bash
curl -sS --max-time 90 http://127.0.0.1:8888/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"用一句话说你已经启动。"}'
```

The RKClaw `/api/chat` endpoint expects a `message` string. Sending OpenAI-style
`messages` directly to this endpoint returns `empty message`; send OpenAI-style
payloads to `8899/v1/chat/completions` instead.

## What Was Noise

These were useful to check once, but they were not the final cause:

```text
power supply capacity
startup sleep 2 / sleep 10
whether the connection is USB
whether PCIe enumeration exists
whether rknn3_rk1820.img contains RK1820 strings
whether explicit db BOOT is required before uf firmware
```

The firmware name and internal strings are confusing, but the image did work
once the host RKEP driver was corrected.

## What Actually Mattered

The vendor source had two critical compatibility issues:

1. `DRV_VERSION` was `0x00030300`, while RKNN3 userspace needed `0x30301`.
2. `PCIE_EP_RESET_CTRL` used a Rockchip PCIe PM reset API that is not present in
   the Orange Pi `6.1.43-rockchip-rk3588` tree.

The first issue made RKNN3 reject or mis-handle the driver ABI. The second issue
prevented compiling the vendor source against the matching Orange Pi kernel
tree.

After adapting those two points, the driver could load and firmware download no
longer wedged the host.

## Model Deployment Notes

Future model deployments should not hit the old device-offline problem as long
as the adapted RKEP module is loaded and firmware has been downloaded.

New model failures are more likely to be normal RKNN3/model issues:

```text
wrong core mask
wrong input shape
wrong dtype
unsupported ops
model too large for node memory
bad or incompatible RKNN3 conversion artifacts
test-tool input format problems
```

RK1828 reports 8 cores. Use `0xff` as the all-core mask. The earlier `0x3`
mask was wrong for this device:

```text
Core number: 8
Error: core_mask 0x3 does not match core number 8
```

Known model-load proof from the Qwen3-VL vision smoke:

```text
rknn3_init success
rknn3_load_model_from_data success
Core number: 8
rknn3_model_init success
```

The `rknn3_model_test` `.npy` reader is picky. A failure like this is a test
input parser problem, not a hardware bring-up failure:

```text
Invalid numpy dtype f2
```

## Gemma4 E4B VLM Notes

Gemma4 E4B with image recognition is deployed as a side-by-side test path, not
as a replacement for the current Qwen3-VL chat service.

Current preserved service path:

```text
150.158.146.192:6288 -> rkclaw-web.service:8888 -> rkllm3-server.service:8899
```

Gemma4 files are separate:

```text
model dir: /home/orangepi/lincaigui/gemma4-e4b
demo dir:  /home/orangepi/rknn3-model-zoo/install/rk3588_linux_aarch64/rknn_gemma4_demo
script:    /home/orangepi/lincaigui/run-gemma4-e4b-vlm.sh
```

Official RKNN3 `v1.0.4` preconverted `gemma4-e4b` file sizes:

```text
gemma4-e4b_per_layer_inputs.embed.bin 5637144576
gemma4-e4b.embed.bin                  1342177280
gemma4-e4b.tokenizer.gguf             15780102
llm_gemma4-e4b.rknn                   28253368
llm_gemma4-e4b.safetensors            50332472
llm_gemma4-e4b.weight                 3000512512
vision_gemma4-e4b.rknn                4014528
vision_gemma4-e4b.weight              92916736
```

The official Gemma4 C++ demo builds Audio, Vision, and LLM together. For a
Vision+LLM-only smoke test on this RK3588 host, the audio path caused a link
failure through `audioutils -> libfftw3f.a`:

```text
relocation R_AARCH64_ADR_PREL_PG_HI21 against symbol `stdout@@GLIBC_2.17'
can not be used when making a shared object; recompile with -fPIC
```

Since the image-recognition path passes empty audio model and audio input
arguments, the useful fix is to patch the demo into a VLM-only build:

```bash
cd /home/orangepi/rknn3-model-zoo
patch -p1 < /path/to/edge-model-lab/patches/rknn3/gemma4-vlm-only-no-fftw.patch
./build-linux.sh -t rk3588 -a aarch64 -d gemma4
```

The resulting binary should not link FFTW:

```bash
ldd install/rk3588_linux_aarch64/rknn_gemma4_demo/rknn_gemma4_demo | grep -i fftw
```

Expected result: no output.

Gemma4 and Qwen3-VL both need the RK1828 accelerator. Do not enable Gemma4 as a
boot service until resource sharing and recovery behavior are validated. For a
manual Gemma4 smoke, stop the Qwen model server only for the duration of the
test, then start it again.

Manual smoke command:

```bash
sudo systemctl stop rkllm3-server.service
/home/orangepi/lincaigui/run-gemma4-e4b-vlm.sh \
  /home/orangepi/rknn3-model-zoo/datasets/COCO/subset/000000419312.jpg \
  "<image>请用中文简短描述这张图片。"
sudo systemctl start rkllm3-server.service
```

Validated on 2026-07-09 with Qwen temporarily stopped:

```text
Gemma4 return code: 0
Image output: 这张图片展示了一张摆满了各种食物的餐桌...
Prefill: 84 tokens, 204.73 ms, 410.30 tokens/s
Generate: 51 tokens, 1072.55 ms, 47.55 tokens/s
Vision latency: 83.07 ms, 12.04 FPS
```

The first failed Gemma4 attempt returned `rknn3_model_init` `ACK_FAIL` because
`rkllm3-server.service` was still active and holding the RK1828. Treat that as a
resource-conflict failure, not a Gemma4 model failure.

## Qwen2.5-Omni-3B VLM Notes

Official RKNN3 `v1.0.4` has a `Qwen2_5_Omni` demo, but the preconverted
`Qwen2.5-Omni-3B` download bundle contains only Vision+LLM files. It does not
include the `Qwen2.5-Omni-3B-audio.rknn` and `.weight` files shown in the demo
README.

Current validated scope:

```text
works: Vision + LLM image understanding
not yet validated: Audio + LLM or Vision + Audio + LLM
reason: official preconverted bundle lacks audio RKNN/weight files
```

Qwen2.5-Omni-3B files are separate from the current Qwen3-VL service:

```text
model dir: /home/orangepi/lincaigui/Qwen2.5-Omni-3B
demo dir:  /home/orangepi/rknn3-model-zoo/install/rk3588_linux_aarch64/rknn_Qwen2_5_Omni_demo
script:    /home/orangepi/lincaigui/run-qwen25-omni-3b-vlm.sh
```

Official preconverted file sizes:

```text
Qwen2.5-Omni-3B.embed.bin        622329856
Qwen2.5-Omni-3B.tokenizer.gguf   5930151
llm_Qwen2.5-Omni-3B.rknn         28195776
llm_Qwen2.5-Omni-3B.weight       1936839168
vision_Qwen2.5-Omni-3B.rknn      6694208
vision_Qwen2.5-Omni-3B.weight    411765248
```

The stock demo failed to link on the RK3588 host for the same FFTW reason as
Gemma4:

```text
libfftw3f.a(assert.o): relocation R_AARCH64_ADR_PREL_PG_HI21 against symbol `stdout@@GLIBC_2.17'
```

The working patch is:

```bash
cd /home/orangepi/rknn3-model-zoo
patch -p0 < /path/to/edge-model-lab/patches/rknn3/qwen25-omni-3b-vlm-only-no-fftw.patch
./build-linux.sh -t rk3588 -a aarch64 -d Qwen2_5_Omni
```

The patch also fixes a demo argument bug: `main.cc` read masks as
`vision_core_mask audio_core_mask llm_core_mask`, but called
`init_qwen2_5_omni_model()` with the wrong order. The bad order passed `0` as
the vision core mask in VLM-only mode and caused:

```text
core mask 0x00000000 is not contiguous
rknn_model_init failed! ret=-2
```

Manual smoke command:

```bash
sudo systemctl stop rkllm3-server.service
/home/orangepi/lincaigui/run-qwen25-omni-3b-vlm.sh
sudo systemctl start rkllm3-server.service
```

Validated on 2026-07-09 with Qwen temporarily stopped:

```text
Qwen2.5-Omni-3B return code: 0
Image output: 月球上，宇航员正在打开啤酒瓶。
Prefill: 247 tokens, 315.24 ms, 783.53 tokens/s
Generate: 12 tokens, 147.97 ms, 81.10 tokens/s
Vision latency: 240.90 ms, 4.15 FPS
```

Do not describe this as full audio-capable Omni deployment until the missing
audio RKNN/weight pair is converted or supplied by the vendor.

## Do Not Repeat

Avoid these patterns:

```text
running firmware download while proxy/model processes are active
using pkill -f with broad patterns that can kill the current SSH command
trusting a vendor installer before reading what it overwrites
running driver-ubuntu.sh without matching kernel headers/source
enabling rknn3.service before manual reboot behavior is validated
assuming /dev/pcie-rkep-* means the full RKNN3 path is healthy
```

## If It Breaks Again

First recovery checks:

```bash
lspci -nn | grep -Ei '182a|1828|processing'
lsmod | grep pcie_rkep
ls -l /dev/pcie-rkep-*
sha256sum /usr/lib/modules/pcie-rkep.ko
modinfo /usr/lib/modules/pcie-rkep.ko | grep vermagic
pcie_upgrade_tool -s 0000:01:00.0 td
rknn-smi info
```

The expected installed module hash is:

```text
58b4cd6664953d560aa8fc72b6295caec2634793ba17246f32e66108fcb913b2
```

If the hash changed, restore the adapted module or rebuild it from the vendor
source with the two compatibility changes above.

## Source Logs

Keep the full chronology for audit only:

```text
docs/experiments/2026-07-03-rk1828-12v-power-detection.md
docs/experiments/2026-07-08-rk1828k-vendor-escalation.md
```
