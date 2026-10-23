"""Authored grip seam supports, tested on the native drill before graph addition."""
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_WORKSPACE = next(p for p in _LayoutPath(__file__).resolve().parents if (p / "pyproject.toml").is_file())
_layout_sys.path.insert(0, str(_WORKSPACE / 'examples'))
from _bootstrap import configure as _configure_examples
_configure_examples(_WORKSPACE)

import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = _WORKSPACE
sys.path.insert(0, str(ROOT / "src"))
from mesh_workbench import attachments, nested, seams, assembly, pathmodel, mechanical, shells


def path(length, front):
    a,b = np.array(([-17,49],[-2,123]) if front else ([-47,49],[-30,118]),float)
    for p in (a,b):
        t = np.clip((140-p[1])/40,0,1)
        p[1] -= length*t*t*(3-2*t)
    tangent = (b-a)/np.linalg.norm(b-a)
    inward = np.array([-tangent[1],tangent[0]])*(1 if front else -1)
    return [[p[0],-1.6,p[1]] for t in np.linspace(.14,.88,18)
            for p in [a+(b-a)*t+inward*2.65]]


def definitions():
    result = {}
    for front in (False,True):
        p0,p1 = np.array(path(28,front)),np.array(path(29,front))
        points = []
        for row,delta in zip(p0,p1-p0):
            points.append([float(v) if abs(d)<1e-12 else
                           {"param":"grip_length","scale":float(d),"offset":float(v-28*d)}
                           for v,d in zip(row,delta)])
        result["housing_seam_"+("front" if front else "rear")+"_grip"] = {
            "kind":"seam_lip", "visible":True,
            "deps":[{"id":"housing_left","use":"geometry"},
                    {"id":"housing_right","use":"geometry"}],
            "args":{"points":points,"normal":[0,1,0],
                    "query":{"materials":[1],"components":1},
                    "overlap":4.8,"thickness":1.4,"clearance":.2,
                    "attachment_distance":.8,"closed":False},
            "material":{"name":"Internal seam support","color":[.08,.08,.08],"roughness":.5}}
    # Authored internal upper-wall supports, following the measured inner
    # contour. These are model geometry controls, not evaluation ray changes.
    upper = {'front': [[42.54613, 173.0],
               [42.34845, 173.25],
               [42.15079, 173.5],
               [41.94093, 173.75],
               [41.7141, 174.0],
               [41.48727, 174.25],
               [41.24064, 174.5],
               [40.98235, 174.75],
               [40.72403, 175.0],
               [40.45177, 175.25],
               [40.17679, 175.5],
               [39.90177, 175.75],
               [39.62678, 176.0],
               [39.33728, 176.25],
               [39.0476, 176.5],
               [38.74786, 176.75],
               [38.42516, 177.0],
               [38.10249, 177.25],
               [37.74474, 177.5],
               [37.38306, 177.75],
               [36.98849, 178.0],
               [36.58008, 178.25],
               [36.13097, 178.5],
               [35.66547, 178.75],
               [35.13409, 179.0],
               [34.56664, 179.25],
               [33.93839, 179.5],
               [33.19511, 179.75],
               [32.3177, 180.0],
               [31.20719, 180.25],
               [29.35437, 180.5],
               [26.17318, 180.75],
               [22.92321, 181.0],
               [19.67326, 181.25],
               [16.6414, 181.5],
               [14.1012, 181.75],
               [11.91554, 182.0],
               [9.94337, 182.25],
               [8.1489, 182.5],
               [6.49327, 182.75],
               [4.94241, 183.0],
               [3.47966, 183.25],
               [2.09146, 183.5],
               [0.76654, 183.75],
               [-0.52512, 184.0],
               [-1.81674, 184.25],
               [-3.10843, 184.5],
               [-4.4001, 184.75],
               [-5.69177, 185.0],
               [-6.98344, 185.25],
               [-8.27513, 185.5],
               [-9.56682, 185.75],
               [-10.85849, 186.0],
               [-12.1501, 186.25],
               [-13.48189, 186.5],
               [-14.91255, 186.75],
               [-16.49496, 187.0]],
     'rear': [[-61.59285, 173.0],
              [-61.52299, 173.25],
              [-61.44537, 173.5],
              [-61.36508, 173.75],
              [-61.28479, 174.0],
              [-61.20343, 174.25],
              [-61.11259, 174.5],
              [-61.02175, 174.75],
              [-60.93091, 175.0],
              [-60.83794, 175.25],
              [-60.74178, 175.5],
              [-60.64562, 175.75],
              [-60.54947, 176.0],
              [-60.45332, 176.25],
              [-60.35383, 176.5],
              [-60.24896, 176.75],
              [-60.1441, 177.0],
              [-60.03922, 177.25],
              [-59.91718, 177.5],
              [-59.79355, 177.75],
              [-59.66991, 178.0],
              [-59.53075, 178.25],
              [-59.38632, 178.5],
              [-59.24192, 178.75],
              [-59.07975, 179.0],
              [-58.91218, 179.25],
              [-58.74461, 179.5],
              [-58.55199, 179.75],
              [-58.35847, 180.0],
              [-58.15515, 180.25],
              [-57.93232, 180.5],
              [-57.7095, 180.75],
              [-57.45773, 181.0],
              [-57.20157, 181.25],
              [-56.92392, 181.5],
              [-56.62949, 181.75],
              [-56.31695, 182.0],
              [-55.97815, 182.25],
              [-55.61826, 182.5],
              [-55.22741, 182.75],
              [-54.8025, 183.0],
              [-54.34971, 183.25],
              [-53.8338, 183.5],
              [-53.29591, 183.75],
              [-52.72449, 184.0],
              [-52.15305, 184.25],
              [-51.58164, 184.5],
              [-51.01022, 184.75],
              [-50.4388, 185.0],
              [-49.84143, 185.25],
              [-49.24152, 185.5],
              [-48.581, 185.75],
              [-47.89941, 186.0],
              [-47.16386, 186.25],
              [-46.36285, 186.5],
              [-45.49953, 186.75],
              [-44.54504, 187.0]]}
    for side, profile in upper.items():
        profile = np.array(profile, float)
        tangent = np.gradient(profile, axis=0)
        tangent /= np.linalg.norm(tangent, axis=1)[:,None]
        inward = np.column_stack((-tangent[:,1], tangent[:,0]))
        if side == "rear":
            inward *= -1
        centers = profile + .6*inward
        node = json.loads(json.dumps(result["housing_seam_front_grip"]))
        node["args"]["points"] = [[float(x),-1.6,float(z)] for x,z in centers]
        result["housing_seam_"+side+"_upper"] = node
    # Continuous roof/rear, neck and lower U supports from native inner contours.
    controls = json.loads(((_WORKSPACE / 'examples/drill/realism/recipes/part-01/drill-realism-seam-controls.json')).read_text())
    result.update(controls["nodes"])
    return result


def probe(source, output):
    output.mkdir(parents=True,exist_ok=False)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),load_ui=False,use_scripts=False)
    state = nested.load()
    left,right = [bpy.data.objects[state["outputs"]["housing_"+side]["object"]]
                  for side in ("left","right")]
    revisions = [attachments.revision(obj) for obj in (left,right)]
    reports = {}
    nodes = definitions()
    for name,node in nodes.items():
        args = nested._resolve(node["args"],state["parameters"])
        try:
            rib = seams.seam_lip(left,right,name,**args)
            reports[name] = {"passed":True,"geometry":json.loads(rib["mw_seam_lip"])}
        except ValueError as exc:
            reports[name] = {"passed":False,"reason":str(exc)}
            diagnostic = pathmodel.create(name+" diagnostic",args["points"],
                [[args["overlap"]/2,args["thickness"]/2]]*len(args["points"]),
                segments=12,reference=args["normal"],closed=False)
            try:
                tree = assembly._tree(right)
                nearest = [tree.find_nearest(Vector(p))
                           for p in seams._probes(diagnostic)]
                reports[name]["diagnostic"] = {
                    "minimum_unsigned_distance":min(row[3] for row in nearest),
                    "opposing_intersections":shells.intersections(diagnostic,right)["triangle_pair_count"],
                    "source_intersections":shells.intersections(diagnostic,left)["triangle_pair_count"]}
            finally:
                mechanical.remove(diagnostic)
        print("SEAM_PROBE",name,json.dumps(reports[name]),flush=True)
    report = {"blender":bpy.app.version_string,"parts":reports,
              "source_preserved":digest == hashlib.sha256(source.read_bytes()).hexdigest(),
              "shell_geometry_preserved":revisions == [attachments.revision(obj) for obj in (left,right)],
              "passed":all(r["passed"] for r in reports.values())}
    (output/"probe.json").write_text(json.dumps(report,indent=2)+"\n")
    (output/"nodes.json").write_text(json.dumps(nodes,indent=2)+"\n")
    if not report["passed"] or not report["source_preserved"] or not report["shell_geometry_preserved"]:
        raise ValueError("Native seam support probe rejected")


if __name__ == "__main__":
    probe(*map(Path,sys.argv[sys.argv.index("--")+1:]))
