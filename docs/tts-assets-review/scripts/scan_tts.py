"""Read-only TTS investigator. Writes only beneath the specified output directory.
Run with Python 3 + Pillow. No network requests; no Lua execution.
"""
import argparse, collections, hashlib, html, json, re, shutil
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image
URL = re.compile(r'https?://[^\s<>\"\'\\\]\)]+')
def norm(s): return re.sub(r'[^a-z0-9]', '', s.lower().replace('the ', ''))
def key(s): return re.sub(r'[^A-Za-z0-9]', '', s)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def walk(x, path='$'):
    yield path,x
    if isinstance(x,dict):
        for k,v in x.items(): yield from walk(v,path+'.'+k)
    elif isinstance(x,list):
        for i,v in enumerate(x): yield from walk(v,path+f'[{i}]')
def local_strings(x,path):
    if isinstance(x,dict):
        for k,v in x.items():
            if k not in ('ContainedObjects','States','ObjectStates'): yield from local_strings(v,path+'.'+k)
    elif isinstance(x,list):
        for i,v in enumerate(x): yield from local_strings(v,path+f'[{i}]')
    elif isinstance(x,str): yield path,x

def catalog(p):
    sql=Path(p).read_text(encoding='utf-8-sig')
    block=sql.split('WITH catalog(content_set_slug, name, slug, sort_order) AS (VALUES',1)[1].split(')\nINSERT INTO',1)[0]
    rows=re.findall(r"\('([^']+)', '((?:[^']|'')+)', '([^']+)', (\d+)\)",block)
    out=[dict(contentSet=a,name=b.replace("''","'"),slug=c,sortOrder=int(e)) for a,b,c,e in rows if a!='discordant-stars']
    assert len(out)==30 and collections.Counter(f['contentSet'] for f in out)=={'base':17,'pok':7,'thunders-edge':6}
    return out

def snapshot(root):
    return {str(p.relative_to(root)): [p.stat().st_size,p.stat().st_mtime_ns] for p in root.rglob('*') if p.is_file()}
def safe_copy(src,dst,root):
    src,dst,root=Path(src).resolve(),Path(dst).resolve(),Path(root).resolve()
    if not dst.is_relative_to(root) or dst==src: raise ValueError('Unsafe copy destination')
    digest=sha(src)
    if dst.exists():
        if sha(dst)!=digest: raise ValueError('Refusing to overwrite different candidate: '+str(dst))
    else:
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    assert sha(dst)==digest
    return digest

def generate_gallery(report,out):
    e=html.escape
    labels={'strong':'✓ candidato forte','ambiguous':'? múltiplos candidatos','weak':'⚠ candidato fraco','missing':'✕ nenhum candidato'}
    chunks=[]
    for f in report['factions']:
        cards=[]
        for c in f['candidates']:
            rel=c['relativeFile'];details=json.dumps({k:v for k,v in c.items() if k not in ('relativeFile',)},ensure_ascii=False,indent=2)
            preview=f'<img loading="lazy" src="{e(rel)}" alt="{e(f["name"]+" — "+c["assetType"])}">'
            if c.get('atlas'):
                a=c['atlas'];w,h=c['dimensions'];ratio=(w/a['columns'])/(h/a['rows'])
                preview=f'<div style="position:relative;overflow:hidden;aspect-ratio:{ratio}"><img loading="lazy" src="{e(rel)}" alt="Ficha de referência de {e(f["name"])}" style="position:absolute;max-width:none;width:{a["columns"]*100}%;height:{a["rows"]*100}%;left:-{a["column"]*100}%;top:-{a["row"]*100}%;border-radius:0"></div>'
                if (w,h,a['columns'],a['rows'])==(7090,4962,5,6):
                    x=a['column']*1418+1210;y=a['row']*827
                    preview+=f'<p>Zoom do emblema · região aproximada para inspeção</p><div role="img" aria-label="Zoom aproximado do emblema de {e(f["name"])}" style="width:208px;height:210px;margin:8px auto;background-image:url({e(rel)});background-size:7090px 4962px;background-position:-{x}px -{y}px;background-repeat:no-repeat"></div>'
            cards.append(f'<article><a href="{e(rel)}">{preview}</a><h3>{e(c["assetType"])}</h3><p>Confiança: {e(c["confidence"])} · {c["dimensions"][0]} × {c["dimensions"][1]}</p><p>{e(c["reason"])}</p><small>{e(Path(rel).name)}</small><details><summary>Proveniência e detalhes técnicos</summary><pre>{e(details)}</pre></details></article>')
        chunks.append(f'<section data-set="{f["contentSet"]}" data-status="{f["status"]}"><h2>{e(f["name"])}</h2><p>{e(f["contentSet"])} · {labels[f["status"]]} · validação humana pendente</p><div class="cards">'+(''.join(cards) or '<p>Nenhum arquivo candidato disponível no cache.</p>')+'</div></section>')
    stats=report['statistics']
    page='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TI4 · Revisão de emblemas TTS</title><style>body{font:16px system-ui;margin:0;background:#0c1422;color:#e6edf5}header,main{max-width:1500px;margin:auto;padding:28px}header{position:relative}h1{font-size:34px}p{line-height:1.5;color:#b8c9de}section{border-top:1px solid #34445b;padding:22px 0}.cards{display:flex;gap:18px;flex-wrap:wrap}article{background:#17243a;border-radius:12px;padding:16px;flex:1 1 280px;max-width:440px}img{width:100%;height:290px;object-fit:contain;background:#eef1f5;border-radius:6px}small{overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}select,input{padding:10px;background:#e6edf5;color:#0c1422;border-radius:6px;margin:4px}a{color:#90cfff}details{margin-top:14px}h3{font-size:17px}</style><header><h1>TI4 · Símbolos de facção</h1><p>Fase 3.1.5 · Candidatos locais para revisão. Nenhum asset foi aprovado ou integrado.</p>'''
    page+=f'<p><b>30 facções</b> · {stats["strong"]} fortes · {stats["ambiguous"]} ambíguas · {stats["weak"]} fracas · {stats["missing"]} sem resultado · {stats["copiedCandidates"]} candidatos copiados</p>'
    page+='<p>Texturas de fichas podem conter vários desenhos; retratos contêm apenas um emblema pequeno. Os arquivos são cópias integrais, sem recorte. Firmament/Obsidian permanece uma única facção do catálogo.</p><label>Conjunto <select id="set"><option value="">Todas</option><option value="base">Base</option><option value="pok">Prophecy of Kings</option><option value="thunders-edge">Thunder’s Edge / oficial associado</option></select></label><label>Status <select id="status"><option value="">Todos</option><option value="ambiguous">Somente ambíguas</option><option value="weak">Candidatos fracos</option><option value="missing">Sem resultado</option></select></label><input id="search" placeholder="Buscar facção" aria-label="Buscar facção"><p id="count"></p><a href="tts-faction-assets-report.json">Relatório JSON</a></header><main>'+''.join(chunks)+'</main>'
    page+='''<script>const set=document.getElementById('set'),status=document.getElementById('status'),search=document.getElementById('search');function filter(){let n=0;document.querySelectorAll('section').forEach(s=>{s.hidden=!!((set.value&&s.dataset.set!==set.value)||(status.value&&s.dataset.status!==status.value)||!s.querySelector('h2').textContent.toLowerCase().includes(search.value.toLowerCase()));if(!s.hidden)n++});document.getElementById('count').textContent=n+' facções exibidas'}[set,status,search].forEach(x=>x.addEventListener('input',filter));filter();</script></html>'''
    (out/'index.html').write_text(page,encoding='utf-8')

def run(source,mods,cat,out):
    source,mods,cat,out=map(lambda p:Path(p).resolve(),(source,mods,cat,out))
    if out.is_relative_to(mods) or mods.is_relative_to(out): raise ValueError('Output overlaps TTS')
    if out.is_relative_to(cat.parent.parent.parent): raise ValueError('Output overlaps main project')
    out.mkdir(parents=True,exist_ok=True)
    before=snapshot(mods); source_hash=sha(source);cat_hash=sha(cat)
    d=json.loads(source.read_text(encoding='utf-8-sig')); factions=catalog(cat); nodes=list(walk(d))
    objects=[(p,x) for p,x in nodes if isinstance(x,dict) and 'GUID' in x and 'Name' in x]
    strings=[(p,x) for p,x in nodes if isinstance(x,str)]
    refs=[dict(fieldPath=p,url=m.group().rstrip('.,;')) for p,s in strings for m in URL.finditer(s)]
    bykey=collections.defaultdict(list)
    for rel in before:
        f=mods/rel
        if f.parent.name in ('Images','Images Raw','Models','Assetbundles'): bykey[f.stem].append(f)
    def resolve(url): return bykey.get(key(url),[])
    for r in refs: r['cacheMatches']=[str(p) for p in resolve(r['url'])]
    lua_pairs=[]
    pattern=re.compile(r'''id\s*=\s*['"]([^'"]+)['"]\s*,\s*tokenName\s*=\s*(['"])(.*?)\2''')
    for p,s in strings:
        if p.endswith('.LuaScript'):
            for m in pattern.finditer(s): lua_pairs.append((m[1],m[3],p))
    for f in factions:
        aliases={norm(f['name'])}; evidence=[]
        for id,token,p in lua_pairs:
            tn=norm(token)
            match=tn in aliases or (tn=='firmamentobsidian' and 'firmament' in f['slug']) or (tn.startswith('keleres') and 'keleres' in f['slug'])
            if match: aliases.update([norm(id),tn]);evidence.append(dict(alias=id,tokenName=token,source=p))
        if 'firmament' in f['slug']: aliases.update(['firmament','obsidian'])
        if 'keleres' in f['slug']: aliases.add('keleres')
        f['aliases']=sorted(aliases);f['aliasEvidence']=list({json.dumps(x):x for x in evidence}.values());f['candidates']=[];f['unavailable']=[];f['relatedAssets']=[]
    def matching(name):
        n=norm(name)
        return [f for f in factions if any(n==a or n.startswith(a+suffix) for a in f['aliases'] for suffix in ['commandtoken','ownertoken','factiontoken','tile','button','sheet','box','leaders','promissory','tech','alliance','baseinfo','extrainfo'])]
    selected=collections.defaultdict(dict)
    def add(f,url,typ,path,obj,field,reason):
        item=selected[f['slug']].setdefault(url,dict(sourceUrl=url,assetType=typ,confidence='medium' if typ=='Textura de fichas' else 'low',reason=reason,provenance=[]))
        item['provenance'].append(dict(objectPath=path,sourceObject=obj.get('Nickname',obj.get('Name','')),GUID=obj.get('GUID'),assetField=field,objectType=obj.get('Name')))
    for p,o in objects:
        name=o.get('Nickname',''); fs=matching(name)
        if name.endswith(' Faction Token') and 'CardID' in o:
            deck=o.get('CustomDeck',{}).get(str(o['CardID']//100))
            if deck and deck.get('FaceURL') and deck.get('NumWidth') and deck.get('NumHeight'):
                index=o['CardID']%100
                if index < deck['NumWidth']*deck['NumHeight']:
                    for f in fs:
                        u=deck['FaceURL']
                        add(f,u,'Ficha de referência / emblema',p,o,p+'.CustomDeck.'+str(o['CardID']//100)+'.FaceURL','Atlas de fichas: prévia da célula indicada por CardID, com emblema no canto superior direito. Clique abre o atlas integral; nenhum arquivo foi recortado.')
                        selected[f['slug']][u]['atlas']=dict(cardId=o['CardID'],index=index,columns=deck['NumWidth'],rows=deck['NumHeight'],column=index%deck['NumWidth'],row=index//deck['NumWidth'])
        for field,s in local_strings(o,p):
            for m in URL.finditer(s):
                u=m.group().rstrip('.,;')
                for f in fs:
                    f['relatedAssets'].append(dict(objectPath=p,GUID=o['GUID'],name=name,field=field,url=u,cacheMatches=[str(v) for v in resolve(u)]))
                    if field.endswith('.DiffuseURL') and re.search(r'(Command Token|Owner Token)$',name,re.I): add(f,u,'Textura de fichas',p,o,field,'Associação nominal direta; pode ser atlas de fichas com emblema e outros desenhos. Requer validação e possível recorte posterior.')
                    elif field.endswith('.DiffuseURL') and name.endswith(' Tile'): add(f,u,'Textura de tile',p,o,field,'Tile associado à facção; pode conter retrato, texto e emblema, não um símbolo isolado.')
    for p,x in nodes:
        if isinstance(x,dict) and 'Name' in x and ('.CustomUIAssets[' in p or p.endswith('.CustomDecal')):
            name=x['Name'];u=x.get('URL',x.get('ImageURL',''))
            if u and (name.endswith('Button') or p.endswith('.CustomDecal')):
                for f in matching(name): add(f,u,'Retrato / botão de facção',p,x,p+('.URL' if 'URL' in x else '.ImageURL'),'Painel ilustrado associado à facção; contém emblema pequeno. Não equivale a ícone isolado.')
    used_hashes={};errors=[]
    for f in factions:
        for c in sorted(selected[f['slug']].values(),key=lambda c:(c['assetType']!='Textura de fichas',c['sourceUrl'])):
            matches=resolve(c['sourceUrl']); usable=[]
            for p in matches:
                if p.parent.name!='Images':continue
                try:
                    with Image.open(p) as im: dims=list(im.size);fmt=im.format;im.verify()
                    usable.append((p,dims,fmt))
                except Exception as ex: errors.append(dict(file=str(p),error=str(ex)))
            if not usable:
                f['unavailable'].append(dict(**c,cacheMatches=[str(p) for p in matches]));continue
            for p,dims,fmt in usable:
                num=len(f['candidates'])+1
                rel=f'candidates/official-reference-atlas-{sha(p)[:12]}{p.suffix.lower()}' if c.get('atlas') else f'candidates/{f["slug"]}__candidate-{num:02d}-{hashlib.sha256(c["sourceUrl"].encode()).hexdigest()[:8]}{p.suffix.lower()}'
                digest=safe_copy(p,out/rel,out);used_hashes[str(p)]=digest
                f['candidates'].append(dict(**c,cachedFile=str(p),copiedFile=str(out/rel),relativeFile=rel,sha256=digest,dimensions=dims,imageFormat=fmt,cacheMethod='Exact case-sensitive stem = URL with non-ASCII-alphanumeric characters removed; cache extension preserved',humanApproval='pending'))
        n=len(f['candidates']);f['status']='ambiguous' if n>1 else 'weak' if n else 'missing'
    after=snapshot(mods);changed=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
    integrity=dict(metadataEntries=len(before),metadataChanges=changed,sourceJsonUnchanged=sha(source)==source_hash,catalogUnchanged=sha(cat)==cat_hash,copiedSourcesSha256Unchanged=all(sha(p)==h for p,h in used_hashes.items()),scope='All Mods file size + mtime before/after; SHA256 of JSON, catalog, and every copied source. Not a bytewise audit of unused cache.')
    counts=collections.Counter(f['status'] for f in factions)
    stats=dict(factions=30,**{s:counts[s] for s in ['strong','ambiguous','weak','missing']},copiedCandidates=sum(len(f['candidates']) for f in factions),uniqueCopiedSources=len(used_hashes),topLevelObjects=len(d['ObjectStates']),objects=len(objects),statesObjects=sum('.States.' in p for p,o in objects),urlOccurrences=len(refs),uniqueUrls=len({r['url'] for r in refs}),uniqueUrlsMatched=len({r['url'] for r in refs if r['cacheMatches']}))
    stats['childObjects']=sum('.ChildObjects[' in p for p,o in objects)
    stats['containedObjectsTraversal']=sum('.States.' not in p and '.ChildObjects[' not in p for p,o in objects)
    stats['copiedFiles']=len({c['copiedFile'] for f in factions for c in f['candidates']})
    normalized_urls=collections.defaultdict(set)
    for ref in refs: normalized_urls[key(ref['url'])].add(ref['url'])
    stats['urlNormalizationCollisions']=sum(len(values)>1 for values in normalized_urls.values())
    report=dict(schemaVersion=1,generatedAt=datetime.now(timezone.utc).isoformat(),phase='3.1.5',sourceJson=str(source),saveName=d['SaveName'],sourceSha256=source_hash,catalogSource=str(cat),catalogSha256=cat_hash,statistics=stats,cacheMethod='Empirically tested exact stem match after stripping all characters except ASCII A-Z a-z 0-9. No prefix/substring guessing or remote downloads. Raw .rawt files indexed but not treated as browser images.',limitations=['No isolated emblem automatically certified. Candidates are complete original images, without crops.','Lua and embedded strings inspected as text; never executed. Unrelated global Lua URLs are inventoried but not assigned to all factions.','Firmament and Obsidian variants share one catalog entry; Keleres variants retained.'],integrity=integrity,imageErrors=errors,factions=factions)
    (out/'tts-faction-assets-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'url-cache-inventory.json').write_text(json.dumps(refs,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'source-metadata-before.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
    generate_gallery(report,out)
    print(json.dumps(stats));print(json.dumps(integrity))
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',default=r'C:\Users\Hugo\Documents\My Games\Tabletop Simulator\Mods\Workshop\1288687076.json');p.add_argument('--mods',default=r'C:\Users\Hugo\Documents\My Games\Tabletop Simulator\Mods');p.add_argument('--catalog',default=r'C:\Projetos\ti4-draft\supabase\migrations\20260930150000_content_catalog_and_draft_configuration.sql');p.add_argument('--output',default=str(Path(__file__).resolve().parent.parent));a=p.parse_args();run(a.source,a.mods,a.catalog,a.output)
