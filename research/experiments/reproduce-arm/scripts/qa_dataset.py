"""Quality check for LeRobot pick-and-place datasets.

Numbers find the candidates, images confirm them, and a human watches whatever is still unclear.

    python qa_dataset.py screen <repo_id>                     # per-episode metrics + flags -> screen.json
    python qa_dataset.py render <repo_id> --episodes 3,41     # joint plots + key-frame sheets
    python qa_dataset.py grid   <repo_id>                     # first and last frame of every episode
    python qa_dataset.py all    <repo_id>                     # screen, render flagged + reference, grid

Common options: --root <dir> for a local dataset not yet on the Hub, --out <dir> (default: review).

Assumptions: LeRobot's normalised joint scale (about +-100), a joint named "*gripper*" whose value rises
when it opens, and a pick-and-place task where the gripper opens once to grasp and once to release.
Flags are candidates, not verdicts: check every flag against the rendered images before deleting anything.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

MOVE_THR = 1.0  # joint units that count as "moving"
OPEN_MARGIN = 3.0  # gripper counts as open when commanded this far above its resting value at episode start
Z_THR = 3.0  # robust z-score above which a metric is flagged
JUMP_ABS_THR = 30.0  # a single-frame joint change this large is a glitch regardless of z-score
MAX_RENDER = 8  # cap on flagged episodes rendered by `all`
METRICS = ["idle_start_s", "idle_end_s", "active_s", "hold_s", "hold_gap", "max_jump",
           "track_err_p99", "start_dev", "end_dev", "path_len"]


def load(repo_id, root):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    ds = LeRobotDataset(repo_id, root=root)
    hf = ds.hf_dataset
    data = {
        "ep": np.array(hf["episode_index"]),
        "ts": np.array(hf["timestamp"], dtype=float),
        "task": np.array(hf["task_index"]),
        "state": np.stack([np.asarray(x) for x in hf["observation.state"]]).astype(float),
        "action": np.stack([np.asarray(x) for x in hf["action"]]).astype(float),
    }
    names = ds.meta.features["observation.state"].get("names") or [
        f"joint{i}" for i in range(data["state"].shape[1])]
    return ds, data, list(names)


def open_segments(mask, min_len=3, merge_gap=5):
    """Contiguous True runs as [start, end) frames, merging short gaps and dropping blips."""
    runs, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            runs.append([i, j])
            i = j
        else:
            i += 1
    merged = []
    for run in runs:
        if merged and run[0] - merged[-1][1] <= merge_gap:
            merged[-1][1] = run[1]
        else:
            merged.append(run)
    return [r for r in merged if r[1] - r[0] >= min_len]


def screen(ds, data, names, out):
    fps, ep, st, ac = ds.fps, data["ep"], data["state"], data["action"]
    grip = next((i for i, n in enumerate(names) if "gripper" in n), None)
    arm = [i for i in range(len(names)) if i != grip]
    eps = sorted(set(ep.tolist()))
    home = np.median(np.stack([st[ep == e][0] for e in eps]), axis=0)

    rows = []
    for e in eps:
        mask = ep == e
        s, a, ts = st[mask], ac[mask], data["ts"][mask]
        n = len(a)
        moved_start = np.abs(a - a[0]).max(1) > MOVE_THR
        moved_end = np.abs(a - a[-1]).max(1) > MOVE_THR
        first = int(np.argmax(moved_start)) if moved_start.any() else n
        last = n - 1 - int(np.argmax(moved_end[::-1])) if moved_end.any() else 0
        row = {
            "episode": int(e),
            "total_s": n / fps,
            "idle_start_s": first / fps,
            "idle_end_s": (n - 1 - last) / fps,
            "active_s": max(last - first, 0) / fps,
            "timing_errors": int((np.abs(np.diff(ts) - 1.0 / fps) > 1e-3).sum()),
            "tasks": sorted(set(data["task"][mask].tolist())),
            "max_jump": float(np.abs(np.diff(s, axis=0)).max()) if n > 1 else 0.0,
            "track_err_p99": float(np.percentile(np.abs(a[:, arm] - s[:, arm]), 99)),
            "start_dev": float(np.abs(s[0] - home).max()),
            "end_dev": float(np.abs(s[-1] - home).max()),
            "path_len": float(np.abs(np.diff(s[:, arm], axis=0)).sum()),
            "n_open": None, "open_segments": [], "grip_rest": None,
            "grasp_frame": None, "release_frame": None, "hold_s": None, "hold_gap": None,
        }
        if grip is not None:
            rest = float(np.median(a[: min(5, n), grip]))
            segs = open_segments(a[:, grip] > rest + OPEN_MARGIN)
            row.update(n_open=len(segs), open_segments=segs, grip_rest=rest)
            if len(segs) >= 2:
                g, r = segs[0][1], segs[-1][0]
                row.update(grasp_frame=int(g), release_frame=int(r), hold_s=(r - g) / fps)
                if r > g:
                    # While holding, the object stops the jaws closing: measured stays above commanded.
                    row["hold_gap"] = float(np.median(s[g:r, grip] - a[g:r, grip]))
        rows.append(row)

    for key in METRICS:
        vals = np.array([r[key] if r[key] is not None else np.nan for r in rows], dtype=float)
        if np.isnan(vals).all():
            continue
        med = np.nanmedian(vals)
        mad = 1.4826 * np.nanmedian(np.abs(vals - med))
        scale = mad if mad > 1e-6 else (np.nanstd(vals) or 1.0)
        for r, v in zip(rows, vals):
            r.setdefault("z", {})[key] = None if np.isnan(v) else float((v - med) / scale)

    n_tasks = len(set(data["task"].tolist()))
    opens = [r["n_open"] for r in rows if r["n_open"] is not None]
    mode_open = Counter(opens).most_common(1)[0][0] if opens else None
    for r in rows:
        reasons, severity = [], 0.0
        if r["timing_errors"]:
            reasons.append(f"{r['timing_errors']} irregular frame gaps")
            severity += 10
        if r["max_jump"] > JUMP_ABS_THR:
            reasons.append(f"joint glitch: {r['max_jump']:.1f} in one frame")
            severity += 10
        if mode_open is not None and r["n_open"] != mode_open:
            reasons.append(f"gripper opened {r['n_open']}x (usual {mode_open}x)")
            severity += 5
        for key, z in r.get("z", {}).items():
            if z is not None and abs(z) > Z_THR:
                reasons.append(f"{key}={r[key]:.2f} (z={z:+.1f})")
                severity += abs(z) - Z_THR
        r["reasons"], r["severity"] = reasons, severity

    flagged = sorted([r for r in rows if r["reasons"]], key=lambda r: -r["severity"])
    reference = min(rows, key=lambda r: sum(abs(z) for z in r.get("z", {}).values() if z is not None)
                    + 100 * bool(r["reasons"]))

    lens = np.array([r["total_s"] for r in rows])
    print(f"episodes={len(rows)} frames={len(ep)} fps={fps} cameras={ds.meta.camera_keys}")
    print(f"task strings: {n_tasks}" + ("  <-- more than one: check for typos" if n_tasks > 1 else ""))
    for i, task in enumerate(ds.meta.tasks.index.tolist()):
        print(f"  [{i}] {task!r}")
    print(f"length: min={lens.min():.1f}s median={np.median(lens):.1f}s max={lens.max():.1f}s")
    if mode_open is not None:
        print(f"gripper open cycles: usual={mode_open} distribution={dict(Counter(opens))}")
    print("medians:", {k: round(float(np.nanmedian([r[k] if r[k] is not None else np.nan for r in rows])), 2)
                       for k in METRICS if any(r[k] is not None for r in rows)})
    print(f"\nFLAGGED {len(flagged)} of {len(rows)} episode(s) (candidates, confirm with render):")
    for r in flagged:
        print(f"  ep {r['episode']:>3} severity={r['severity']:5.1f} :: " + "; ".join(r["reasons"]))
    print(f"\nREFERENCE (most typical) episode: {reference['episode']}")

    out.mkdir(parents=True, exist_ok=True)
    result = {"repo": ds.repo_id, "fps": fps, "names": names, "reference": reference["episode"],
              "flagged": [r["episode"] for r in flagged], "episodes": rows}
    (out / "screen.json").write_text(json.dumps(result, indent=1))
    print(f"wrote {out / 'screen.json'}")
    return result


def to_image(tensor):
    from PIL import Image

    return Image.fromarray((tensor.permute(1, 2, 0).numpy() * 255).clip(0, 255).astype("uint8"))


def render(ds, data, names, out, episodes, result):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image, ImageDraw

    fps, cams = ds.fps, ds.meta.camera_keys
    metrics = {m["episode"]: m for m in result["episodes"]}
    tile_w, tile_h, cols = 320, 240, 4
    out.mkdir(parents=True, exist_ok=True)

    for e in episodes:
        idx = np.where(data["ep"] == e)[0]
        s, a, m = data["state"][idx], data["action"][idx], metrics[e]
        t = np.arange(len(idx)) / fps
        label = "; ".join(m["reasons"]) if m["reasons"] else "reference (typical)"

        n_rows = -(-len(names) // 2)
        fig, axes = plt.subplots(n_rows, 2, figsize=(12, 2.5 * n_rows), sharex=True, squeeze=False)
        for j, name in enumerate(names):
            axis = axes.ravel()[j]
            axis.plot(t, a[:, j], "--", lw=1.2, label="action (command)")
            axis.plot(t, s[:, j], lw=1.2, label="state (measured)")
            for seg in m["open_segments"]:
                axis.axvspan(seg[0] / fps, seg[1] / fps, color="tab:green", alpha=0.12)
            axis.axvline(m["idle_start_s"], color="grey", lw=0.8, ls=":")
            axis.set_title(name, fontsize=9)
            axis.grid(alpha=0.3)
        for axis in axes.ravel()[len(names):]:
            axis.set_visible(False)
        axes[0, 0].legend(fontsize=8)
        fig.suptitle(f"episode {e} | {label}\n(green = gripper open, dotted = motion start)", fontsize=10)
        fig.tight_layout()
        fig.savefig(out / f"ep{e:03d}_joints.png", dpi=80)
        plt.close(fig)

        n = len(idx)
        f0 = min(int(round(m["idle_start_s"] * fps)), n - 1)
        g, r = m["grasp_frame"], m["release_frame"]
        if g is None or r is None:
            picks = [(int(x), f"t={x / fps:.1f}s") for x in np.linspace(0, n - 1, 8)]
        else:
            lag = int(0.7 * fps)
            picks = [(f0, "motion start"), ((f0 + g) // 2, "approach"), (min(g + 3, n - 1), "grasp"),
                     (min(g + lag, n - 1), "lift"), ((g + r) // 2, "transport"), (r, "release cmd"),
                     (min(r + lag, n - 1), "after release"), (n - 1, "end")]
        rows = -(-len(picks) // cols)
        sheet = Image.new("RGB", (cols * tile_w, rows * len(cams) * tile_h), "black")
        for k, (frame, text) in enumerate(picks):
            item = ds[int(idx[frame])]
            for c, cam in enumerate(cams):
                tile = to_image(item[cam]).resize((tile_w, tile_h))
                draw = ImageDraw.Draw(tile)
                draw.rectangle([0, 0, tile_w, 16], fill="black")
                draw.text((4, 2), f"{cam.split('.')[-1]} | {text} | {frame / fps:.1f}s", fill="white")
                sheet.paste(tile, ((k % cols) * tile_w, ((k // cols) * len(cams) + c) * tile_h))
        sheet.save(out / f"ep{e:03d}_frames.jpg", quality=85)
        print(f"rendered episode {e} -> {out / f'ep{e:03d}_joints.png'}, {out / f'ep{e:03d}_frames.jpg'}")


def grid(ds, data, out, cols=10, tile=(192, 144)):
    """First frame shows where the object started; last frame shows where it ended up."""
    from PIL import Image, ImageDraw

    ep = data["ep"]
    eps = sorted(set(ep.tolist()))
    rows = -(-len(eps) // cols)
    out.mkdir(parents=True, exist_ok=True)
    sheets = {(which, cam): Image.new("RGB", (cols * tile[0], rows * tile[1]), "black")
              for which in ("start", "end") for cam in ds.meta.camera_keys}
    for k, e in enumerate(eps):
        idx = np.where(ep == e)[0]
        for which, frame in (("start", idx[0]), ("end", idx[-1])):
            item = ds[int(frame)]
            for cam in ds.meta.camera_keys:
                img = to_image(item[cam]).resize(tile)
                draw = ImageDraw.Draw(img)
                draw.rectangle([0, 0, 40, 14], fill="black")
                draw.text((3, 1), f"ep{e}", fill="yellow")
                sheets[(which, cam)].paste(img, ((k % cols) * tile[0], (k // cols) * tile[1]))
    for (which, cam), sheet in sheets.items():
        path = out / f"grid_{which}_{cam.split('.')[-1]}.jpg"
        sheet.save(path, quality=90)
        print(f"wrote {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["screen", "render", "grid", "all"])
    parser.add_argument("repo_id")
    parser.add_argument("--root", default=None, help="local dataset directory (default: HF cache / Hub)")
    parser.add_argument("--out", type=Path, default=Path("review"))
    parser.add_argument("--episodes", default="", help="comma-separated episode indices for render")
    args = parser.parse_args()

    ds, data, names = load(args.repo_id, args.root)
    if args.command == "grid":
        grid(ds, data, args.out)
        return
    if args.command == "render" and (args.out / "screen.json").exists():
        result = json.loads((args.out / "screen.json").read_text())
    else:
        result = screen(ds, data, names, args.out)
    if args.command == "render":
        render(ds, data, names, args.out, [int(x) for x in args.episodes.split(",") if x], result)
    elif args.command == "all":
        render(ds, data, names, args.out, [result["reference"]] + result["flagged"][:MAX_RENDER], result)
        grid(ds, data, args.out)


if __name__ == "__main__":
    main()
