from neo4j import GraphDatabase

import networkx as nx

from bokeh.io import curdoc
from bokeh.plotting import figure
from bokeh.models import (
    GraphRenderer,
    StaticLayoutProvider,
    ColumnDataSource,
    Circle,
    MultiLine,
    HoverTool,
    CustomJS,
    TextInput,
    Button,
    Select
)

from bokeh.layouts import column, row


# ============================================================
# 1. NEO4J CONNECTION
# ============================================================

URI = "neo4j://127.0.0.1:7687"
USERNAME = "neo4j"

# ------------------------------------------------------------
# IMPORTANT:
# Replace ONLY YOUR_NEO4J_PASSWORD with your real password.
# DO NOT share your password with anyone.
# ------------------------------------------------------------

PASSWORD = "ABCama24"


driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)


# Check Neo4j connection
driver.verify_connectivity()


# ============================================================
# 2. GET NODES FROM NEO4J
# ============================================================

def get_nodes(tx):

    result = tx.run("""
        MATCH (n)
        RETURN elementId(n) AS id,
               labels(n) AS labels,
               n
    """)

    return [
        {
            "id": record["id"],
            "labels": record["labels"],
            "properties": dict(record["n"])
        }
        for record in result
    ]


with driver.session(database="neo4j") as session:

    nodes = session.execute_read(get_nodes)


# ============================================================
# 3. GET RELATIONSHIPS FROM NEO4J
# ============================================================

def get_relationships(tx):

    result = tx.run("""
        MATCH (n)-[r]->(m)
        RETURN elementId(n) AS source,
               type(r) AS relationship_type,
               elementId(m) AS target
    """)

    return [
        {
            "source": record["source"],
            "relationship_type": record["relationship_type"],
            "target": record["target"]
        }
        for record in result
    ]


with driver.session(database="neo4j") as session:

    relationships = session.execute_read(get_relationships)


# ============================================================
# 4. CREATE NETWORKX GRAPH
# ============================================================

G = nx.DiGraph()


# Add nodes
for node in nodes:

    G.add_node(
        node["id"],
        labels=node["labels"],
        properties=node["properties"]
    )


# Add relationships
for rel in relationships:

    G.add_edge(
        rel["source"],
        rel["target"],
        relationship_type=rel["relationship_type"]
    )


# ============================================================
# 5. PREPARE NODE INFORMATION
# ============================================================

for node_id, data in G.nodes(data=True):

    if "Person" in data["labels"]:

        G.nodes[node_id]["node_type"] = "Person"

        G.nodes[node_id]["display_name"] = (
            data["properties"]["name"]
        )

        G.nodes[node_id]["year"] = ""

        G.nodes[node_id]["genre"] = ""

    elif "Movie" in data["labels"]:

        G.nodes[node_id]["node_type"] = "Movie"

        G.nodes[node_id]["display_name"] = (
            data["properties"]["title"]
        )

        G.nodes[node_id]["year"] = (
            data["properties"]["year"]
        )

        G.nodes[node_id]["genre"] = (
            data["properties"]["genre"]
        )


# ============================================================
# 6. NODE LIST AND INDEX
# ============================================================

node_ids = list(G.nodes())


node_index = {
    node_id: index
    for index, node_id in enumerate(node_ids)
}


# ============================================================
# 7. CONNECTED NODE INFORMATION
# ============================================================

connected_nodes = {}


for node_id in G.nodes():

    neighbors = set()

    # Outgoing connections
    for target in G.successors(node_id):

        neighbors.add(target)

    # Incoming connections
    for source in G.predecessors(node_id):

        neighbors.add(source)

    connected_nodes[node_id] = neighbors


# ============================================================
# 8. CREATE NODE DATA SOURCE
# ============================================================

node_data = {

    "index": [],

    "node_id": [],

    "display_name": [],

    "node_type": [],

    "year": [],

    "genre": [],

    "alpha": []

}


for index, node_id in enumerate(node_ids):

    data = G.nodes[node_id]

    node_data["index"].append(index)

    node_data["node_id"].append(node_id)

    node_data["display_name"].append(
        data["display_name"]
    )

    node_data["node_type"].append(
        data["node_type"]
    )

    node_data["year"].append(
        data["year"]
    )

    node_data["genre"].append(
        data["genre"]
    )

    node_data["alpha"].append(1.0)


node_source = ColumnDataSource(node_data)


# ============================================================
# 9. CREATE GRAPH RENDERER
# ============================================================

graph = GraphRenderer()


graph.node_renderer.data_source = node_source


# ------------------------------------------------------------
# NODE APPEARANCE
# ------------------------------------------------------------

graph.node_renderer.glyph = Circle(
    radius=0.10,
    fill_alpha="alpha"
)


graph.node_renderer.selection_glyph = Circle(
    radius=0.14,
    fill_alpha=1.0
)


graph.node_renderer.hover_glyph = Circle(
    radius=0.13,
    fill_alpha=1.0
)


# ============================================================
# 10. CREATE EDGE DATA
# ============================================================

edge_start = []

edge_end = []

edge_types = []

edge_source_names = []

edge_target_names = []


for source, target, data in G.edges(data=True):

    edge_start.append(
        node_index[source]
    )

    edge_end.append(
        node_index[target]
    )

    edge_types.append(
        data["relationship_type"]
    )

    edge_source_names.append(
        G.nodes[source]["display_name"]
    )

    edge_target_names.append(
        G.nodes[target]["display_name"]
    )


# ------------------------------------------------------------
# IMPORTANT:
# Relationship lines use start/end.
# The extra columns are used for edge tooltips.
# ------------------------------------------------------------

graph.edge_renderer.data_source.data = {

    "start": edge_start,

    "end": edge_end,

    "relationship_type": edge_types,

    "source_name": edge_source_names,

    "target_name": edge_target_names,

    "alpha": [0.8] * len(edge_types)

}


# ============================================================
# 11. EDGE APPEARANCE
# ============================================================

graph.edge_renderer.glyph = MultiLine(
    line_alpha="alpha",
    line_width=2
)


# ============================================================
# 12. CREATE NETWORK LAYOUT
# ============================================================

positions = nx.spring_layout(
    G,
    seed=42,
    scale=2
)


graph_layout = {}


for node_id, position in positions.items():

    graph_layout[
        node_index[node_id]
    ] = position


graph.layout_provider = StaticLayoutProvider(
    graph_layout=graph_layout
)


# ============================================================
# 13. CREATE BOKEH PLOT
# ============================================================

plot = figure(

    width=1100,

    height=700,

    title="Interactive Movie Network",

    x_axis_type=None,

    y_axis_type=None,

    tools="""
        pan,
        wheel_zoom,
        box_zoom,
        tap,
        reset,
        save
    """
)


# Add graph to plot
plot.renderers.append(graph)


# ============================================================
# 14. NODE HOVER TOOLTIP
# ============================================================

node_hover = HoverTool(

    renderers=[
        graph.node_renderer
    ],

    tooltips=[

        ("Name / Title", "@display_name"),

        ("Type", "@node_type"),

        ("Year", "@year"),

        ("Genre", "@genre")

    ]
)


plot.add_tools(node_hover)


# ============================================================
# 15. EDGE HOVER TOOLTIP
# ============================================================

edge_hover = HoverTool(

    renderers=[
        graph.edge_renderer
    ],

    tooltips=[

        ("Source", "@source_name"),

        ("Relationship", "@relationship_type"),

        ("Target", "@target_name")

    ]
)


plot.add_tools(edge_hover)


# ============================================================
# 16. SEARCH BOX
# ============================================================

search_box = TextInput(

    title="Search Node:",

    placeholder="Type a person or movie name..."

)


search_button = Button(

    label="Search",

    button_type="primary"

)


# ============================================================
# 17. SEARCH FUNCTION
# ============================================================

search_callback = CustomJS(

    args=dict(

        node_source=node_source,

        search_box=search_box

    ),

    code="""

    const search_text =
        search_box.value.toLowerCase().trim();


    // If search box is empty,
    // show all nodes.

    if (search_text === "") {

        for (
            let i = 0;
            i < node_source.data.alpha.length;
            i++
        ) {

            node_source.data.alpha[i] = 1.0;

        }

        node_source.change.emit();

        return;
    }


    // Search node names.

    for (
        let i = 0;
        i < node_source.data.alpha.length;
        i++
    ) {

        const name =
            node_source.data.display_name[i]
            .toLowerCase();


        if (name.includes(search_text)) {

            node_source.data.alpha[i] = 1.0;

        }
        else {

            node_source.data.alpha[i] = 0.15;

        }

    }


    node_source.change.emit();

    """

)


search_button.js_on_click(
    search_callback
)


# ============================================================
# 18. RELATIONSHIP FILTER
# ============================================================

relationship_filter = Select(

    title="Relationship Type:",

    value="ALL",

    options=[

        "ALL",

        "ACTED_IN",

        "DIRECTED"

    ]

)


# ============================================================
# 19. RELATIONSHIP FILTER FUNCTION
# ============================================================

relationship_callback = CustomJS(

    args=dict(

        edge_source=graph.edge_renderer.data_source,

        relationship_filter=relationship_filter

    ),

    code="""

    const selected_type =
        relationship_filter.value;


    const relationship_types =
        edge_source.data.relationship_type;


    const alpha =
        edge_source.data.alpha;


    for (
        let i = 0;
        i < relationship_types.length;
        i++
    ) {


        if (
            selected_type === "ALL" ||
            relationship_types[i] === selected_type
        ) {

            alpha[i] = 0.8;

        }
        else {

            alpha[i] = 0.0;

        }

    }


    edge_source.change.emit();

    """

)


relationship_filter.js_on_change(
    "value",
    relationship_callback
)


# ============================================================
# 20. CONNECTED NODE HIGHLIGHTING
# ============================================================

highlight_callback = CustomJS(

    args=dict(

        node_source=node_source,

        graph=graph

    ),

    code="""

    const selected =
        node_source.selected.indices;


    // If nothing is selected,
    // show all nodes.

    if (selected.length === 0) {


        for (
            let i = 0;
            i < node_source.data.alpha.length;
            i++
        ) {

            node_source.data.alpha[i] = 1.0;

        }


        node_source.change.emit();

        return;

    }


    const selected_index =
        selected[0];


    const connected =
        new Set();


    const starts =
        graph.edge_renderer.data_source.data.start;


    const ends =
        graph.edge_renderer.data_source.data.end;


    // Find connected nodes.

    for (
        let i = 0;
        i < starts.length;
        i++
    ) {


        if (
            starts[i] === selected_index
        ) {

            connected.add(
                ends[i]
            );

        }


        if (
            ends[i] === selected_index
        ) {

            connected.add(
                starts[i]
            );

        }

    }


    // Change transparency.

    for (
        let i = 0;
        i < node_source.data.alpha.length;
        i++
    ) {


        if (
            i === selected_index ||
            connected.has(i)
        ) {

            node_source.data.alpha[i] = 1.0;

        }
        else {

            node_source.data.alpha[i] = 0.15;

        }

    }


    node_source.change.emit();

    """

)


node_source.selected.js_on_change(

    "indices",

    highlight_callback

)


# ============================================================
# 21. TITLE AND INFORMATION
# ============================================================

info_text = """

**Interactive Movie Network**

Use the controls below:

• Search for a person or movie  
• Select a relationship type  
• Hover over nodes for information  
• Hover over lines for relationship information  
• Click a node to highlight connected nodes  
• Use zoom and pan to explore the network

"""


# ============================================================
# 22. FINAL LAYOUT
# ============================================================

controls = row(

    search_box,

    search_button,

    relationship_filter

)


layout = column(

    controls,

    plot

)


# ============================================================
# 23. START BOKEH SERVER
# ============================================================

curdoc().add_root(layout)

curdoc().title = "Interactive Movie Network"


print("Neo4j connection successful!")

print(
    "Number of nodes:",
    len(nodes)
)

print(
    "Number of relationships:",
    len(relationships)
)
