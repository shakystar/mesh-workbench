"""Focused bilateral periorbital fitting and multi-region transaction checks."""
import copy
import json
import sys
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from mesh_workbench import anatomy,anatomy_fit,sculpt
from anatomy_fit_test import fixture as oral_fixture


def fixture(name,half,upper,lower,tilt):
    nx,nz=131,101
    def point(x,z):return [x,-.08+.02*(x/.09)**2+.005*((z-1.67)/.06)**2,z]
    verts=[point(x,z) for z in np.linspace(1.62,1.73,nz) for x in np.linspace(-.09,.09,nx)]
    faces=[]
    for j in range(nz-1):
        for i in range(nx-1):
            k=j*nx+i;faces.append((k,k+1,k+nx+1,k+nx))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces)
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    targets=[]
    for side,sign in [('negative_x',-1),('positive_x',1)]:
        center=np.array([sign*.035,1.67]);axis=np.array([sign*np.cos(tilt),np.sin(tilt)])
        up=np.array([-axis[1],axis[0]])
        if up[1]<0:up=-up
        coords={'medial_canthus':center-axis*half,'lateral_canthus':center+axis*half,
                'upper_lid':center+up*upper,'lower_lid':center-up*lower}
        targets.append({'units':'m','knowledge_id':'periorbital-v1','side':side,
                        'landmarks':{k:point(*p) for k,p in coords.items()}})
    return obj,targets


def run():
    folder=ROOT/'runs/human/orbital-fit'
    if folder.exists():raise ValueError('Use a fresh runs/human/orbital-fit directory')
    kb=anatomy_fit.knowledge('periorbital-v1')
    assert all(f['source'] in kb['sources'] for f in kb['features'].values())
    assert all(a in kb['features'] and b in kb['features'] for a,_,b in kb['relations'])
    results=[]
    for name,half,upper,lower,tilt in [('narrow eyes',.012,.004,.003,0),('wide tilted eyes',.017,.0055,.004,.12)]:
        source,targets=fixture(name,half,upper,lower,tilt)
        source.shape_key_add(name='Basis');key=source.shape_key_add(name='Existing lower-face edit')
        for p in key.data:
            if p.co.z<1.645:p.co.y-=.0003
        key.value=1
        before=sculpt.coordinates(source)
        obj,diagrams,reports=anatomy_fit.apply_many(source,targets,name+' fitted')
        after=sculpt.coordinates(obj);editable=np.zeros(len(before),dtype=bool)
        assert len(reports)==10 and all(r['changed_vertices'] for r in reports)
        for d in diagrams:
            region=next(iter(d['regions'].values()))
            editable|=np.all((before>=region['min'])&(before<=region['max']),axis=1)
            for name in kb['required_target_landmarks']:
                np.testing.assert_allclose(np.array(d['landmarks'][name])[[0,2]],
                    np.array(d['registration']['target']['landmarks'][name])[[0,2]],atol=1e-7)
        np.testing.assert_array_equal(before[~editable],after[~editable])
        np.testing.assert_array_equal(before[before[:,2]<1.645],after[before[:,2]<1.645])
        np.testing.assert_array_equal(before,sculpt.coordinates(source))
        assert key.value==1
        for r in reports:
            assert r['max_displacement_mm']<=r['command']['max_displacement_mm']+1e-5
            sculpt.set_layer(obj,r['layer'],0)
        np.testing.assert_allclose(before,sculpt.coordinates(obj),atol=1e-8)
        for r in reports:sculpt.set_layer(obj,r['layer'],1)
        assert np.linalg.norm(after-before,axis=1).max()>.0002
        assert len(json.loads(obj['mw_anatomy_fits']))==2
        results.append({'fixture':source.name,'protected_vertices':int((~editable).sum()),
                        'maximum_mm':float(np.linalg.norm(after-before,axis=1).max()*1000),
                        'source_preserved':True,'rollback':True,'paths':len(reports)})
    bad=[]
    t=copy.deepcopy(targets);del t[1]['landmarks']['upper_lid'];bad.append(t)
    t=copy.deepcopy(targets);t[1]['side']='negative_x';bad.append(t)
    t=copy.deepcopy(targets);t[1]['landmarks']['lower_lid'][2]=1.69;bad.append(t)
    t=copy.deepcopy(targets);t[1]['landmarks']['upper_lid'][1]+=.03;bad.append(t)
    t=copy.deepcopy(targets);t[1]['units']='cm';bad.append(t)
    t=copy.deepcopy(targets);t[1]['landmarks']['lateral_canthus'][2]+=.02;bad.append(t)
    t=copy.deepcopy(targets);t[1]['landmarks']['upper_lid'][0]=float('nan');bad.append(t)
    bad.append([targets[0],targets[0]])
    snapshot=(set(bpy.data.objects.keys()),set(bpy.data.meshes.keys()))
    for targets_bad in bad:
        try:anatomy_fit.apply_many(source,targets_bad,'Rejected eyes')
        except ValueError:pass
        else:raise AssertionError('Invalid eye targets accepted')
        assert snapshot==(set(bpy.data.objects.keys()),set(bpy.data.meshes.keys()))
        np.testing.assert_array_equal(before,sculpt.coordinates(source))
    # Fail after the first eye has actually changed: the entire result must vanish.
    real=anatomy.path_stroke;calls=0
    def fail_second_eye(obj,command):
        nonlocal calls
        calls+=1
        if calls==6:raise ValueError('Injected second-eye failure')
        return real(obj,command)
    anatomy.path_stroke=fail_second_eye
    try:
        try:anatomy_fit.apply_many(source,targets,'Partial eyes')
        except ValueError:pass
        else:raise AssertionError('Injected failure missing')
    finally:anatomy.path_stroke=real
    assert calls==6 and snapshot==(set(bpy.data.objects.keys()),set(bpy.data.meshes.keys()))
    np.testing.assert_array_equal(before,sculpt.coordinates(source))
    # The original single-region public API still returns one diagram and works.
    old,old_target=oral_fixture('Oral compatibility',.021,.024,.017,.3)
    old_before=sculpt.coordinates(old)
    single,d,rs=anatomy_fit.apply(old,old_target,'Oral compatibility result')
    assert isinstance(d,dict) and len(rs)==7
    np.testing.assert_array_equal(old_before,sculpt.coordinates(old))
    for r in rs:sculpt.set_layer(single,r['layer'],0)
    np.testing.assert_allclose(old_before,sculpt.coordinates(single),atol=1e-8)
    folder.mkdir(parents=True)
    report={'blender':bpy.app.version_string,'fixtures':results,'invalid_batches':len(bad),
            'late_failure_atomic':True,'single_oral_api':True,
            'scope':'Surface fixtures only; no eyeball, open aperture or anatomical validation.'}
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'orbital-fixtures.blend'))
    print('ORBITAL_FIT_PASS',json.dumps(report),flush=True)


if __name__=='__main__':run()
