"""Join source-bound side inserts to tapered rear inserts per shell half."""
import copy


def add_grip_wrap(nodes):
    for side,sign in (('left',-1),('right',1)):
        key='grip_'+side
        original=copy.deepcopy(nodes[key]);original['visible']=False
        nodes['grip_oval_'+side]=original
        nodes['grip_rear_'+side]={
            'kind':'insert','visible':False,
            'deps':[{'id':'housing_'+side,'use':'geometry'}],
            'args':{
                'query':{'box':[[-55,min(sign*20,0),{'param':'grip_length','offset':78,'scale':-1}],
                                [-20,max(sign*20,0),105]],
                         'normal':[-1,0,0],'normal_min':.5,'materials':[0],'components':1},
                'center':[0,sign*7.0,{'param':'grip_length','offset':91.5,'scale':-.5}],
                'radii':[6.25,{'param':'grip_length','offset':8.5,'scale':.5}],
                'projection_axis':0,'side':-1,'offset':.6,'thickness':.8,
                'rim_offset':.15,'rim_fraction':.3,
                'rings':12,'segments':64,'max_distance':150},
            'material':copy.deepcopy(original['material'])}
        nodes[key]={
            'kind':'union','visible':True,
            'deps':[{'id':'grip_oval_'+side,'use':'geometry'},
                    {'id':'grip_rear_'+side,'use':'geometry'}],
            'args':{},'material':copy.deepcopy(original['material']),
            'frame':copy.deepcopy(original['frame'])}
        # Keep the original side chart as the construction surface for its
        # existing ribs. The final union contains that patch; the grip verifier
        # separately measures every rib anchor against the visible union.
        for dependency in nodes['texture_'+side]['deps']:
            if dependency['id']==key:
                dependency['id']='grip_oval_'+side
