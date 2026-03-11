# todo alles als ein array darstellen
import networkx as nx

INPUT=dict(
    werte=[10,40,6000,3249824,], # encodes return values of prev calcs
    influencer=.5, # ein dynamisch festgeelgter influenzer wert welcher an bestimmten stellen eingebracht wird
    meta=dict(
        time=00.00,  # dauer der kalkulation
        step=4  # anzahl schritte
    ),
    utils=dict(
        regeln
    ),
)

CALC_ARRAY=[
    # als graphen darstellen -> jeder dieser werte über edges (operatoren) verbunden
    # kalkulationen über diesen Wert können einfluss auf operatoren und ihre konstelation vorübergehend o.
    # dauerhaft ändern
    [9.0,4.6,1],
    [3.0,4.6,2],
    [5.0,4.6,3]
]


def make_graph():
    g = nx.Graph()
    # Make Input array graph


    # Make Calc array graph
    for c in CALC_ARRAY:
        g.add_node(
            c
        )

    for k, v in g.nodes(data=True):
        for nk, nv in g.nodes(data=True):
            g.add_edge(
                k,
                nk,
                attrs=dict(
                    operator=","
                )
            )





# am ende merget man input graph und calc graph und erhält eine neue state -> alles geht ineinander über