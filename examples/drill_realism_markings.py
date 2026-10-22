"""Original procedural torque numerals on an explicit exterior label band."""

def add_torque_markings(nodes):
    nodes['torque_ring']['args']['profile'] = [
        [0,21.6,14.5,0],[.6,22,14,0],[5.8,22,14,0],[6.2,22,14,1],
        [12,22,14,1],[13,22,14,0],[15,19,14.5,0]]
    for text,z in [('1',149),('3',159),('5',169)]:
        nodes['torque_mark_'+text] = {
            'kind':'surface_marking','visible':True,
            'deps':[{'id':'torque_ring','use':'geometry'}],
            'args':{'text':text,'origin':[48.2,-30,z],
                    'horizontal':[1,0,0],'vertical':[0,0,1],
                    'query':{'box':[[48,-23,145],[51,-15,175]],
                             'normal':[0,-1,0],'normal_min':.5,
                             'materials':[0],'components':1},
                    'size':2.5,'width':.12,'height':.025,
                    'projection_axis':1,'side':-1,'max_distance':30},
            'material':{'name':'Original light marking','color':[.8,.82,.78],
                        'roughness':.38}}

def add_control_markings(nodes):
    for index,side in enumerate((-1,1)):
        nodes['direction_mark_'+str(index)] = {
            'kind':'surface_marking','visible':True,
            'deps':[{'id':'direction_switch','use':'geometry'}],
            'args':{'text':'>' if side<0 else '<','origin':[2.4,side*30,135.2],
                    'horizontal':[1,0,0],'vertical':[0,0,1],
                    'query':{'normal':[0,side,0],'normal_min':.99,'materials':[0],'components':1},
                    'size':2.4,'width':.12,'height':.025,
                    'projection_axis':1,'side':side,'max_distance':40},
            'material':{'name':'Original light marking','color':[.8,.82,.78],'roughness':.38}}
    # Battery-cover prefix keeps these bound marks in the existing rigid
    # battery removal group. Z follows the same grip-length dependency.
    for index,side in enumerate((-1,1)):
        nodes['battery_cover_indicator_'+str(index)] = {
            'kind':'surface_marking','visible':True,
            'deps':[{'id':'battery_cover_'+str(index),'use':'geometry'}],
            'args':{'text':'---','origin':[-45,side*24,{'param':'grip_length','offset':35.3,'scale':-1}],
                    'horizontal':[1,0,0],'vertical':[0,0,1],
                    'query':{'normal':[0,side,0],'normal_min':.99,'materials':[0],'components':1},
                    'size':2.4,'width':.16,'height':.025,
                    'projection_axis':1,'side':side,'max_distance':40},
            'material':{'name':'Original indicator marking','color':[.32,.68,.25],'roughness':.38}}

def add_torque_pointer(nodes):
    nodes['torque_pointer'] = {
        'kind':'surface_marking','visible':True,
        'deps':[{'id':'housing_left','use':'geometry'}],
        'args':{'text':'>','origin':[36,-30,158.8],
                'horizontal':[1,0,0],'vertical':[0,0,1],
                'query':{'box':[[33,-30,155],[43,-12,166]],
                         'normal':[0,-1,0],'normal_min':.5,'materials':[0],'components':1},
                'size':2.4,'width':.14,'height':.025,
                'projection_axis':1,'side':-1,'max_distance':40},
        'material':{'name':'Original pointer marking','color':[.025,.03,.035],'roughness':.38}}
