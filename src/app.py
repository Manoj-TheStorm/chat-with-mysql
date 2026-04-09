import os
import json
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

import re
import streamlit.components.v1 as components
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
import streamlit as st

DASHBOARD_TEMPLATE = """
<html><head>
    <title>Query Results</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script><style id="plotly.js-style-global"></style>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.8/css/jquery.dataTables.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.2/css/buttons.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.2/js/dataTables.buttons.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.2/js/buttons.html5.min.js"></script>
    <style>
        
* { box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0;
    padding: 15px;
    background: #f5f5f5;
}
.chart-container {
    background: white;
    padding: 15px;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 15px;
    max-width: 100%;
}
.chart-container h3 {
    margin: 0 0 10px 0;
    color: #333;
    font-size: 16px;
}
.chart-caption {
    color: #888888;
    font-size: 12px;
    margin-top: 8px;
}
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
th, td {
    padding: 8px;
    text-align: left;
    border-bottom: 1px solid #eee;
}
th { background: #f8f9fa; font-weight: 600; }
tr:hover { background: #f8f9fa; }

        .toolbar {
            background: white;
            padding: 12px 15px;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 15px;
            max-width: 100%;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 10px;
        }
        .pills {
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
        }
        .pill {
            padding: 5px 12px;
            border: 1px solid #ddd;
            border-radius: 16px;
            background: white;
            color: #666666;
            font-size: 12px;
            cursor: pointer;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            transition: all 0.15s;
        }
        .pill:hover {
            border-color: #7B61FF;
            color: #7B61FF;
        }
        .pill.active {
            background: #7B61FF;
            color: white;
            border-color: #7B61FF;
        }
        .col-select {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;
            color: #666666;
        }
        .col-select select {
            padding: 4px 6px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 140px;
        }
        #z-select-group { display: none; }
        .chart-actions {
            position: absolute; top: 10px; right: 10px;
            display: flex; gap: 4px;
        }
        .chart-container { position: relative; }
        .chart-action-btn {
            background: none; border: none; padding: 6px;
            color: #999; cursor: pointer; transition: color 0.15s;
            display: flex; align-items: center; justify-content: center;
        }
        .chart-action-btn:hover { color: #333; }
        .chart-action-btn svg { width: 18px; height: 18px; }
        .axis-toggle {
            font-size: 10px; font-weight: 600; font-family: inherit;
            min-width: 18px; height: 18px; line-height: 18px;
            text-align: center; border-radius: 3px;
        }
        .axis-toggle.on { color: #333; background: #e9ecef; }
        .chart-actions-sep {
            width: 1px; background: #ddd; margin: 2px 2px;
        }
        /* DataTables overrides */
        .dataTables_wrapper { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 13px; }
        .dataTables_filter input { border: 1px solid #ddd; border-radius: 4px; padding: 4px 8px; }
        .dataTables_length select { border: 1px solid #ddd; border-radius: 4px; padding: 2px 6px; }
        table.dataTable thead th { background: #f8f9fa; font-weight: 600; border-bottom: 2px solid #ddd; }
        table.dataTable tbody tr:hover { background: #f8f9fa !important; }
        .dataTables_info, .dataTables_paginate { margin-top: 10px; }
        
    </style>
</head>
<body>
    <div class="toolbar">
        <div class="pills">
            <button type="button" class="pill active" onclick="selectChart(this, 'table')">Table</button>
            <button type="button" class="pill " onclick="selectChart(this, 'bar')">Bar</button>
            <button type="button" class="pill " onclick="selectChart(this, 'horizontal_bar')">H-Bar</button>
            <button type="button" class="pill " onclick="selectChart(this, 'grouped_bar')">Grouped</button>
            <button type="button" class="pill " onclick="selectChart(this, 'pie')">Donut</button>
            <button type="button" class="pill " onclick="selectChart(this, 'line')">Line</button>
            <button type="button" class="pill " onclick="selectChart(this, 'scatter')">Scatter</button>
            <button type="button" class="pill " onclick="selectChart(this, 'heatmap')">Heatmap</button>
        </div>
        <div class="col-select">
            <label>X:</label>
            <select id="x-select" onchange="render(currentType())"></select>
        </div>
        <div class="col-select">
            <label>Y:</label>
            <select id="y-select" onchange="render(currentType())"></select>
        </div>
        <div class="col-select" id="z-select-group">
            <label>Z:</label>
            <select id="z-select" onchange="render(currentType())"></select>
        </div>
    </div>
    <div class="chart-container">
        <h3 id="chart-title">Query Results</h3>
        <div class="chart-actions" style="display: none;">
        <button id="toggle-x" class="chart-action-btn axis-toggle on" title="Toggle X axis label" onclick="toggleAxis('x')">X</button>
        <button id="toggle-y" class="chart-action-btn axis-toggle on" title="Toggle Y axis label" onclick="toggleAxis('y')">Y</button>
        </div>
        <div id="chart" style="display: none;"></div>
        <div id="table-container" style="display: block;"></div>
        <p class="chart-caption" id="caption"></p>
    </div>

<script>
const DATA = __DATA__;
const COLUMNS = __COLUMNS__;
const BAR_COLORS = ["#1a1a2e", "#7B61FF", "#2a9d8f", "#5a45cc", "#9580FF", "#e76f51", "#264653", "#e9c46a", "#f4a261", "#606c38"];
const PIE_COLORS = ["#7B61FF", "#5a45cc", "#9580FF", "#b8a9ff", "#2a9d8f", "#a8d5e5", "#d4a8e5", "#e5d4a8", "#e5a8b8", "#b8e5a8", "#a8b8e5", "#e5e5a8", "#d4e5a8", "#a8e5d4", "#e5a8a8", "#a8a8e5"];
const BRAND = {
    primary: '#7B61FF',
    primaryDark: '#5a45cc',
    primaryLight: '#9580FF',
    navy: '#1a1a2e',
    teal: '#2a9d8f',
};
const MARGINS = {
    standard: { t: 30, b: 40, l: 40, r: 20 },
    horizontal_bar: { t: 20, b: 40, l: 200, r: 50 },
};
const PLOTLY_CFG = { responsive: true, displayModeBar: false, scrollZoom: false };

let _currentType = 'table';
let _showXLabel = true;
let _showYLabel = true;
let _lastXAxisLabel = '';
let _lastYAxisLabel = '';

// Populate selects
function initSelects() {
    const xSel = document.getElementById('x-select');
    const ySel = document.getElementById('y-select');
    const zSel = document.getElementById('z-select');
    
    COLUMNS.forEach(col => {
        const op1 = new Option(col, col);
        const op2 = new Option(col, col);
        const op3 = new Option(col, col);
        xSel.add(op1);
        ySel.add(op2);
        zSel.add(op3);
    });
    
    if (COLUMNS.length > 1) {
        ySel.selectedIndex = 1;
    }
}

function toggleAxis(axis) {
    var btn = document.getElementById('toggle-' + axis);
    if (axis === 'x') {
        _showXLabel = !_showXLabel;
        btn.classList.toggle('on', _showXLabel);
        Plotly.relayout('chart', { 'xaxis.title': _showXLabel ? _lastXAxisLabel : '' });
    } else {
        _showYLabel = !_showYLabel;
        btn.classList.toggle('on', _showYLabel);
        Plotly.relayout('chart', { 'yaxis.title': _showYLabel ? _lastYAxisLabel : '' });
    }
}

function currentType() { return _currentType; }

function getX() { return document.getElementById('x-select').value || COLUMNS[0]; }
function getY() { return document.getElementById('y-select').value || COLUMNS[0]; }

function getNumericCols(excludeX) {
    if (!DATA.length) return [];
    const x = excludeX ? getX() : null;
    return COLUMNS.filter(c => c !== x && typeof DATA[0][c] === 'number');
}

function selectChart(btn, chartType) {
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    _currentType = chartType;
    document.getElementById('z-select-group').style.display = chartType === 'heatmap' ? 'flex' : 'none';
    render(chartType);
}

function prettyLabel(col) {
    return col.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/_/g, ' ')
        .split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function render(chartType) {
    const chartDiv = document.getElementById('chart');
    const tableDiv = document.getElementById('table-container');
    const caption = document.getElementById('caption');

    var actionsDiv = document.querySelector('.chart-actions');
    if (chartType === 'table') {
        chartDiv.style.display = 'none';
        tableDiv.style.display = 'block';
        if (actionsDiv) actionsDiv.style.display = 'none';
        renderTable();
        caption.textContent = DATA.length + ' rows';
        return;
    }
    if (actionsDiv) actionsDiv.style.display = 'flex';

    chartDiv.style.display = 'block';
    tableDiv.style.display = 'none';

    const x = getX();
    _lastXAxisLabel = prettyLabel(x);
    const xLabel = _showXLabel ? _lastXAxisLabel : '';
    const labels = DATA.map(r => r[x] ?? '');
    const maxLabelLen = Math.max(...labels.map(l => String(l).length), 0);
    const needsRotation = DATA.length > 6 || maxLabelLen > 12;
    const tickAngle = needsRotation ? -45 : 0;
    const bMargin = tickAngle ? Math.max(80, Math.min(300, maxLabelLen * 6)) : 40;

    if (chartType === 'grouped_bar') {
        const yCols = getNumericCols(true);
        if (yCols.length < 2) { renderSingleBar(labels, tickAngle, bMargin); return; }
        const traces = yCols.map((col, i) => ({
            type: 'bar', name: col,
            x: labels, y: DATA.map(r => r[col] || 0),
            marker: { color: BAR_COLORS[i % BAR_COLORS.length] },
            text: DATA.map(r => r[col] || 0), textposition: 'outside',
        }));
        Plotly.newPlot(chartDiv, traces, {
            barmode: 'group',
            margin: { ...MARGINS.standard, b: bMargin },
            xaxis: { title: xLabel, tickangle: tickAngle, automargin: true },
            yaxis: { automargin: true },
            autosize: true, dragmode: false,
        }, PLOTLY_CFG);
        caption.textContent = DATA.length + ' items';
        return;
    }

    if (chartType === 'heatmap') { renderHeatmap(labels, x); return; }

    const yCol = getY();
    _lastYAxisLabel = prettyLabel(yCol);
    const yLabel = _showYLabel ? _lastYAxisLabel : '';
    const values = DATA.map(r => r[yCol] || 0);

    const displayTitle = (yLabel + ' by ' + xLabel);
    document.getElementById('chart-title').textContent = displayTitle;

    if (chartType === 'bar') {
        renderSingleBar(labels, tickAngle, bMargin, xLabel, yLabel);
    } else if (chartType === 'horizontal_bar') {
        const height = Math.max(DATA.length * 32 + 80, 400);
        Plotly.newPlot(chartDiv, [{
            type: 'bar', y: labels, x: values, orientation: 'h',
            marker: { color: BRAND.primary },
            text: values, textposition: 'outside', cliponaxis: false,
        }], {
            margin: MARGINS.horizontal_bar,
            xaxis: { title: yLabel, automargin: true },
            yaxis: { title: xLabel, automargin: true },
            height: height, autosize: true, dragmode: false,
        }, PLOTLY_CFG);
    } else if (chartType === 'pie') {
        const total = values.reduce((a, b) => a + (typeof b === 'number' ? b : 0), 0);
        Plotly.newPlot(chartDiv, [{
            type: 'pie', labels: labels, values: values,
            hole: 0.5,
            textposition: 'outside',
            textfont: { size: 10 },
            marker: { colors: PIE_COLORS.slice(0, DATA.length) },
            sort: false,
        }], {
            margin: { t: 50, b: 50, l: 50, r: 50 },
            height: 500, autosize: true, showlegend: true,
            annotations: [{ text: total.toLocaleString(), x: 0.5, y: 0.5,
                font: { size: 20, color: BRAND.navy, weight: 'bold' },
                showarrow: false }],
        }, PLOTLY_CFG);
    } else if (chartType === 'scatter') {
        Plotly.newPlot(chartDiv, [{
            type: 'scatter', x: labels, y: values, mode: 'markers',
            marker: { color: BRAND.primary, size: 10 },
        }], {
            margin: MARGINS.standard,
            xaxis: { title: xLabel, automargin: true },
            yaxis: { title: yLabel, automargin: true },
            autosize: true, dragmode: false,
        }, PLOTLY_CFG);
    } else if (chartType === 'line') {
        Plotly.newPlot(chartDiv, [{
            type: 'scatter', x: labels, y: values, mode: 'lines+markers',
            line: { color: BRAND.primary },
            marker: { size: 6 },
        }], {
            margin: MARGINS.standard,
            xaxis: { title: xLabel, automargin: true },
            yaxis: { title: yLabel, automargin: true },
            autosize: true, dragmode: false,
        }, PLOTLY_CFG);
    }
    caption.textContent = DATA.length + ' items';
}

function renderSingleBar(labels, tickAngle, bMargin, xLabel, yLabel) {
    const yCol = getY();
    const values = DATA.map(r => r[yCol] || 0);
    Plotly.newPlot('chart', [{
        type: 'bar', x: labels, y: values,
        marker: { color: BRAND.primaryDark },
        text: values, textposition: 'outside',
    }], {
        margin: { ...MARGINS.standard, b: bMargin },
        xaxis: { title: xLabel || prettyLabel(getX()), tickangle: tickAngle, automargin: true },
        yaxis: { title: yLabel || prettyLabel(yCol), automargin: true },
        autosize: true, dragmode: false,
    }, PLOTLY_CFG);
}

function renderHeatmap(labels, xCol) {
    const yCol = document.getElementById('y-select').value;
    let zCol = document.getElementById('z-select').value || yCol;
    const xCats = [...new Map(DATA.map(r => [r[xCol], true])).keys()];
    const yCats = [...new Map(DATA.map(r => [r[yCol], true])).keys()];
    const lookup = {};
    DATA.forEach(r => { lookup[r[yCol] + '||' + r[xCol]] = parseFloat(r[zCol]) || 0; });
    const zMatrix = yCats.map(yc => xCats.map(xc => lookup[yc + '||' + xc] || 0));
    Plotly.newPlot('chart', [{
        type: 'heatmap', z: zMatrix, x: xCats, y: yCats,
        colorscale: [[0, '#f8f7fc'], [0.5, BRAND.primaryLight], [1, BRAND.primaryDark]],
        showscale: true, hoverongaps: false,
    }], {
        margin: { t: 30, b: 180, l: 20, r: 20 },
        xaxis: { tickangle: -45, automargin: true },
        yaxis: { automargin: true },
        height: Math.max(yCats.length * 32 + 200, 520),
        autosize: true, dragmode: false,
    }, PLOTLY_CFG);
    document.getElementById('caption').textContent = xCats.length + ' x ' + yCats.length + ' matrix';
}

function renderTable() {
    const container = document.getElementById('table-container');
    if ($.fn.DataTable.isDataTable('#data-table')) { $('#data-table').DataTable().destroy(); }
    const table = document.createElement('table');
    table.id = 'data-table';
    table.className = 'display';
    table.style.width = '100%';
    const thead = table.createTHead();
    const headerRow = thead.insertRow();
    COLUMNS.forEach(c => {
        const th = document.createElement('th');
        th.textContent = c;
        headerRow.appendChild(th);
    });
    const tbody = table.createTBody();
    DATA.forEach(row => {
        const tr = tbody.insertRow();
        COLUMNS.forEach(c => {
            const td = tr.insertCell();
            td.textContent = String(row[c] ?? '');
        });
    });
    container.replaceChildren(table);
    $('#data-table').DataTable({ dom: 'frtip', pageLength: 20, order: [] });
}

initSelects();
render('table');
</script>
</body></html>
"""

def render_message_content(content: str):
    # Handle JSON blocks for the advanced dashboard
    if "```json" in content:
        parts = re.split(r"```json(.*?)```", content, flags=re.DOTALL)
        for i, part in enumerate(parts):
            if i % 2 == 0:
                if part.strip():
                    st.markdown(part)
            else:
                try:
                    data_json = json.loads(part.strip())
                    raw_data = data_json.get('data', [])
                    columns = data_json.get('columns', [])
                    
                    if not columns and raw_data:
                        columns = list(raw_data[0].keys())

                    if raw_data:
                        # Inject data and columns into the template
                        html_content = DASHBOARD_TEMPLATE.replace("__DATA__", json.dumps(raw_data))
                        html_content = html_content.replace("__COLUMNS__", json.dumps(columns))
                        
                        components.html(html_content, height=800, scrolling=True)
                    else:
                        st.info("Query returned no data for visualization.")
                except Exception as e:
                    st.error(f"Error rendering dashboard: {e}")
                    st.code(part)
    
    # Also handle standard HTML blocks if any remain (legacy support)
    elif "```html" in content:
        parts = re.split(r"```html(.*?)```", content, flags=re.DOTALL)
        for i, part in enumerate(parts):
            if i % 2 == 0:
                if part.strip():
                    st.markdown(part)
            else:
                if part.strip():
                    components.html(part, height=500, scrolling=True)
    else:
        st.markdown(content)

def safe_db_run(db: SQLDatabase, query: str):
    try:
        res = str(db.run(query))
        if len(res) > 20000:
            return res[:20000] + "\n...[TRUNCATED due to length]..."
        return res
    except Exception as e:
        return f"Error: {e}"

def init_database(user: str, password: str, host: str, port: str, database: str) -> SQLDatabase:
  encoded_password = urllib.parse.quote_plus(password)
  db_uri = f"mysql+mysqlconnector://{user}:{encoded_password}@{host}:{port}/{database}"
  return SQLDatabase.from_uri(db_uri)

def get_sql_chain(db):
  template = """
    You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database.
    Based on the table schema below, write a SQL query that would answer the user's question. Take the conversation history into account.
    
    <SCHEMA>{schema}</SCHEMA>
    
    Conversation History: {chat_history}
    
    Write only the SQL query and nothing else. Do not wrap the SQL query in any other text, not even backticks.
    
    IMPORTANT: Unless the user wants all specific aggregate rows, ALWAYS append a LIMIT (e.g. LIMIT 50) to your SQL queries to prevent out-of-memory outputs.
    
    For example:
    Question: which 3 artists have the most tracks?
    SQL Query: SELECT ArtistId, COUNT(*) as track_count FROM Track GROUP BY ArtistId ORDER BY track_count DESC LIMIT 3;
    Question: Name 10 artists
    SQL Query: SELECT Name FROM Artist LIMIT 10;
    
    Your turn:
    
    Question: {question}
    SQL Query:
    """
    
  prompt = ChatPromptTemplate.from_template(template)
  
  llm = ChatOpenAI(model="gpt-4o-mini")
  # llm = ChatGroq(model="mixtral-8x7b-32768", temperature=0)
  
  def get_schema(_):
    return db.get_table_info()
  
  return (
    RunnablePassthrough.assign(schema=get_schema)
    | prompt
    | llm
    | StrOutputParser()
  )
    
def get_response(user_query: str, db: SQLDatabase, chat_history: list):
  sql_chain = get_sql_chain(db)
  template = """
    You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database.
    Based on the table schema below, question, sql query, and sql response, write a natural language response.
    
    If the data is suitable for a chart or visualization, or if the user explicitly asks for one (or for any generic data/comparison questions), you must provide the data in a structured JSON format enclosed within ```json ... ``` blocks. 
    The JSON structure MUST be:
    {{
      "columns": ["column1", "column2", ...],
      "data": [{{ "column1": value1, "column2": value2 }}, ...]
    }}
    Include all relevant columns from the SQL response in the JSON.
    Do NOT write HTML or JavaScript. Only provide the natural language response and the JSON block.
    
    <SCHEMA>{schema}</SCHEMA>

    Conversation History: {chat_history}
    SQL Query: <SQL>{query}</SQL>
    User question: {question}
    SQL Response: {response}"""
  
  prompt = ChatPromptTemplate.from_template(template)
  
  llm = ChatOpenAI(model="gpt-4o-mini")
  # llm = ChatGroq(model="mixtral-8x7b-32768", temperature=0)
  
  chain = (
    RunnablePassthrough.assign(query=sql_chain).assign(
      schema=lambda _: db.get_table_info(),
      response=lambda vars: safe_db_run(db, vars["query"]),
    )
    | prompt
    | llm
    | StrOutputParser()
  )
  
  return chain.invoke({
    "question": user_query,
    "chat_history": chat_history,
  })
    
  
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
      AIMessage(content="Hello! I'm a SQL assistant. Ask me anything about your database."),
    ]

st.set_page_config(page_title="Chat with MySQL", page_icon=":speech_balloon:")

st.title("Chat with MySQL")

with st.sidebar:
    st.subheader("Settings")
    st.write("This is a simple chat application using MySQL. Connect to the database and start chatting.")
    
    st.text_input("Host", value=os.environ.get("DB_HOST", "localhost"), key="Host")
    st.text_input("Port", value=os.environ.get("DB_PORT", "3306"), key="Port")
    st.text_input("User", value=os.environ.get("DB_USER", "root"), key="User")
    st.text_input("Password", type="password", value=os.environ.get("DB_PASSWORD", "admin"), key="Password")
    st.text_input("Database", value=os.environ.get("DB_NAME", "Chinook"), key="Database")
    
    if st.button("Connect"):
        with st.spinner("Connecting to database..."):
            db = init_database(
                st.session_state["User"],
                st.session_state["Password"],
                st.session_state["Host"],
                st.session_state["Port"],
                st.session_state["Database"]
            )
            st.session_state.db = db
            st.success("Connected to database!")
    
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            render_message_content(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(message.content)

user_query = st.chat_input("Type a message...")
if user_query is not None and user_query.strip() != "":
    st.session_state.chat_history.append(HumanMessage(content=user_query))
    
    with st.chat_message("Human"):
        st.markdown(user_query)
        
    with st.chat_message("AI"):
        with st.spinner("Thinking..."):
            recent_history = st.session_state.chat_history[-6:]
            response = get_response(user_query, st.session_state.db, recent_history)
        render_message_content(response)
        
    st.session_state.chat_history.append(AIMessage(content=response))