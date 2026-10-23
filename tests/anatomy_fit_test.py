"""Two proportion fixtures: KB fitting, atomic failures, protection and rollback."""
import copy
import json
import sys
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import anatomy_fit,sculpt


def fixture(name,half,upper,lower,offset):
    nx,nz=101,91
    def point(x,z):return [offset+x,-.08+.018*(x/(half*2))**2+.006*(z/(upper*1.7))**2,1.5+z]
    vertices=[point(x,z) for z in np.linspace(-lower*1.8,upper*1.5,nz)
              for x in np.linspace(-half*2,half*2,nx)]
    faces=[]
    for j in range(nz-1):
        for i in range(nx-1):
            k=j*nx+i;faces.append((k,k+1,k+nx+1,k+nx))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces)
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    target={'units':'m','landmarks':{'corner_left':point(-half,0),'corner_right':point(half,0),
            'nose_base':point(0,upper),'chin_fold':point(0,-lower)}}
    return obj,target


def run():
    folder=ROOT/'runs/human/anatomy-fit'
    if folder.exists():raise ValueError('Use fresh runs/human/anatomy-fit directory')
    results=[];diagrams=[]
    kb=anatomy_fit.knowledge()
    assert all(f['source'] in kb['sources'] for f in kb['features'].values())
    known=set(kb['features'])
    assert all(a in known and b in known for a,_,b in kb['relations'])
    for name,half,upper,lower,offset,bow in [('narrow',.021,.024,.017,0,1),('wide',.029,.030,.024,.2,1.2)]:
        source,target=fixture(name,half,upper,lower,offset)
        original=sculpt.coordinates(source)
        output,diagram,reports=anatomy_fit.apply(source,target,name+' fitted',bow_width=bow)
        after=sculpt.coordinates(output)
        np.testing.assert_array_equal(sculpt.coordinates(source),original)
        region=diagram['regions']['mouth'];lo=np.array(region['min']);hi=np.array(region['max'])
        protected=~np.all((original>=lo)&(original<=hi),axis=1)
        np.testing.assert_array_equal(original[protected],after[protected])
        for r in reports:sculpt.set_layer(output,r['layer'],0)
        np.testing.assert_allclose(original,sculpt.coordinates(output),atol=1e-8)
        for r in reports:sculpt.set_layer(output,r['layer'],1)
        assert all(r['changed_vertices']>0 for r in reports)
        assert np.linalg.norm(after-original,axis=1).max()>.0005
        for r in reports:assert r['max_displacement_mm']<=r['command']['max_displacement_mm']+1e-5
        np.testing.assert_allclose(np.array(diagram['landmarks']['corner_right'])[[0,2]],
                                   np.array(target['landmarks']['corner_right'])[[0,2]],atol=1e-8)
        assert abs(diagram['landmarks']['bow_right'][0]-offset-half*kb['landmarks_uv']['bow_right'][0]*bow)<1e-7
        results.append({'fixture':name,'protected_vertices':int(protected.sum()),'source_preserved':True,
                        'rollback':True,'paths':len(reports),'maximum_mm':float(np.linalg.norm(after-original,axis=1).max()*1000)})
        diagrams.append(diagram)
    # Each failed application must leave both scene datablocks and input state intact.
    bad=[]
    t=copy.deepcopy(target);del t['landmarks']['nose_base'];bad.append(t)
    t=copy.deepcopy(target);t['units']='cm';bad.append(t)
    t=copy.deepcopy(target);t['landmarks']['corner_left'],t['landmarks']['corner_right']=t['landmarks']['corner_right'],t['landmarks']['corner_left'];bad.append(t)
    t=copy.deepcopy(target);t['landmarks']['nose_base'][2]=1.49;bad.append(t)
    t=copy.deepcopy(target);t['landmarks']['chin_fold'][1]+=.05;bad.append(t)
    t=copy.deepcopy(target);t['landmarks']['nose_base'][0]=float('nan');bad.append(t)
    t=copy.deepcopy(target);t['landmarks']['corner_right'][2]+=.01;bad.append(t)
    t=copy.deepcopy(target)
    for p in t['landmarks'].values():p[0]+=1
    bad.append(t)
    scene_before=(set(bpy.data.objects.keys()),set(bpy.data.meshes.keys()))
    for t in bad:
        try:anatomy_fit.apply(source,t,'Should not survive')
        except ValueError:pass
        else:raise AssertionError('Invalid target accepted')
        assert scene_before==(set(bpy.data.objects.keys()),set(bpy.data.meshes.keys()))
        np.testing.assert_array_equal(sculpt.coordinates(source),original)
    folder.mkdir(parents=True)
    report={'blender':bpy.app.version_string,'fixtures':results,'atomic_failures':len(bad),
            'scope':'Two curved surface fixtures; not full-body or anatomical accuracy validation.'}
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    (folder/'registered-diagrams.json').write_text(json.dumps(diagrams,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'proportion-fixtures.blend'))
    print('ANATOMY_FIT_PASS',json.dumps(report),flush=True)


if __name__=='__main__':run()
