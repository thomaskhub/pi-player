"""
This variable is defining the actions when a particualr button is pressed.
Each seleactable element in the GUI has a uniqe ID which is assigned to it
when a Kivy selectable object is created. All the selectable Elements can be
found in isha_kivy.py

Each of the tree elemts contains of multiple child object which are
lists of dicts. These dicts have the follwing keys:

'func' --> this is a method of the selectable gui object which should be executed
'id' --> defines the id of the gui element which shall be used

The last element of the dict list must always be {'nextid':ID} which defines
the id of the next element which shall be selected. FUnctions are executed
in the list from left to right.

Example:

0:{
    "left": [{'func':'enable', 'id':1},{'nextid':1}],
}

In the above example the behaviour of the gui element with id 0 is defined.
If we selected element with ID=0 and we press the 'left' key the method "enable"
of the object with the ID=1 is executed. Then the nextid is set to one,
meaning that this object will gain keyboard control
"""

controlTree = {
    0:{
        "left": None,
        "right": [{'func':'switch','id':1}, {'func':'enable','id':1}, {'func':'disable','id':0}, {'nextid':1}],
        "up": None,
        "down":[{'func':'enable','id':100}, {'func':'disable','id':0}, {'nextid':100}],
        "type":"tab",
      },
    1:{
        "left":  [{'func':'switch','id':0}, {'func':'enable','id':0}, {'func':'disable','id':1}, {'nextid':0}],
        "right": [{'func':'switch','id':2}, {'func':'enable','id':2}, {'func':'disable','id':1}, {'nextid':2}],
        "up": [{
                'func':'disable',
                'id':20000
                },
                {'nextid':20000}
        ],
        "down": [{'func':'enable','id':20000}, {'nextid':20000}],
        "enter":[{'func':'enter', 'id':20000},{'nextid':20000}],
        "type":"tab",
      },
    2:{
        "left":  [{'func':'switch','id':1}, {'func':'enable','id':1}, {'func':'disable','id':2}, {'nextid':1}],
        "right": [{'func':'switch','id':3}, {'func':'enable','id':3}, {'func':'disable','id':2}, {'nextid':3}],
        "up": [{
                'func':'disable',
                'id':30000
                },
                {'nextid':30000}
        ],
        "down": [{'func':'enable','id':30000}, {'nextid':30000}],
        "enter":[{'func':'enter', 'id':30000},{'nextid':30000}],
        "type":"tab",
      },
    3:{
        "left":  [{'func':'switch','id':2}, {'func':'enable','id':2}, {'func':'disable','id':3}, {'nextid':2}],
        "right": None,
        "up": None,
        "down":None,
        "type":"tab",
      },
    100:{
        "left":[{'func':'decrement', 'id':100}],
        "right":[{'func':'increment', 'id':100}],
        "up":[ {'func':'disable','id':100}, {'func':'enable','id':0},{'nextid':0}],
        "down":[{'func':'enable','id':101}, {'func':'disable','id':100}, {'nextid':101}],
        "type":"slider",
      },
    101:{
        "left":[{'func':'decrement', 'id':101}],
        "right":[{'func':'increment', 'id':101}],
        "up": [{'func':'enable','id':100}, {'func':'disable','id':101}, {'nextid':100}],
        "down":None,
        "type":"slider",
      },

    103:{
        "left":None,
        "right":None,
        "up":[{'func':'enable','id':100}, {'func':'disable','id':103}, {'nextid':100}],
        "down":None,
        "type":"label",
        },
    20000:{
        "left":  [{'func':'switch','id':0}, {'func':'enable','id':0}, {'func':'disable','id':1}, {'nextid':0}],
        "right": [{'func':'switch','id':2}, {'func':'enable','id':2}, {'func':'disable','id':1}, {'nextid':2}],
        "up":[{
            'func':'disable',
            'id':20000,
            'true':{
                'func':'enable',
                'id':1,
                'nextid':1
                }
            }],
        "down":[{'func':'enable','id':20000}],
        "enter":[{'func':'enter', 'id':20000},{'nextid':20000}],
        "type":"123",
        },
    30000:{
        "left":  [{'func':'switch','id':1}, {'func':'enable','id':1}, {'func':'disable','id':2}, {'nextid':1}],
        "right": [{'func':'switch','id':3}, {'func':'enable','id':3}, {'func':'disable','id':2}, {'nextid':3}],
        "up":[{
            'func':'disable',
            'id':30000,
            'true':{
                'func':'enable',
                'id':2,
                'nextid':2
                }
            }],
        "down":[{'func':'enable','id':30000}],
        "enter":[{'func':'enter', 'id':30000},{'nextid':30000}],
        "type":"123",
        },
}
