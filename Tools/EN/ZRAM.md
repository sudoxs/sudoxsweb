# ZRAM: Compressed RAM Swap

ZRAM creates a compressed swap device entirely in RAM. Pages written to it are compressed in place, so you trade CPU cycles for effective memory capacity. On modern Linux it's the default swap backend on Fedora, Pop!_OS, and most Android devices.

**Why it matters:** If your CPU has idle headroom but your RAM is the bottleneck — many similar processes (Electron apps, Chromium tabs, Docker containers running the same image), large builds, VMs, or virtual network labs — ZRAM can multiply your usable memory by 2x to 10x+ in practice. Compression ratios of 4:1 to 10:1 are common when workloads share a lot of identical memory pages; ratios of 20x–30x have been observed with highly redundant container workloads.

**Tradeoffs:** Compression and decompression cost CPU time and add latency. Disk swap is avoided entirely in most desktop workloads once ZRAM is tuned, which matters on SSDs. Don't inflate the ZRAM size beyond what makes sense — a 128 GB ZRAM on a 48 GB machine is absurd in general use, even if it worked in a specific lab case.

---

## Setup

Load the module and configure it persistently.

```bash
# Load zram module
sudo modprobe zram

# Check it loaded
lsmod | grep zram
```

Set the number of ZRAM devices and their size. `zramctl` is the userspace tool.

```bash
# Create a zram device (or use an existing one)
sudo zramctl --find --size 32G --algorithm zstd
```

- `--find` picks the first free `/dev/zramN`
- `--size` is the uncompressed capacity (this is what gets compressed)
- `--algorithm` — use `zstd` for best ratio/speed balance; `lz4` is faster but compresses less

Format it as swap and enable it.

```bash
# Format the device as swap
sudo mkswap /dev/zram0

# Enable it with high priority so the kernel prefers it over disk swap
sudo swapon --priority 100 /dev/zram0

# Verify
swapon --show
zramctl
```

`--priority 100` ensures the kernel uses ZRAM before any disk swap partition. Keep a small disk swap as a fallback, but ZRAM should absorb almost everything.

---

## Monitoring

```bash
# Live view: DISKSIZE, DATA, COMPR, TOTAL, STREAMS, ALGORITHM
zramctl

# Swap usage summary
swapon --show

# Per-device memory stats
cat /proc/swaps
```

Key columns in `zramctl`:
- **DISKSIZE** — uncompressed capacity
- **DATA** — actual compressed bytes stored in RAM
- **COMPR** — compression ratio (DISKSIZE used vs DATA)
- **TOTAL** — total RAM consumed by the device

Watch the `COMPR` value. Anything above 3x means ZRAM is pulling its weight. If it stays near 1x, the workload isn't compressible and ZRAM is just wasting CPU.

---

## Tuning

**Size:** Start with a ZRAM size equal to your physical RAM. Going higher (2x–4x) only makes sense for heavily redundant workloads. Your physical RAM is still the hard limit — ZRAM does not create memory, it compresses what's already there.

**Algorithm:** `zstd` for the best ratio, `lz4` if CPU is weak and latency matters. Check availability:

```bash
cat /sys/block/zram0/comp_algorithm
```

**Persist across reboots** with a systemd unit or by adding to `/etc/fstab`:

```fstab
/dev/zram0 none swap defaults,pri=100 0 0
```

And in `/etc/modules-load.d/zram.conf`:

```
zram
```

---

## Real-World Notes

- **Electron/Chromium heavy workloads:** Many shared libraries across processes compress extremely well. Ratios of 4x–9x are typical on a 32 GB machine with multiple VS Code windows and browser tabs.
- **Containerlab / Docker labs:** Identical router images across dozens of containers compress to a fraction of their nominal size. 48 GB RAM running ~100 virtual routers has been done this way. The ratio only holds when the processes share pages — heterogeneous workloads will compress far less.
- **Large builds:** Compilation bursts allocate and free memory rapidly; ZRAM absorbs the spikes without touching disk swap.
- **Oversizing is a real risk.** A ZRAM sized far above your RAM (e.g. 128 GB on a 48 GB box) can push the system into a CPU-bound thrash if the data isn't actually compressible. Size it to your workload, not to a number that looks impressive.
