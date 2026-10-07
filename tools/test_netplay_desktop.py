"""Cold-boot two real desktop hosts; check pacing and offline-save isolation."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "rom", "x3", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--port", type=int, default=18010)
    parser.add_argument("--savestate-menu", action="store_true",
                        help="Exercise host save/load/cancel and guest authority checks")
    parser.add_argument("--delay-sync", action="store_true")
    args = parser.parse_args()
    frames = 360 if args.savestate_menu else 180
    for name in ("exe", "rom", "x3"):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    root = args.output.resolve()
    catalog = Path(__file__).resolve().parents[1] / "mods/preloaded/packages"
    processes = []
    try:
        for seat in range(2):
            peer = root / f"peer{seat}"
            peer.mkdir(parents=True, exist_ok=True)
            # Never overwrite an existing test/user installation or save.
            if (peer / args.exe.name).exists() or (peer / "saves").exists():
                raise RuntimeError(f"Use a fresh output directory: {peer}")
            exe = peer / args.exe.name
            shutil.copy2(args.exe, exe)
            mods = peer / "mods/preloaded"
            shutil.copytree(catalog, mods / "packages")
            (mods / "state.toml").write_text(
                'format_version = 1\n[[shared_resource]]\n'
                'id = "megaman-x.source.x3"\npath = ' +
                json.dumps(str(args.x3), ensure_ascii=False) + '\n', encoding="utf-8")
            (peer / "config.ini").write_text(
                '[General]\nAutosave=1\nDisableFrameDelay=0\n'
                '[Graphics]\nOutputMethod=SDL-Software\nWindowScale=1\n'
                '[Sound]\nEnableAudio=0\n', encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if not k.startswith(
                ("MMX_", "SNES_NET", "SNES_RB_", "SNESRECOMP_", "RNET_", "LNG_"))}
            env.update(SNES_NETPLAY="1", SNES_NET_SLOT=str(seat),
                SNES_NET_BIND=f"127.0.0.1:{args.port + seat}",
                SNES_NET_PEER=f"127.0.0.1:{args.port + 1 - seat}",
                SNES_NET_INPUT_PLAYER="0", SNESRECOMP_RUN_FRAMES=str(frames),
                SDL_VIDEODRIVER="dummy")
            if args.savestate_menu:
                env["SNES_NET_MENU_SELFTEST"] = "1"
            if args.delay_sync:
                env["SNES_NET_MODE"] = "delay"
            log = (peer / "desktop.log").open("wb")
            proc = subprocess.Popen([str(exe), "--no-launcher", "--rom", str(args.rom)],
                cwd=peer, env=env, stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            processes.append((proc, log, peer))
        digests = []
        for proc, log, peer in processes:
            result = proc.wait(timeout=40)
            log.close()
            text = (peer / "desktop.log").read_text(errors="replace")
            assert result == 0, text[-4000:]
            digest = re.search(r"RB boot digest agreed \(([0-9a-f]+)\)", text)
            if not args.delay_sync:
                assert digest, text[-4000:]
                digests.append(re.findall(r"RB boot digest agreed \(([0-9a-f]+)\)", text))
            timing = re.search(rf"video totals: simulations={frames} presentations=\d+ seconds=([0-9.]+)", text)
            assert timing, text[-4000:]
            elapsed = float(timing.group(1))
            assert elapsed >= frames / 60 - 0.1, f"Guest outran the SNES frame rate: {elapsed}s"
            assert not (peer / "saves/save0.sav").exists(), "Online match wrote an offline autosave"
            assert "match refused" not in text and "INPUT desync" not in text, text[-4000:]
            if args.savestate_menu:
                assert text.count("menu resumed serial=") == 3, text[-6000:]
                assert "menu sync failed" not in text and "RB fork" not in text, text[-6000:]
                if peer.name == "peer0":
                    assert all(f"action={action}" in text for action in ("save", "load", "cancel"))
                    assert (peer / "saves/save11.sav").exists(), "Host did not save slot 12"
                else:
                    assert "guest actions refused" in text
                    assert not list((peer / "saves").glob("*.sav")), "Guest wrote a personal save"
            print(f"{peer.name}: {frames} frames in {elapsed:.3f}s, no autosave")
        if not args.delay_sync:
            assert digests[0] == digests[1], f"Boot/resume states differ: {digests}"
            if args.savestate_menu:
                assert len(digests[0]) == 4, f"Missing post-resume agreements: {digests}"
    finally:
        for proc, log, _ in processes:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            log.close()


if __name__ == "__main__":
    main()
