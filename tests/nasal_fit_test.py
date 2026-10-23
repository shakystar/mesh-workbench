"""Focused nasal knowledge, shared oral reference and two-proportion checks."""
import copy
import json
import sys
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tests'))
from mesh_workbench import anatomy_fit,sculpt
from anatomy_fit_test import fixture


def run():
    folder=ROOT/'runs/nasal-fit'
    if folder.exists():raise ValueError('Use a fresh runs/nasal-fit directory')
    kb=anatomy_fit.knowledge('nasal-base-v1')
    assert all(v['source'] in kb['sources'] for v in kb['features'].values())
    assert all(a in kb['features'] and b in kb['features'] for a,_,b in kb['relations'])
    assert kb['shared_anchors']['nose_base']['module']=='oral-neutral-v1'
    results=[];diagrams=[]
    for name,half,height,offset in [('narrow nose',.014,.018,0),('wide nose',.022,.026,.2)]:
        source,oral_fixture=fixture(name,half,height,.012,offset)
        # The old oral default still compiles unchanged through the shared code.
        oral=anatomy_fit.compile_diagram(source,oral_fixture)
        assert oral['registration']['knowledge_id']=='oral-neutral-v1'
        assert len(oral['paths'])==7 and set(oral['regions'])=={'mouth'}
        def point(x,z):return [offset+x,-.08+.018*(x/(half*2))**2+.006*(z/(height*1.7))**2,1.5+z]
        target={'units':'m','knowledge_id':'nasal-base-v1','landmarks':{
            'ala_left':point(-half,height*.3),'ala_right':point(half,height*.3),
            'nose_base':point(0,0),'nose_tip':point(0,height),'philtrum_top':point(0,-.006)},
            'linked_oral_target':{'units':'m','landmarks':{'nose_base':point(0,0),
                'corner_left':point(-half,-.015),'corner_right':point(half,-.015)}}}
        # Existing lower-face deformation must survive the new snapshot and edits.
        source.shape_key_add(name='Basis');key=source.shape_key_add(name='Existing mouth relief')
        for p in key.data:
            if p.co.z<1.49:p.co.y-=.0004
        key.value=1
        original=sculpt.coordinates(source)
        output,diagram,reports=anatomy_fit.apply(source,target,name+' fitted')
        after=sculpt.coordinates(output)
        np.testing.assert_array_equal(original,sculpt.coordinates(source))
        assert source.data.shape_keys.key_blocks['Existing mouth relief'].value==1
        below=original[:,2]<=1.5
        np.testing.assert_array_equal(original[below],after[below])
        region=diagram['regions']['nasal_base'];lo=np.array(region['min']);hi=np.array(region['max'])
        protected=~np.all((original>=lo)&(original<=hi),axis=1)
        np.testing.assert_array_equal(original[protected],after[protected])
        assert len(reports)==6 and all(r['changed_vertices']>0 for r in reports)
        assert np.linalg.norm(after-original,axis=1).max()>.0002
        for r in reports:
            assert r['max_displacement_mm']<=r['command']['max_displacement_mm']+1e-5
            sculpt.set_layer(output,r['layer'],0)
        np.testing.assert_allclose(original,sculpt.coordinates(output),atol=1e-8)
        for r in reports:sculpt.set_layer(output,r['layer'],1)
        assert diagram['registration']['shared_oral_reference_checked']
        results.append({'fixture':name,'protected_vertices':int(protected.sum()),
            'oral_vertices_unchanged':int(below.sum()),'source_preserved':True,'rollback':True,
            'maximum_mm':float(np.linalg.norm(after-original,axis=1).max()*1000)})
        diagrams.append(diagram)
    bad=[]
    t=copy.deepcopy(target);del t['landmarks']['philtrum_top'];bad.append(t)
    t=copy.deepcopy(target);t['landmarks']['nose_tip'][2]=1.49;bad.append(t)
    t=copy.deepcopy(target);t['landmarks']['ala_left'][0]=t['landmarks']['ala_right'][0];bad.append(t)
    t=copy.deepcopy(target);t['landmarks']['nose_base'][1]+=.05;bad.append(t)
    t=copy.deepcopy(target);t['linked_oral_target']['landmarks']['nose_base'][2]+=.001;bad.append(t)
    t=copy.deepcopy(target);t['linked_oral_target']['landmarks']['corner_left'][2]=1.6;bad.append(t)
    t=copy.deepcopy(target);t['knowledge_id']='../../invalid';bad.append(t)
    t=copy.deepcopy(target);t['landmarks']['ala_right'][2]+=.01;bad.append(t)
    scene=(set(bpy.data.objects.keys()),set(bpy.data.meshes.keys()))
    for t in bad:
        try:anatomy_fit.apply(source,t,'Rejected nasal result')
        except ValueError:pass
        else:raise AssertionError('Invalid nasal target accepted')
        assert scene==(set(bpy.data.objects.keys()),set(bpy.data.meshes.keys()))
        np.testing.assert_array_equal(original,sculpt.coordinates(source))
    folder.mkdir(parents=True)
    report={'blender':bpy.app.version_string,'fixtures':results,'atomic_failures':len(bad),
            'oral_default_compilation':True,'scope':'Front surface relief; no nostril cavity or anatomical accuracy validation.'}
    (folder/'verification.json').write_text(json.dumps(report,indent=2))
    (folder/'diagrams.json').write_text(json.dumps(diagrams,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'nasal-fixtures.blend'))
    print('NASAL_FIT_PASS',json.dumps(report),flush=True)


if __name__=='__main__':run()
