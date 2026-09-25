"""Run with Blender --background --factory-startup --python this_file."""
import ast
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import tempfile

import bpy
from mathutils import Matrix

folder = Path(__file__).resolve().parents[1] / 'addon'
output_directory = tempfile.TemporaryDirectory(prefix='stellar_blade_roundtrip_')
output = Path(output_directory.name)
spec = importlib.util.spec_from_file_location('stellar_test', folder / '__init__.py', submodule_search_locations=[str(folder)])
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
addon.register()
from stellar_test import export_fbx_bin, parse_fbx
from stellar_test.stellar_blade_import import restore_bind_poses, reference_bone_names

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def snapshot():
    arm = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
    bones = {bone.name: bone.matrix_local.copy() for bone in arm.data.bones}
    pose = {bone.name: bone.matrix.copy() for bone in arm.pose.bones}
    graph = bpy.context.evaluated_depsgraph_get()
    meshes = []
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
            assert len(obj.data.materials) == 1, 'Material assignment was lost'
            shader = PrincipledBSDFWrapper(obj.data.materials[0], is_readonly=True)
            assert shader.node_principled_bsdf is not None
            assert max(abs(a-b) for a,b in zip(shader.base_color, (0.2, 0.4, 0.6))) < 0.0001
            assert abs(shader.metallic - 0.25) < 0.0001
            assert abs(shader.roughness - 0.35) < 0.0001
            evaluated = obj.evaluated_get(graph)
            mesh = evaluated.to_mesh()
            meshes.append([evaluated.matrix_world @ vertex.co for vertex in mesh.vertices])
            evaluated.to_mesh_clear()
    return bones, pose, meshes

def compare(expected, actual):
    for left, right in zip(expected[:2], actual[:2]):
        assert left.keys() == right.keys()
        for name in left:
            error = max(abs(left[name][i][j] - right[name][i][j]) for i in range(4) for j in range(4))
            assert error < 0.0002, (name, error)
    for left, right in zip(expected[2], actual[2]):
        assert len(left) == len(right)
        assert max((a-b).length for a, b in zip(left, right)) < 0.0002

clear_scene()
arm_data = bpy.data.armatures.new('TestRig')
arm = bpy.data.objects.new('TestRig', arm_data)
bpy.context.collection.objects.link(arm)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
skeleton = 'LILY' if '--lily' in sys.argv else 'EVE'
names = (['Bip001-R-Finger0Nub', 'Bip001-R-Finger1Nub', 'Bip001-R-Finger2Nub', 'UnrelatedBone']
         if skeleton == 'LILY' else ['Dm-R-Breast-Point', 'Dm-R-Breast', 'Ab-R-Breast-Link', 'UnrelatedBone'])
if '--mirrored' in sys.argv:
    names[0] = 'Bip001' if skeleton == 'LILY' else 'Root'
parent = None
for index, name in enumerate(names):
    bone = arm_data.edit_bones.new(name)
    bone.head = (index * 0.2, index, 0.1 * index)
    bone.tail = (index * 0.2 + 0.1, index + 0.8, 0.3 + index * 0.1)
    bone.roll = 0.2 * index
    bone.parent = parent
    parent = bone
bpy.ops.object.mode_set(mode='OBJECT')
for mesh_index in range(2):
    data = bpy.data.meshes.new(f'TestMesh{mesh_index}')
    data.from_pydata([(0,0,0), (1,1,0), (0,2,1), (1,3,1)], [], [(0,1,2),(1,2,3)])
    obj = bpy.data.objects.new(data.name, data)
    bpy.context.collection.objects.link(obj)
    material = bpy.data.materials.new(f'TestMaterial{mesh_index}')
    from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
    shader = PrincipledBSDFWrapper(material, is_readonly=False)
    shader.base_color = (0.2, 0.4, 0.6)
    shader.metallic = 0.25
    shader.roughness = 0.35
    obj.data.materials.append(material)
    obj.parent = arm
    mod = obj.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    for index, name in enumerate(names):
        obj.vertex_groups.new(name=name).add([index], 1.0, 'REPLACE')
    obj.select_set(True)

if '--mirrored' in sys.argv:
    arm.scale = (-1, 1, 1)
    bpy.context.view_layer.update()

animated = '--animation' in sys.argv
if animated:
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 3
    for frame, angle in ((1, 0.0), (3, 0.4)):
        bpy.context.scene.frame_set(frame)
        arm.pose.bones[names[1]].rotation_mode = 'XYZ'
        arm.pose.bones[names[1]].rotation_euler.z = angle
        arm.pose.bones[names[1]].keyframe_insert(data_path='rotation_euler', frame=frame)
    bpy.context.scene.frame_set(1)

fixed_path = output / 'fixed.fbx'
control_path = output / 'control.fbx'
legacy_path = output / 'legacy.fbx'
assert bpy.ops.export_scene.stellar_blade_fbx(filepath=str(fixed_path), use_selection=True, bake_anim=animated, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, stellar_blade_show_log=False, stellar_blade_skeleton=skeleton) == {'FINISHED'}

# Control file: same export pipeline, with the reflection condition disabled.
original = export_fbx_bin.fbx_data_bindpose_element
tree = ast.parse((folder / 'export_fbx_bin.py').read_text())
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == original.__name__)
for node in ast.walk(function):
    if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == 'should_flip':
        node.test = ast.Constant(False)
ast.fix_missing_locations(function)
exec(compile(ast.Module(body=[function], type_ignores=[]), '<control-export>', 'exec'), export_fbx_bin.__dict__)
try:
    assert bpy.ops.export_scene.stellar_blade_fbx(filepath=str(control_path), use_selection=True, bake_anim=animated, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, stellar_blade_show_log=False, stellar_blade_skeleton=skeleton) == {'FINISHED'}
finally:
    export_fbx_bin.fbx_data_bindpose_element = original

# Generate a legacy file using the real exporter without the new metadata.
parsed, version = parse_fbx.parse(str(fixed_path))
def count_flips(node):
    return sum((child.props[0] if child.id == b'StellarBladeBindFlip' else count_flips(child)) for child in node.elems)
assert count_flips(parsed) > 0, 'Fixture must actually exercise bone flips'
original_int_writer = export_fbx_bin.elem_data_single_int32
def legacy_int_writer(parent, name, value):
    if name != b'StellarBladeBindFlip':
        return original_int_writer(parent, name, value)
export_fbx_bin.elem_data_single_int32 = legacy_int_writer
try:
    assert bpy.ops.export_scene.stellar_blade_fbx(filepath=str(legacy_path), use_selection=True, bake_anim=animated, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, stellar_blade_show_log=False, stellar_blade_skeleton=skeleton) == {'FINISHED'}
finally:
    export_fbx_bin.elem_data_single_int32 = original_int_writer

results = []
for path in (control_path, fixed_path, legacy_path):
    clear_scene()
    assert bpy.ops.import_scene.stellar_blade_fbx(filepath=str(path), use_anim=animated, stellar_blade_show_log=False, stellar_blade_skeleton=skeleton) == {'FINISHED'}
    samples = []
    for frame in ((1, 2, 3) if animated else (1,)):
        bpy.context.scene.frame_set(frame)
        samples.append(snapshot())
    results.append(samples)
for control, fixed, legacy in zip(*results):
    compare(control, fixed)
    compare(control, legacy)

# Metadata also disambiguates intentionally reflected poses and unknown bone names.
original_matrix = Matrix.Translation((2, 3, 4)) @ Matrix.Rotation(0.4, 4, 'Z')
reflection = Matrix.Diagonal((-1, -1, -1, 1))
node = SimpleNamespace(is_bone=True, bind_matrix=original_matrix @ reflection,
                       fbx_name='UnknownName', get_world_matrix=lambda: original_matrix @ reflection)
assert restore_bind_poses({1: node}, {1: 1}, set(), lambda message: None) == 1
assert max(abs(node.bind_matrix[i][j]-original_matrix[i][j]) for i in range(4) for j in range(4)) < 1e-6
assert restore_bind_poses({1: node}, {1: 0}, set(), lambda message: None) == 0
assert reference_bone_names('EVE') and reference_bone_names('LILY')
print('PASS: real FBX round trip matches uncorrected control: rest matrices, pose matrices and skinned vertices; legacy FBX, multi-mesh parent chains, metadata and both skeleton references.')

# Leave unknown bones and already-restored legacy bind poses unchanged.
assert restore_bind_poses({1: node}, {}, set(), lambda message: None) == 0
node.get_world_matrix = lambda: original_matrix
assert restore_bind_poses({1: node}, {}, {'UnknownName'}, lambda message: None) == 0
output_directory.cleanup()
