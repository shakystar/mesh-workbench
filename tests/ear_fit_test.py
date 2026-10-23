"""Ear proportions, opposite/occluded sheets, side direction and front compatibility."""
import copy
import json
import sys
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from mesh_workbench import anatomy,anatomy_fit,sculpt
from anatomy_path_test import run as front_check


def fixture(name,half,height):
    verts=[];faces=[];hidden=[];n,m=61,81
    def point(sign,y,z,inset=0):return [sign*(.08+.003*(y/half)**2+.002*((z-1.64)/height)**2-inset),y,z]
    for sign in (-1,1):
        for inset in (0,.004):
            start=len(verts)
            verts.extend(point(sign,y,z,inset) for z in np.linspace(1.64-height*1.4,1.64+height*1.4,m)
                         for y in np.linspace(-half*1.5,half*1.5,n))
            hidden.extend([inset!=0]*(n*m))
            for j in range(m-1):
                for i in range(n-1):
                    k=start+j*n+i;faces.append((k,k+1,k+n+1,k+n))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces)
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    targets=[]
    for sign,side in [(-1,'negative_x'),(1,'positive_x')]:
        targets.append({'units':'m','knowledge_id':'auricle-v1','side':side,'landmarks':{
            'anterior':point(sign,-half,1.64),'posterior':point(sign,half,1.64),
            'superior':point(sign,0,1.64+height),'inferior':point(sign,0,1.64-height)}})
    return obj,targets,np.array(hidden)


def run():
    folder=ROOT/'runs/ear-fit'
    if folder.exists():raise ValueError('Use a fresh runs/ear-fit directory')
    kb=anatomy_fit.knowledge('auricle-v1')
    assert all(f['source'] in kb['sources'] for f in kb['features'].values())
    results=[]
    for name,half,height in [('small ears',.009,.022),('large ears',.013,.028)]:
        source,targets,hidden=fixture(name,half,height);before=sculpt.coordinates(source)
        result,diagrams,reports=anatomy_fit.apply_many(source,targets,name+' fitted')
        after=sculpt.coordinates(result)
        np.testing.assert_array_equal(before,sculpt.coordinates(source))
        np.testing.assert_array_equal(before[hidden],after[hidden])
        np.testing.assert_array_equal(before[:,1:],after[:,1:])
        editable=np.zeros(len(before),dtype=bool)
        for d in diagrams:
            r=next(iter(d['regions'].values()))
            editable|=np.all((before>=r['min'])&(before<=r['max']),axis=1)
        np.testing.assert_array_equal(before[~editable],after[~editable])
        assert len(reports)==12 and all(r['changed_vertices'] for r in reports)
        # Disable the second side: the opposite surface must return exactly.
        for r in reports[6:]:sculpt.set_layer(result,r['layer'],0)
        one=sculpt.coordinates(result);np.testing.assert_allclose(before[before[:,0]>0],one[before[:,0]>0],atol=1e-8)
        for r in reports[:6]:
            assert r['max_displacement_mm']<=r['command']['max_displacement_mm']+1e-5
            sculpt.set_layer(result,r['layer'],0)
        np.testing.assert_allclose(before,sculpt.coordinates(result),atol=1e-8)
        # Isolate a positive helix stroke on each side and check outward direction.
        for index,sign in [(0,-1),(6,1)]:
            sculpt.set_layer(result,reports[index]['layer'],1)
            delta=sculpt.coordinates(result)-before
            assert np.max(delta[:,0]*sign)>.0001 and np.min(delta[:,0]*sign)>-1e-8
            sculpt.set_layer(result,reports[index]['layer'],0)
        for r in reports:sculpt.set_layer(result,r['layer'],1)
        results.append({'fixture':name,'hidden_vertices_unchanged':int(hidden.sum()),
            'protected_vertices':int((~editable).sum()),'source_preserved':True,'rollback':True,
            'maximum_mm':float(np.linalg.norm(after-before,axis=1).max()*1000)})
    bad=[]
    t=copy.deepcopy(targets);t[1]['side']='negative_x';bad.append(t)
    t=copy.deepcopy(targets);t[1]['landmarks']['anterior'][1]=.1;bad.append(t)
    t=copy.deepcopy(targets);t[1]['landmarks']['superior'][2]=1.63;bad.append(t)
    t=copy.deepcopy(targets);t[1]['landmarks']['posterior'][0]+=.03;bad.append(t)
    t=copy.deepcopy(targets);del t[1]['landmarks']['inferior'];bad.append(t)
    t=copy.deepcopy(targets);t[1]['landmarks']['superior'][1]=float('nan');bad.append(t)
    snapshot=(set(bpy.data.objects.keys()),set(bpy.data.meshes.keys()))
    for t in bad:
        try:anatomy_fit.apply_many(source,t,'Rejected ears')
        except ValueError:pass
        else:raise AssertionError('Invalid ear reference accepted')
        assert snapshot==(set(bpy.data.objects.keys()),set(bpy.data.meshes.keys()))
        np.testing.assert_array_equal(before,sculpt.coordinates(source))
    # Modified common path projection must retain its existing front semantics.
    front_check()
    folder.mkdir(parents=True)
    report={'blender':bpy.app.version_string,'fixtures':results,'invalid_batches':len(bad),
            'front_path_check':True,'scope':'Side surface relief; no canal or anatomical validation.'}
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'ear-fixtures.blend'))
    print('EAR_FIT_PASS',json.dumps(report),flush=True)


if __name__=='__main__':run()
