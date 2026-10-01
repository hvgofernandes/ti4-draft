"""Generate a self-contained QA page from the faction assets manifest."""

from __future__ import annotations

import json
import os
from pathlib import Path

from build_assets import MANIFEST, QA_ROOT, ROOT


def gallery_path(project_relative: str | None) -> str | None:
    if not project_relative:
        return None
    resolved = (ROOT / project_relative).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"Unsafe gallery image path: {project_relative}")
    return Path(os.path.relpath(resolved, QA_ROOT)).as_posix()


def build() -> Path:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data = []
    for faction in manifest["factions"]:
        data.append({**faction, "sourceUrl": gallery_path(faction["source"]),
                     "finalUrl": gallery_path(faction["final"]),
                     "intermediateUrl": gallery_path(faction.get("intermediate")),
                     "previewUrl": gallery_path((faction.get("sourcePreview") or faction.get("preview") or {}).get("path"))})
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    counts = manifest["counts"]
    page = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TI4-Draft · QA de símbolos</title>
<style>
:root{{--bg:#0b1019;--panel:#162031;--line:#344154;--text:#eef3fa;--muted:#a9b8c9;--accent:#77dcc9;--warn:#f5bf70}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at top right,#263b53,#0b1019 48%);font:16px/1.45 system-ui,Segoe UI,sans-serif;color:var(--text)}}
header,main,footer{{max-width:1450px;margin:auto;padding:28px}}header{{padding-top:46px}}h1{{font-size:clamp(30px,4vw,52px);margin:4px 0}}p{{color:var(--muted)}}.eyebrow{{color:var(--accent);font-size:12px;letter-spacing:.2em;text-transform:uppercase;font-weight:800}}
.summary{{display:flex;gap:14px;flex-wrap:wrap;margin:28px 0}}.stat{{background:#1a283a;border:1px solid var(--line);border-radius:16px;padding:16px 22px;min-width:150px}}.stat strong{{display:block;font-size:28px}}.stat span{{color:var(--muted)}}
.notice{{border:1px solid #9b753f;background:#42351f;border-radius:14px;padding:16px 20px;color:#ffe6b7;max-width:1050px}}
.controls{{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:30px 0 22px}}button,input{{font:inherit}}button{{border:1px solid var(--line);background:#19283a;color:var(--text);padding:10px 14px;border-radius:9px;cursor:pointer}}button[aria-pressed=true]{{background:#266457;border-color:#71d3c0}}input{{background:#101b29;color:var(--text);border:1px solid var(--line);border-radius:9px;padding:10px 13px;min-width:230px}}.controls label{{color:var(--muted)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,480px),1fr));gap:18px}}article{{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px;min-width:0}}article h2{{margin:0 0 3px;font-size:20px}}.set{{color:var(--accent);font-size:13px;text-transform:uppercase;letter-spacing:.06em}}.badge{{display:inline-block;color:#ffd49a;background:#573b20;border-radius:30px;padding:4px 9px;font-size:12px;margin:12px 0}}.badge.ready{{background:#1a604f;color:#b0f3db}}
.compare{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));align-items:center;gap:6px;margin:8px 0}}.column label{{display:block;font-size:10px;color:var(--muted);font-weight:700;margin-bottom:5px;min-height:28px}}.imagebox{{height:160px;border-radius:9px;border:1px solid var(--line);display:grid;place-items:center;overflow:hidden;cursor:zoom-in}}.imagebox img{{max-width:95%;max-height:95%;object-fit:contain}}.imagebox.empty{{color:#b5bac1;font-size:12px;text-align:center;padding:12px;cursor:default}}.arrow{{text-align:center;color:var(--accent);font-size:22px}}.light{{background:#f6f6ed;color:#333}}.dark{{background:#06090e}}.checker{{background-color:#e9e9e9;background-image:linear-gradient(45deg,#bbb 25%,transparent 25%),linear-gradient(-45deg,#bbb 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#bbb 75%),linear-gradient(-45deg,transparent 75%,#bbb 75%);background-size:22px 22px;background-position:0 0,0 11px,11px -11px,-11px 0}}
.facts{{color:var(--muted);font-size:13px;margin-top:12px}}.facts div{{margin:3px 0}}.warnings{{color:#f2c481;font-size:12px;margin-top:10px;overflow-wrap:anywhere}}dialog{{border:1px solid #65847f;background:#0c1420;color:var(--text);padding:18px;border-radius:16px;max-width:min(94vw,1000px);max-height:94vh}}dialog::backdrop{{background:#000c}}dialog img{{display:block;max-width:86vw;max-height:75vh;object-fit:contain;margin:auto}}dialog .modal-head{{display:flex;justify-content:space-between;gap:30px;align-items:center;margin-bottom:12px}}footer{{color:var(--muted);font-size:13px}}
</style></head><body>
<header><div class="eyebrow">TI4-Draft / Fase 3.1.6</div><h1>QA dos símbolos de facção</h1>
<p>Original → isolamento clássico → normalização. Clique para ampliar e alterne o fundo para inspecionar bordas e resíduos.</p>
<div class="summary"><div class="stat"><strong>{counts['catalog']}</strong><span>facções no catálogo</span></div><div class="stat"><strong>{counts['mappedSources']}</strong><span>sources locais mapeados</span></div><div class="stat"><strong>{counts.get('isolated',0)}</strong><span>intermediários isolados</span></div><div class="stat"><strong>{counts['outputs']}</strong><span>finais candidatos</span></div><div class="stat"><strong>{counts['readyForReview']}</strong><span>prontos para revisão humana</span></div><div class="stat"><strong>{counts['needsManualReview']}</strong><span>revisões manuais</span></div></div>
<div class="notice">Todos os resultados são candidatos para revisão humana. Crops, métodos, parâmetros e hashes permitem conferir as transformações. A aprovação definitiva pertence ao usuário.</div></header>
<main><div class="controls" id="controls"><label>Conjunto</label><button data-set="all" aria-pressed="true">Todas</button><button data-set="base">Base</button><button data-set="pok">PoK</button><button data-set="thunders-edge">Thunder's Edge</button><button data-set="discordant-stars">Discordant Stars</button><label>Status</label><button data-status="all" aria-pressed="true">Todas</button><button data-status="clean">Sem alertas</button><button data-status="ready">Ready for review</button><button data-status="manual">Needs manual review</button><button data-status="warnings">Warnings</button><label>Source</label><button data-source="all" aria-pressed="true">All</button><button data-source="atlas">Atlas</button><button data-source="token">Token / ficha</button><button data-source="ds">DS</button><label>Fundo</label><button data-bg="checker" aria-pressed="true">Checkerboard</button><button data-bg="light">Claro</button><button data-bg="dark">Escuro</button><input id="search" placeholder="Buscar facção" aria-label="Buscar facção"></div>
<p id="resultCount"></p><section class="grid" id="grid"></section></main>
<dialog id="zoom"><div class="modal-head"><strong id="zoomTitle"></strong><button id="closeZoom">Fechar</button></div><div class="imagebox checker" style="height:auto;min-height:70vh"><img id="zoomImage" alt="Imagem ampliada"></div></dialog>
<footer>Catálogo: migration da Fase 3.1. <a href="faction-assets-manifest.json" style="color:#93e7d8">Manifest</a> · <a href="qa-report.json" style="color:#93e7d8">Relatório automático</a> · <a href="official-extraction.json" style="color:#93e7d8">Extração oficial</a> · <a href="discordant-stars-mapping.json" style="color:#93e7d8">Mapping DS</a>. Os originais e candidatos da Fase 3.1.5 permanecem inalterados.</footer>
<script>const items={payload};let set='all',status='all',source='all',bg='checker';const grid=document.querySelector('#grid');
const esc=s=>String(s??'').replace(/[&<>\"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[c]));
function image(url,label,zoomUrl){{return url?`<div class="imagebox ${{bg}}" data-zoom="${{esc(zoomUrl||url)}}" data-title="${{esc(label)}}"><img src="${{esc(url)}}" alt="${{esc(label)}}" loading="lazy"></div>`:`<div class="imagebox empty ${{bg}}">Arquivo ainda indisponível</div>`}}
function draw(){{const q=document.querySelector('#search').value.toLowerCase().trim();const visible=items.filter(x=>(set==='all'||x.contentSet===set)&&(source==='all'||x.sourceKind===source)&&(status==='all'||(status==='ready'?x.status==='READY_FOR_REVIEW':status==='manual'?x.status==='NEEDS_MANUAL_REVIEW':status==='warnings'?x.warnings.length>0:x.status==='READY_FOR_REVIEW'&&x.warnings.length===0))&&(!q||x.name.toLowerCase().includes(q)||x.slug.includes(q)));document.querySelector('#resultCount').textContent=`${{visible.length}} de ${{items.length}} facções`;
grid.innerHTML=visible.map(x=>`<article><h2>${{esc(x.name)}}</h2><div class="set">${{esc(x.contentSet)}} · ${{esc(x.sourceKind||"pendente")}}</div><span class="badge ${{x.status==="READY_FOR_REVIEW"?"ready":""}}">${{esc(x.status)}}</span><div class="compare"><div class="column"><label>SOURCE ORIGINAL · ROI</label>${{image(x.previewUrl||x.sourceUrl,x.name+" · source original completo",x.sourceUrl)}}</div><div class="column"><label>ISOLATED / INTERMEDIATE</label>${{image(x.intermediateUrl,x.name+" · intermediate")}}</div><div class="column"><label>FINAL NORMALIZED</label>${{image(x.finalUrl,x.name+" · final")}}</div></div><div class="facts"><div>Dimensões: original ${{x.sourceWidth??"—"}}×${{x.sourceHeight??"—"}} · isolado ${{x.intermediateWidth??"—"}}×${{x.intermediateHeight??"—"}} · final ${{x.finalWidth??"—"}}×${{x.finalHeight??"—"}}</div><div>Método: ${{esc(x.extraction?.method||"pendente")}}</div><div>Crop [x0,y0,x1,y1]: ${{x.extraction?.crop?.join(", ")??"pendente"}}</div><div>Alpha original: ${{x.sourceTransparent?"sim":"opaco"}} · final: ${{x.transparent?"sim":"pendente"}}</div><div>BBox final: ${{x.finalMetrics?.bounds?.join(", ")??"pendente"}} · aspecto: ${{x.finalMetrics?.aspectRatio??"—"}}</div><div>Ocupação alpha: ${{x.finalMetrics?Math.round(x.finalMetrics.alphaOccupancy*1000)/10+"%":"—"}} · densidade: ${{x.finalMetrics?Math.round(x.finalMetrics.density*1000)/10+"%":"—"}}</div><div>Componentes: ${{x.finalMetrics?.componentCount??"—"}} · fringe: ${{x.finalMetrics?Math.round(x.finalMetrics.alphaFringeRatio*1000)/10+"%":"—"}}</div><div style="font:10px Consolas,monospace;overflow-wrap:anywhere">${{esc(x.source)}}</div><div>Slug: ${{esc(x.slug)}}</div></div><div class="warnings">${{esc(x.warnings.join(" · ")||"Sem alertas automáticos")}}</div><details><summary style="cursor:pointer;color:#93e7d8">Proveniência e métricas</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere;font-size:10px">${{esc(JSON.stringify({{source:x.source,sourceSha256:x.sourceSha256,intermediate:x.intermediate,intermediateSha256:x.intermediateSha256,final:x.final,finalSha256:x.finalSha256,extraction:x.extraction,processing:x.processing,intermediateMetrics:x.intermediateMetrics,finalMetrics:x.finalMetrics}},null,2))}}</pre></details></article>`).join("");}}
document.querySelector('#controls').addEventListener('click',e=>{{const b=e.target.closest('button');if(!b)return;let key=null;if(b.dataset.set){{set=b.dataset.set;key='set'}}if(b.dataset.status){{status=b.dataset.status;key='status'}}if(b.dataset.source){{source=b.dataset.source;key='source'}}if(b.dataset.bg){{bg=b.dataset.bg;key='bg'}}if(key){{document.querySelectorAll(`button[data-${{key}}]`).forEach(x=>x.setAttribute('aria-pressed',String(x===b)));draw()}}}});document.querySelector('#search').addEventListener('input',draw);
grid.addEventListener('click',e=>{{const box=e.target.closest('[data-zoom]');if(!box)return;document.querySelector('#zoomImage').src=box.dataset.zoom;document.querySelector('#zoomTitle').textContent=box.dataset.title;document.querySelector('#zoom .imagebox').className='imagebox '+bg;document.querySelector('#zoom').showModal()}});document.querySelector('#closeZoom').onclick=()=>document.querySelector('#zoom').close();draw();</script></body></html>"""
    output = QA_ROOT / "index.html"
    output.write_text(page, encoding="utf-8")
    return output


if __name__ == "__main__":
    print(build())
