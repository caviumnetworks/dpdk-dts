# <COPYRIGHT_TAG>

"""
ixiaPorts Structure

IxiaGroup: {
Version : IXIA TCL server version
IP      : IXIA server IP address
Ports   : [IXIA port list]
},

IxiaGroup: {
Version : IXIA TCL server version
IP      : IXIA server IP address
Ports   : [IXIA ports list]
}
"""
# IXIA configure file
ixiaPorts = {
    'Group1': {"Version": "6.62",
               "IP": "10.239.128.121",
               "Ports": [
                   {"card": 1, "port": 1},
                   {"card": 1, "port": 2},
                   {"card": 1, "port": 3},
                   {"card": 1, "port": 4}
               ]
               }

}
