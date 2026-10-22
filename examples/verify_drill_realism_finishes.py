"""Reopen and read actual finish shader values and attached procedural marks."""
import hashlib
import json
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import nested,attachments


def inspect_current():
    state=nested.load(); finishes={}; marks={}
    for key,node in state['nodes'].items():
        if not node.get('visible',True):continue
        obj=bpy.data.objects[state['outputs'][key]['object']]
        style=node.get('material',{});expected=style.get('finish')
        if expected:
            slots=[]
            for index,mat in enumerate(obj.data.materials):
                actual=json.loads(mat.get('mw_finish','{}')) if mat else {}
                values=dict(expected,roughness=style.get('roughness',.4),slot=index,
                            mm_per_unit=bpy.context.scene.unit_settings.scale_length*1000)
                valid=all(abs(actual.get(k,-1)-v)<1e-6 if isinstance(v,(float,int)) else actual.get(k)==v for k,v in values.items())
                tree=mat.node_tree if mat else None
                shader=tree.nodes.get('Principled BSDF') if tree else None
                scales=[n for n in tree.nodes if n.bl_idname=='ShaderNodeVectorMath' and n.operation=='SCALE'] if tree else []
                offsets=[n for n in tree.nodes if n.bl_idname=='ShaderNodeVectorMath' and n.operation=='ADD'] if tree else []
                bumps=[n for n in tree.nodes if n.bl_idname=='ShaderNodeBump'] if tree else []
                ranges=[n for n in tree.nodes if n.bl_idname=='ShaderNodeMapRange'] if tree else []
                topology=bool(shader and len(scales)==len(offsets)==len(bumps)==len(ranges)==1)
                if topology:
                    mm=values['mm_per_unit'];seed=expected['seed'];rough=values['roughness'];variation=expected['variation']
                    valid=valid and abs(scales[0].inputs[3].default_value-mm/expected['grain_mm'])<1e-4
                    valid=valid and abs(bumps[0].inputs['Distance'].default_value-expected['bump_mm']/mm)<1e-6
                    valid=valid and all(abs(offsets[0].inputs[1].default_value[i]-(seed*f%104729)/101)<1e-5 for i,f in enumerate((17,43,71)))
                    valid=valid and abs(ranges[0].inputs['To Min'].default_value-(rough-variation))<1e-6 and abs(ranges[0].inputs['To Max'].default_value-(rough+variation))<1e-6
                    valid=valid and abs(shader.inputs['Metallic'].default_value-(1 if expected['role']=='metal' else 0))<1e-6
                    valid=valid and all(abs(shader.inputs['Base Color'].default_value[i]-c)<1e-6 for i,c in enumerate([*style['color'],1]))
                    valid=valid and shader.inputs['Normal'].is_linked and shader.inputs['Roughness'].is_linked and bumps[0].inputs['Height'].is_linked
                slots.append({'slot':index,'metadata':actual,'passed':bool(valid and topology)})
            finishes[key]={'slots':slots,'passed':bool(slots) and all(s['passed'] for s in slots)}
        if node['kind']=='surface_marking':
            marking=json.loads(obj.get('mw_marking','{}'));binding=json.loads(obj.get('mw_surface_paths','{}'))
            parent=bpy.data.objects.get(binding.get('source',''))
            current=bool(parent and binding['source_revision']==attachments.revision(parent) and attachments.resolve(parent,binding['binding']))
            args=nested._resolve(node['args'],state['parameters'])
            exact=all(marking.get(k)==v for k,v in args.items() if k not in ('projection_axis','side','max_distance'))
            exact=exact and all(marking.get('projection',{}).get(k)==args[k] for k in ('projection_axis','side','max_distance'))
            marks[key]={'text':marking.get('text'),'current_binding':current,'settings_match':exact,'passed':current and exact}
    return {'finishes':finishes,'markings':marks,'passed':bool(finishes) and bool(marks) and all(x['passed'] for x in [*finishes.values(),*marks.values()])}


def verify(source,output):
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),load_ui=False,use_scripts=False)
    report=inspect_current();report.update(blender=bpy.app.version_string,source_sha256=digest,source_preserved=digest==hashlib.sha256(source.read_bytes()).hexdigest())
    report['passed']=report['passed'] and report['source_preserved']
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    print('FINISH_MARKING_READBACK',report['passed'],len(report['finishes']),len(report['markings']),flush=True)
    if not report['passed']:raise ValueError('Persisted finish or marking readback failed')

if __name__=='__main__':
    verify(*map(Path,sys.argv[sys.argv.index('--')+1:]))
