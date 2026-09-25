# SPDX-License-Identifier: GPL-2.0-or-later
"""Undo the exporter's bind-pose reflections before Blender creates its bones."""

import json
from pathlib import Path
from mathutils import Matrix  # pyright: ignore[reportMissingImports]

BIND_FLIP_ELEMENT = b"StellarBladeBindFlip"


def reference_bone_names(skeleton):
    filename = {
        "EVE": "CH_P_EVE_01_Skeleton.json",
        "LILY": "CH_NPC_01_Skeleton.json",
    }[skeleton]
    path = Path(__file__).with_name("sb-json") / filename
    with path.open(encoding="utf-8") as stream:
        reference = json.load(stream)[-1]["ReferenceSkeleton"]
    return set(reference["FinalNameToIndexMap"])


def restore_bind_poses(nodes, flip_flags, reference_names, log):
    # The export fix right-multiplies by this reflection. Its inverse is itself.
    reflection = Matrix.Diagonal((-1.0, -1.0, -1.0, 1.0))
    restored = 0
    legacy = 0
    for node_id, node in nodes.items():
        if not node.is_bone or node.bind_matrix is None:
            continue
        flag = flip_flags.get(node_id)
        if flag is not None:
            should_restore = flag == 1
            method = "export metadata"
        elif node.fbx_name in reference_names:
            # Older exports have no marker. Their Model transforms are untouched
            # by the export fix, while BindPose/TransformLink can be reflected.
            # Compare global handedness, including any armature/object reflection.
            bind_det = node.bind_matrix.to_3x3().determinant()
            model_det = node.get_world_matrix().to_3x3().determinant()
            should_restore = bind_det * model_det < 0.0
            method = "legacy transform comparison"
        else:
            continue
        if should_restore:
            node.bind_matrix = node.bind_matrix @ reflection
            restored += 1
            legacy += flag is None
            log(f'    Restored "{node.fbx_name}" ({method}).')
    log(f"[Stellar Blade import] Restored {restored} bone bind poses; {legacy} identified from legacy transforms.")
    return restored
