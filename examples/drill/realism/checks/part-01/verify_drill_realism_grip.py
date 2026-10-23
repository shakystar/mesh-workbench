"""Check wrap connectivity, explicit CSG invalidation and rear-surface coverage."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)
import hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=_WORKSPACE;sys.path.insert(0,str(ROOT/'src'))
from mesh_workbench import assembly,geometry,nested,attachments


def verify(source,output):
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),load_ui=False,use_scripts=False)
    state=nested.load();spec_path=ROOT/'examples/drill/realism/recipes/part-01/drill-realism-grip-wrap-rays.json';spec=json.loads(spec_path.read_text());reports={}
    for side,roi in spec['rois'].items():
        obj=bpy.data.objects[state['outputs'][roi['blocker']]['object']]
        shell=bpy.data.objects[state['outputs']['housing_'+side]['object']]
        tree=assembly._tree(obj);shell_tree=assembly._tree(shell)
        adjacency={v.index:set() for v in obj.data.vertices}
        for edge in obj.data.edges:
            a,b=edge.vertices;adjacency[a].add(b);adjacency[b].add(a)
        remaining=set(adjacency);components=0
        while remaining:
            components+=1;stack=[remaining.pop()]
            while stack:
                neighbors=adjacency[stack.pop()]&remaining;remaining-=neighbors;stack.extend(neighbors)
        samples=[]
        for ray in roi['rays']:
            origin,direction=map(Vector,(ray['origin'],ray['direction']))
            hit=tree.ray_cast(origin,direction);skin=shell_tree.ray_cast(origin,direction)
            relief=skin[3]-hit[3] if hit[0] is not None and skin[0] is not None else None
            samples.append({'relief_along_ray_mm':relief,'passed':relief is not None and .1<=relief<=1.3})
        texture=bpy.data.objects[state['outputs']['texture_'+side]['object']]
        binding=json.loads(texture['mw_surface_paths'])
        support=bpy.data.objects[binding['source']]
        anchors=attachments.resolve(support,binding['binding'])
        distances=[tree.find_nearest(Vector(a['position']))[3] for a in anchors]
        rib_support=(bool(distances) and max(distances)<=.05 and
                     support.name==state['outputs']['grip_oval_'+side]['object'])
        info=geometry.inspect(obj);transfer=json.loads(obj.get('mw_csg_transfer','{}'))
        invalidated=transfer.get('invalidated_indexed_state',[])
        provenance=transfer.get('operation')=='UNION' and 'mw_insert' in invalidated and 'mw_insert' not in obj
        reports[side]={'components':components,'geometry':info,'csg_provenance_passed':provenance,'rays':samples,'rib_anchors':len(distances),'rib_max_distance_mm':max(distances) if distances else None,'rib_support_passed':rib_support,
                       'passed':components==1 and info['finite'] and info['nonmanifold_edges']==0 and provenance and rib_support and all(row['passed'] for row in samples)}
    report={'blender':bpy.app.version_string,'source_sha256':digest,'source_preserved':digest==hashlib.sha256(source.read_bytes()).hexdigest(),
            'rays_sha256':hashlib.sha256(spec_path.read_bytes()).hexdigest(),'sides':reports}
    report['passed']=report['source_preserved'] and all(row['passed'] for row in reports.values())
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n');print('GRIP_WRAP',report['passed'],flush=True)
    if not report['passed']:raise ValueError('Grip wrap coverage, connectivity or provenance failed')

if __name__=='__main__':verify(*map(Path,sys.argv[sys.argv.index('--')+1:]))
