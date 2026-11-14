# Motion Planner

Turn a still image into a reviewable animation plan. The skill records which objects and regions matter, what could move, which points stay attached, and what would need a mask or reconstructed background later.

## Usage

Copy the bundled [`motion-planner/`](motion-planner/) folder into your Codex skills directory, such as `~/.codex/skills/`. Keep its contents together and invoke it as `$motion-planner`.

> Use $motion-planner to map the motion in this illustration. Show where the cloth and foliage are anchored and mark any uncertain coordinates.

Use Python 3 and Pillow for the overlay. Install `jsonschema` to enable structural validation in addition to the built-in semantic checks.

```bash
python -m pip install pillow jsonschema
cd motion-planner
python scripts/validate_manifest.py examples/caravela.manifest.json
python scripts/render_overlay.py manifest.json reference.png out/overlay.png
```

Run from this skill's folder. For the overlay command, provide your own reference image and the manifest prepared for that image.

## How it works

1. Read the image dimensions and record how they were obtained.
2. Inventory the scene and distinguish whole objects from the regions that may animate.
3. Record movement inheritance, drawing order, and coupled motion separately. Label each critical value with a review status and its provenance.
4. Validate the JSON and render the overlay from the same coordinates. Review the overlay and list missing masks or hidden areas.

The plan contains estimated coordinates where necessary. The workflow stops at planning. See the [manifest schema](motion-planner/schema/manifest.schema.json) and [motion presets](motion-planner/references/motion_presets.md).
