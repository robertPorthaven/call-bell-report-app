# utils/aagrid_dataframe.py
from pathlib import Path
import re
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# --- Brand colours ---
AMBER = "#f09c2e"
SLATE = "#757a6e"
OCEAN = "#3e6f86"

AGGRID_CSS_PATH = Path(__file__).parent / "aggrid.css"


def load_aggrid_css(theme_color: str) -> dict[str, dict[str, str]]:
    """
    Load CSS from aggrid.css and translate to st_aggrid custom_css dict.
    Adds !important to ensure precedence over theme defaults.
    """
    css = Path(AGGRID_CSS_PATH).read_text(encoding="utf-8")
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
    css = css.replace('--theme-color--', theme_color)

    result: dict[str, dict[str, str]] = {}
    for match in re.finditer(r'([^{]+)\{([^}]+)\}', css):
        selector = match.group(1).strip()
        body = match.group(2).strip()
        props: dict[str, str] = {}
        for line in body.splitlines():
            line = line.strip().rstrip(';')
            if ':' in line:
                prop, _, val = line.partition(':')
                props[prop.strip()] = val.strip() + ' !important'
        if props:
            result[selector] = props
    return result


def load_pill_renderer_wrapping_svgs() -> JsCode:
    """
    Robust pill renderer that prefers JSON-string arrays for 'Events'.
    - If value is a JSON string: JSON.parse -> list[data-URIs] or labels.
    - If value is already an array: use directly.
    - If value is an Arrow List payload (fallback), try to decode to array.

    Notes:
    * No manual row-height forcing (ideal settings let AG Grid size rows).
    * Tags the cell with data-events-lines="one|multi" to vertically center
      single-line rows while keeping multi-line rows top-stacked.
    """
    return JsCode(r"""
    (function() {
      function PillRenderer() {}

      // ---------- helpers ----------
      function idxObjToArray(x){
        if (Array.isArray(x) || (x && x.BYTES_PER_ELEMENT)) return x;
        if (!x || typeof x !== 'object') return null;
        const keys = Object.keys(x).filter(k => /^\d+$/.test(k)).sort((a,b)=>Number(a)-Number(b));
        return keys.length ? keys.map(k => x[k]) : null;
      }
      function findTypedArray(obj, maxDepth=2){
        try {
          const stack = [{v:obj, d:0}];
          while (stack.length){
            const {v,d} = stack.pop();
            if (!v) continue;
            if ((v.BYTES_PER_ELEMENT|0) > 0 && typeof v.length === 'number') return v;
            if (d >= maxDepth || typeof v !== 'object') continue;
            for (const k in v){ if (Object.prototype.hasOwnProperty.call(v,k)) stack.push({v:v[k], d:d+1}); }
          }
        } catch(_) {}
        return null;
      }
      function decodeArrowList(val){
        const node = (val && (val.data && val.data[0])) ? val.data[0] : val;
        if (!node || typeof node !== 'object') return null;

        let offsets = idxObjToArray(node.valueOffsets || node._offsets || node.offsets);
        let values  = idxObjToArray(node.values       || node._values  );
        if (!values) {
          const dataField = node.data || node.byteData || null;
          values = idxObjToArray(dataField) || findTypedArray(dataField) || findTypedArray(node);
        }
        if (!offsets || !values) return null;

        const u8 = (values.BYTES_PER_ELEMENT) ? values
                 : Array.isArray(values)     ? new Uint8Array(values)
                 : null;
        const off = (offsets.BYTES_PER_ELEMENT) ? offsets
                 : Array.isArray(offsets)     ? new Int32Array(offsets)
                 : null;
        if (!u8 || !off) return null;

        const td = new TextDecoder('utf-8');
        const out = [];
        const n = (typeof off.length === 'number') ? off.length - 1 : 0;
        for (let i=0;i<n;i++){
          const s = Number(off[i]), e = Number(off[i+1]);
          if (Number.isFinite(s) && Number.isFinite(e) && e >= s && s >= 0 && e <= u8.length) {
            out.push(td.decode(u8.subarray(s, e)));
          }
        }
        return out;
      }
      function toArray(val){
        // 1) JSON string (preferred for Option A)
        if (typeof val === 'string') {
          try { const a = JSON.parse(val); if (Array.isArray(a)) return a; } catch(e){}
          if (val.indexOf('data:image') !== -1){
            const parts = val.split(/(?=data:image)/).map(s=>s.trim()).filter(Boolean);
            if (parts.length) return parts;
          }
          if (val.indexOf('>') >= 0 || val.indexOf('➤') >= 0){
            return val.split(/\s*[>➤]\s*/).filter(Boolean);
          }
          return [val];
        }
        // 2) Plain array
        if (Array.isArray(val)) return val;
        // 3) Arrow fallback
        const dec = decodeArrowList(val);
        return dec || [];
      }

      function styleFor(lbl){
        const l = String(lbl).toLowerCase().trim();
        const S = {
          "call":        {bg:"#ffffff", border:"#f09c2e", fg:"#000000"},
          "priority":    {bg:"#f09c2e", border:"#f09c2e", fg:"#ffffff"},
          "present":     {bg:"#757a6e", border:"#757a6e", fg:"#ffffff"},
          "emergency":   {bg:"#ff0000", border:"#ff0000", fg:"#ffffff"},
          "reset":       {bg:"#ffffff", border:"#757a6e", fg:"#000000"},
          "assistance":  {bg:"#3e6f86", border:"#757a6e", fg:"#ffffff"},
        };
        return S[l] || {bg:"#ffffff", border:"#ff0000", fg:"#ff0000"};
      }
      function pillWidth(lbl){
        const CHAR_W=8.5, HPAD=4, MIN_W=52; const t=String(lbl).trim();
        return Math.max(MIN_W, Math.floor(t.length*CHAR_W + 2*HPAD));
      }
      function makePillSVG(label, w, h, r, colors){
        const xmlns='http://www.w3.org/2000/svg';
        const svg=document.createElementNS(xmlns,'svg'); svg.setAttribute('width', String(w)); svg.setAttribute('height', String(h));
        const rect=document.createElementNS(xmlns,'rect');
        rect.setAttribute('x','1'); rect.setAttribute('y','1');
        rect.setAttribute('width', String(w-2)); rect.setAttribute('height', String(h-2));
        rect.setAttribute('rx', String(r)); rect.setAttribute('ry', String(r));
        rect.setAttribute('fill', colors.bg); rect.setAttribute('stroke', colors.border); rect.setAttribute('stroke-width','2');
        const text=document.createElementNS(xmlns,'text');
        text.setAttribute('x', String(Math.floor(w/2))); text.setAttribute('y', String(Math.floor(h/2)));
        text.setAttribute('dominant-baseline','middle'); text.setAttribute('text-anchor','middle');
        text.setAttribute('font-family','Consolas, Menlo, ui-monospace, monospace');
        text.setAttribute('font-size','12'); text.setAttribute('font-weight','600'); text.setAttribute('fill', colors.fg);
        text.textContent=String(label).toUpperCase();
        svg.appendChild(rect); svg.appendChild(text); return svg;
      }

      function tagOneOrMulti(container, params){
        try {
          const cell = (params && (params.eGridCell || container.closest('.ag-cell'))) || null;
          if (!cell) return;
          const oneLine = (container.clientHeight || 0) <= 30;
          cell.setAttribute('data-events-lines', oneLine ? 'one' : 'multi');
        } catch(_) {}
      }

      PillRenderer.prototype.init = function(params) {
        const container = document.createElement('div');
        container.className = 'pill-container';

        try{
          const arr = toArray(params.value);
          const isDataURI = (s) => typeof s === 'string' && s.startsWith('data:image/svg+xml;base64,');

          if (arr.length && arr.every(isDataURI)){
            for (let i=0;i<arr.length;i++){
              const img=document.createElement('img');
              img.src=arr[i]; img.alt='event';
              img.style.height='24px'; img.style.display='inline-block'; img.style.verticalAlign='middle';
              container.appendChild(img);
              if (i < arr.length-1){ const a=document.createElement('span'); a.className='arrow'; a.textContent='➤'; container.appendChild(a); }
            }
          } else if (arr.length){
            const H=24, R=H/2;
            for (let i=0;i<arr.length;i++){
              const lbl=arr[i], w=pillWidth(lbl);
              const svg=makePillSVG(lbl, w, H, R, styleFor(lbl));
              const wrap=document.createElement('span'); wrap.style.display='inline-flex'; wrap.style.alignItems='center';
              wrap.appendChild(svg); container.appendChild(wrap);
              if (i < arr.length-1){ const a=document.createElement('span'); a.className='arrow'; a.textContent='➤'; container.appendChild(a); }
            }
          } else {
            const span=document.createElement('span'); span.style.color='#999'; span.textContent='(no events)'; container.appendChild(span);
          }
        } catch(e){
          console.error("PillRenderer error:", e);
          const err=document.createElement('span'); err.style.color='#d00'; err.textContent='(renderer error)'; container.appendChild(err);
        }

        this.eGui = container;

      };

      PillRenderer.prototype.getGui = function(){ return this.eGui; };
      PillRenderer.prototype.refresh = function(){ return false; };
      PillRenderer.prototype.destroy = function(){};
      return PillRenderer;
    })()
    """)


def render_call_grid(
    df_in,
    unique_key: str,
    theme_color: str = OCEAN,
):
    """
    Ideal-settings grid for Option A (JSON strings in Events):
      - domLayout='autoHeight'
      - Events column wrapText + autoHeight
      - Renderer handles JSON/array/Arrow, no manual row sizing
    """
    if df_in.empty:
        st.info("None", icon="👍")
        return

    df = df_in.copy()

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(resizable=True, sortable=False, filter=False)

    if "Events" in df.columns:
        gb.configure_column("Room Location", minWidth=150)
        gb.configure_column("Call Type", minWidth=150)
        gb.configure_column("Start", minWidth=150)

        gb.configure_column(
            "Events",
            cellRenderer=load_pill_renderer_wrapping_svgs(),
            wrapText=True,        # allow wrapping
            autoHeight=True,      # let AG Grid expand rows automatically
            minWidth=700,
        )

    gb.configure_grid_options(
        domLayout='autoHeight',
        enableCellTextSelection=True,
    )

    AgGrid(
        df,
        gridOptions=gb.build(),
        custom_css=load_aggrid_css(theme_color),
        allow_unsafe_jscode=True,
        theme="alpine",
        key=unique_key,
        fit_columns_on_grid_load=True,
    )