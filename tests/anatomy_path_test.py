"""Focused Blender check: front path registration, occlusion and atomic failures."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mesh_workbench import anatomy,sculpt


def run():
    n=41;vertices=[];faces=[]
    for y in (0,.005):
        base=len(vertices)
        vertices.extend((x,y,z) for z in np.linspace(-.02,.02,n) for x in np.linspace(-.02,.02,n))
        for j in range(n-1):
            for i in range(n-1):
                k=base+j*n+i;faces.append((k,k+1,k+n+1,k+n))
    mesh=bpy.data.meshes.new('Path sheets');mesh.from_pydata(vertices,[],faces)
    obj=bpy.data.objects.new('Path sheets',mesh);bpy.context.collection.objects.link(obj)
    spec={'units':'m','landmarks':{'left':[-.01,0,0],'right':[.01,0,0],
          'outside':[.018,0,0],'miss':[.04,0,0]},
          'regions':{'patch':{'min':[-.015,-.01,-.01],'max':[.015,.01,.01],'feather':.002}}}
    anatomy.bind(obj,spec)
    command={'anchors':['left','right'],'region':'patch','radius_mm':3,'distance_mm':1,'max_displacement_mm':1}
    original=sculpt.coordinates(obj)
    report=anatomy.path_stroke(obj,command);after=sculpt.coordinates(obj)
    np.testing.assert_array_equal(after[n*n:],original[n*n:])
    protected=(np.abs(original[:,0])>=.015)|(np.abs(original[:,2])>=.01)
    np.testing.assert_array_equal(after[protected],original[protected])
    center=n//2*n+n//2
    assert abs((after[center,1]-original[center,1])+.001)<1e-8
    assert np.linalg.norm(after-original,axis=1).max()<=.00100001
    sculpt.set_layer(obj,report['layer'],0)
    np.testing.assert_allclose(sculpt.coordinates(obj),original,atol=1e-8)
    count=len(obj.data.shape_keys.key_blocks)
    invalid=[{'distance_mm':2},{'anchors':['left','left']},
             {'anchors':['left','outside']},{'anchors':['left','miss']},
             {'radius_mm':float('nan')},{'distance_mm':0}]
    for change in invalid:
        try:anatomy.path_stroke(obj,{**command,**change})
        except ValueError:pass
        else:raise AssertionError('Invalid path accepted: '+str(change))
        assert len(obj.data.shape_keys.key_blocks)==count
        np.testing.assert_allclose(sculpt.coordinates(obj),original,atol=1e-8)
    obj.location.x=.01
    try:anatomy.path_stroke(obj,command)
    except ValueError:pass
    else:raise AssertionError('Stale registration accepted')
    print('ANATOMY_PATH_PASS',json.dumps({'rear_sheet_protected':True,'rollback':True,
          'bounded_effect':True,'atomic_failures':len(invalid),'stale_rejected':True}),flush=True)


if __name__=='__main__':run()
