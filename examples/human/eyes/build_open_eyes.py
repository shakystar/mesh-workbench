"""Create fitted open eyes on the included procedural ear-stage model."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').exists())
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import eye_socket,sculpt
from mesh_workbench.runner import camera


def eye_material():
    material=bpy.data.materials.new('Procedural sclera iris pupil')
    material.use_nodes=True
    nodes=material.node_tree.nodes;links=material.node_tree.links
    bsdf=nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value=.26
    tex=nodes.new('ShaderNodeTexCoord')
    split=nodes.new('ShaderNodeSeparateXYZ');links.new(tex.outputs['Generated'],split.inputs[0])
    combine=nodes.new('ShaderNodeCombineXYZ')
    links.new(split.outputs['X'],combine.inputs['X']);links.new(split.outputs['Z'],combine.inputs['Z'])
    distance=nodes.new('ShaderNodeVectorMath');distance.operation='DISTANCE'
    distance.inputs[1].default_value=(.5,0,.5);links.new(combine.outputs[0],distance.inputs[0])
    ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.interpolation='LINEAR'
    colors=[(0,(.008,.011,.013,1)),(.075,(.008,.011,.013,1)),
            (.082,(.07,.11,.12,1)),(.16,(.12,.18,.19,1)),
            (.175,(.035,.055,.06,1)),(.19,(.65,.69,.68,1)),(1,(.65,.69,.68,1))]
    r=ramp.color_ramp;r.elements.remove(r.elements[1])
    r.elements[0].position=0;r.elements[0].color=colors[0][1]
    for position,color in colors[1:]:r.elements.new(position).color=color
    links.new(distance.outputs['Value'],ramp.inputs[0]);links.new(ramp.outputs['Color'],bsdf.inputs['Base Color'])
    return material


def run(source_path, output_path):
    folder=Path(output_path).resolve()
    if folder.exists():raise ValueError('Use a fresh output folder')
    bpy.ops.wm.open_mainfile(filepath=str(Path(source_path).resolve()))
    source=bpy.data.objects['Fitted ear guides']
    before=sculpt.coordinates(source)
    settings=[dict(center_xz=[sign*.032,1.645],width_mm=28,upper_mm=6,lower_mm=4,
                   radius_mm=15,tilt_degrees=sign*2,yaw_degrees=sign*25) for sign in (-1,1)]
    # Invalid controls must fail before mutation; late second-eye failure is atomic.
    objects=set(bpy.data.objects);meshes=set(bpy.data.meshes)
    bad=[dict(settings[0],radius_mm=10)]
    for invalid in (bad,[settings[0],settings[0]], [settings[0],dict(settings[1],center_xz=[.4,1.645])]):
        try:eye_socket.build(source,invalid,'Must roll back')
        except ValueError:pass
        else:raise AssertionError('Invalid eye request accepted')
        assert set(bpy.data.objects)==objects and set(bpy.data.meshes)==meshes
    head,balls,report=eye_socket.build(source,settings)
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    after=sculpt.coordinates(head)
    # Points outside the two local patches retain their exact world coordinates.
    expected=before[(np.abs(before[:,0])>.057)|(before[:,2]<1.624)|(before[:,2]>1.667)|(before[:,1]>-.025)]
    retained={tuple(p) for p in after}
    assert all(tuple(p) in retained for p in expected)
    assert all(eye['removed_faces']>0 for eye in report['eyes'])
    report.update(blender=bpy.app.version_string,protected_vertices=len(expected),
                  failure_cases=3,late_failure_atomic=True,
                  limits='Static authored eyes; no rig, tear duct, corneal optics or anatomical validation.')
    material=eye_material()
    for ball in balls:ball.data.materials.append(material)
    source.hide_render=True;source.hide_set(True)
    folder.mkdir(parents=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
    # Save the actual model used for both preview views.
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'open-eyes.blend'))
    print('OPEN_EYES_GEOMETRY_PASS',json.dumps(report),flush=True)
    for view,pos in [('front',(0,-4,1.65)),('three-quarter',(2.5,-4,1.65))]:
        camera(position=pos,target=(0,-.005,1.64),scale=.29,size=(900,900))
        scene.cycles.samples=24;scene.cycles.use_denoising=True
        scene.render.filepath=str(folder/(view+'.png'))
        bpy.ops.render.render(write_still=True)
    print('OPEN_EYES_PREVIEW_COMPLETE',flush=True)


if __name__=='__main__':run(*sys.argv[sys.argv.index('--')+1:])
