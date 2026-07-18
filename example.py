"""
Example Dash MCP app — no dash_langsmith imports needed.

Install dash-langsmith and set LANGSMITH_API_KEY. Every MCP tools/call
is automatically traced to LangSmith via the dash_hooks entry point.
"""

import plotly.graph_objects as go
from dash import Dash, dash_table, dcc, html, Input, Output, callback
from dash.mcp import mcp_enabled

# ---------------------------------------------------------------------------
# Fake data
# ---------------------------------------------------------------------------

REGIONS = ["north", "south", "east", "west"]

SALES = {
    "north": [88, 95, 102, 110, 120, 133],
    "south": [72, 78, 85, 90, 95, 101],
    "east":  [110, 118, 125, 130, 140, 152],
    "west":  [95, 99, 105, 107, 110, 118],
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]

INVENTORY = [
    {"category": "guitars",   "units": 42, "reorder_at": 10, "status": "OK"},
    {"category": "drums",     "units":  7, "reorder_at": 10, "status": "LOW"},
    {"category": "keyboards", "units": 31, "reorder_at": 15, "status": "OK"},
    {"category": "bass",      "units": 19, "reorder_at": 10, "status": "OK"},
    {"category": "amps",      "units":  4, "reorder_at":  5, "status": "LOW"},
    {"category": "cables",    "units": 88, "reorder_at": 20, "status": "OK"},
]

CUSTOMERS = [
    {"id": 1, "name": "Alice Martin",  "region": "north", "lifetime_value": 4200},
    {"id": 2, "name": "Bob Chen",      "region": "east",  "lifetime_value": 7800},
    {"id": 3, "name": "Carol Davis",   "region": "south", "lifetime_value": 3100},
    {"id": 4, "name": "Dan Kim",       "region": "west",  "lifetime_value": 5500},
    {"id": 5, "name": "Eva Rossi",     "region": "east",  "lifetime_value": 9200},
    {"id": 6, "name": "Frank Osei",    "region": "north", "lifetime_value": 6600},
    {"id": 7, "name": "Grace Lee",     "region": "south", "lifetime_value": 2900},
    {"id": 8, "name": "Hiro Tanaka",   "region": "west",  "lifetime_value": 8100},
]

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = Dash(__name__, enable_mcp=True, suppress_callback_exceptions=True)

app.layout = html.Div(
    style={"fontFamily": "sans-serif", "maxWidth": 960, "margin": "0 auto", "padding": "24px"},
    children=[
        html.H1("Music Store Dashboard", style={"marginBottom": 4}),
        html.P("Powered by Dash MCP + LangSmith tracing", style={"color": "#888", "marginTop": 0}),

        dcc.Tabs(id="tabs", value="sales", children=[
            dcc.Tab(label="Sales", value="sales"),
            dcc.Tab(label="Inventory", value="inventory"),
            dcc.Tab(label="Customers", value="customers"),
        ]),

        html.Div(id="tab-content", style={"paddingTop": 24}),
    ],
)

# ---------------------------------------------------------------------------
# Tab router
# ---------------------------------------------------------------------------

@callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab: str):
    if tab == "sales":
        return sales_layout()
    if tab == "inventory":
        return inventory_layout()
    if tab == "customers":
        return customers_layout()
    return html.Div("Unknown tab")


# ---------------------------------------------------------------------------
# Sales tab
# ---------------------------------------------------------------------------

def sales_layout():
    return html.Div([
        html.Div(
            style={"display": "flex", "gap": 16, "marginBottom": 16},
            children=[
                html.Div(style={"flex": 1}, children=[
                    html.Label("Region"),
                    dcc.Dropdown(
                        id="sales-region",
                        options=[{"label": r.title(), "value": r} for r in REGIONS],
                        value="north",
                        clearable=False,
                    ),
                ]),
                html.Div(style={"flex": 1}, children=[
                    html.Label("Compare with"),
                    dcc.Dropdown(
                        id="sales-compare",
                        options=[{"label": r.title(), "value": r} for r in REGIONS],
                        value="east",
                        clearable=False,
                    ),
                ]),
                html.Div(style={"flex": 1}, children=[
                    html.Label("Chart type"),
                    dcc.RadioItems(
                        id="sales-chart-type",
                        options=[{"label": "Line", "value": "line"}, {"label": "Bar", "value": "bar"}],
                        value="line",
                        inline=True,
                    ),
                ]),
            ],
        ),
        dcc.Graph(id="sales-chart"),
        html.Div(id="sales-summary", style={"marginTop": 12, "color": "#555"}),
    ])


@callback(
    Output("sales-chart", "figure"),
    Output("sales-summary", "children"),
    Input("sales-region", "value"),
    Input("sales-compare", "value"),
    Input("sales-chart-type", "value"),
    mcp_enabled=True,
    mcp_expose_docstring=True,
)
def update_sales_chart(region: str, compare: str, chart_type: str):
    """
    Render a sales trend chart for two regions over the last 6 months.
    Returns a Plotly figure and a text summary of the most recent month.
    """
    fig = go.Figure()
    for r, color in [(region, "#636efa"), (compare, "#ef553b")]:
        y = SALES[r]
        if chart_type == "line":
            fig.add_trace(go.Scatter(x=MONTHS, y=y, name=r.title(), line={"color": color}))
        else:
            fig.add_trace(go.Bar(x=MONTHS, y=y, name=r.title(), marker_color=color))

    fig.update_layout(
        title=f"{region.title()} vs {compare.title()} — last 6 months",
        yaxis_title="Sales ($k)",
        legend={"orientation": "h"},
        margin={"t": 48, "b": 32},
    )

    a, b = SALES[region][-1], SALES[compare][-1]
    delta = a - b
    sign = "+" if delta >= 0 else ""
    summary = f"Latest month: {region.title()} ${a}k vs {compare.title()} ${b}k  ({sign}{delta}k)"
    return fig, summary


# ---------------------------------------------------------------------------
# Inventory tab
# ---------------------------------------------------------------------------

def inventory_layout():
    return html.Div([
        html.Div(
            style={"display": "flex", "gap": 16, "marginBottom": 16, "alignItems": "flex-end"},
            children=[
                html.Div([
                    html.Label("Filter by status"),
                    dcc.Checklist(
                        id="inventory-status-filter",
                        options=["OK", "LOW"],
                        value=["OK", "LOW"],
                        inline=True,
                    ),
                ]),
                html.Div([
                    html.Label("Min units"),
                    dcc.Slider(
                        id="inventory-min-units",
                        min=0, max=90, step=5, value=0,
                        marks={0: "0", 30: "30", 60: "60", 90: "90"},
                    ),
                ], style={"flex": 1}),
            ],
        ),
        dash_table.DataTable(
            id="inventory-table",
            columns=[
                {"name": "Category", "id": "category"},
                {"name": "Units", "id": "units"},
                {"name": "Reorder At", "id": "reorder_at"},
                {"name": "Status", "id": "status"},
            ],
            style_data_conditional=[
                {
                    "if": {"filter_query": '{status} = "LOW"'},
                    "backgroundColor": "#fff3cd",
                    "color": "#856404",
                }
            ],
            style_header={"fontWeight": "bold"},
        ),
        html.Div(id="inventory-summary", style={"marginTop": 12, "color": "#555"}),
    ])


@callback(
    Output("inventory-table", "data"),
    Output("inventory-summary", "children"),
    Input("inventory-status-filter", "value"),
    Input("inventory-min-units", "value"),
    mcp_enabled=True,
    mcp_expose_docstring=True,
)
def filter_inventory(statuses: list, min_units: int):
    """
    Filter inventory by status (OK / LOW) and minimum unit count.
    Returns the filtered rows and a summary of how many items are low stock.
    """
    rows = [
        r for r in INVENTORY
        if r["status"] in statuses and r["units"] >= min_units
    ]
    low = sum(1 for r in rows if r["status"] == "LOW")
    summary = f"Showing {len(rows)} categories — {low} low stock"
    return rows, summary


# ---------------------------------------------------------------------------
# Customers tab
# ---------------------------------------------------------------------------

def customers_layout():
    return html.Div([
        html.Div(
            style={"display": "flex", "gap": 16, "marginBottom": 16},
            children=[
                html.Div(style={"flex": 1}, children=[
                    html.Label("Filter by region"),
                    dcc.Dropdown(
                        id="customer-region",
                        options=[{"label": "All", "value": "all"}]
                             + [{"label": r.title(), "value": r} for r in REGIONS],
                        value="all",
                        clearable=False,
                    ),
                ]),
                html.Div(style={"flex": 1}, children=[
                    html.Label("Sort by"),
                    dcc.RadioItems(
                        id="customer-sort",
                        options=[
                            {"label": "Name", "value": "name"},
                            {"label": "Lifetime value", "value": "lifetime_value"},
                        ],
                        value="lifetime_value",
                        inline=True,
                    ),
                ]),
            ],
        ),
        dcc.Graph(id="customer-chart"),
        html.Div(id="customer-summary", style={"marginTop": 12, "color": "#555"}),
    ])


@callback(
    Output("customer-chart", "figure"),
    Output("customer-summary", "children"),
    Input("customer-region", "value"),
    Input("customer-sort", "value"),
    mcp_enabled=True,
    mcp_expose_docstring=True,
)
def update_customer_chart(region: str, sort_by: str):
    """
    Show a bar chart of customers filtered by region and sorted by name or lifetime value.
    Returns a Plotly figure and a summary of total lifetime value for the filtered set.
    """
    rows = CUSTOMERS if region == "all" else [c for c in CUSTOMERS if c["region"] == region]
    rows = sorted(rows, key=lambda c: c[sort_by], reverse=(sort_by == "lifetime_value"))

    fig = go.Figure(go.Bar(
        x=[c["name"] for c in rows],
        y=[c["lifetime_value"] for c in rows],
        marker_color="#00cc96",
    ))
    fig.update_layout(
        title="Customer lifetime value",
        yaxis_title="$ value",
        margin={"t": 48, "b": 32},
    )

    total = sum(c["lifetime_value"] for c in rows)
    summary = f"{len(rows)} customers — total lifetime value ${total:,}"
    return fig, summary


# ---------------------------------------------------------------------------
# @mcp_enabled standalone tools (no UI counterpart)
# ---------------------------------------------------------------------------

@mcp_enabled(expose_docstring=True)
def get_inventory(category: str) -> dict:
    """Return current inventory levels for a single product category."""
    row = next((r for r in INVENTORY if r["category"] == category), None)
    if row is None:
        return {"error": f"Unknown category: {category}"}
    return row


@mcp_enabled(expose_docstring=True)
def get_top_customers(limit: int = 3) -> list:
    """Return the top N customers by lifetime value."""
    return sorted(CUSTOMERS, key=lambda c: c["lifetime_value"], reverse=True)[:limit]


@mcp_enabled(expose_docstring=True)
def compare_regions(region_a: str, region_b: str) -> dict:
    """
    Compare total 6-month sales between two regions.
    Returns totals, the difference, and which region is ahead.
    """
    if region_a not in SALES or region_b not in SALES:
        return {"error": "Unknown region. Valid: north, south, east, west"}
    a, b = sum(SALES[region_a]), sum(SALES[region_b])
    return {
        region_a: a,
        region_b: b,
        "difference": abs(a - b),
        "leader": region_a if a >= b else region_b,
    }


@mcp_enabled(expose_docstring=True)
def search_products(query: str) -> list:
    """Search inventory categories by partial name match."""
    q = query.lower()
    return [r for r in INVENTORY if q in r["category"]]


if __name__ == "__main__":
    app.run(debug=True)
