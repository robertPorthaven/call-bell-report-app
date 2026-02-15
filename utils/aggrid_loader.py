# assets/aggrid_loader.py
from __future__ import annotations
import re
from pathlib import Path
from st_aggrid import JsCode

def load_pill_renderer() -> JsCode:
    return JsCode("""
    (function() {
        function PillRenderer() {}

        PillRenderer.prototype.init = function(params) {
            this.eGui = document.createElement('img');
            this.eGui.src = params.value || '';
            this.eGui.style.cssText = 'height:100%; object-fit:none; object-position:left center;';
        };

        PillRenderer.prototype.getGui    = function() { return this.eGui; };
        PillRenderer.prototype.refresh   = function() { return false; };
        PillRenderer.prototype.destroy   = function() {};

        return PillRenderer;
    })()
    """)

def load_aggrid_css(theme_color) -> dict[str, dict[str, str]]:
    css = Path("assets/aggrid.css").read_text(encoding="utf-8")
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
    css = css.replace('--theme-color--', theme_color)  # Replace with actual amber color

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