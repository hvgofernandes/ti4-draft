"""Verify the relocated delivery only. Never reads or modifies the TTS cache."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.request import urlopen
from urllib.parse import urljoin,urlsplit
import hashlib,json,re,concurrent.futures
ROOT=Path(__file__).resolve().parent.parent
BASE='http://127.0.0.1:5173/docs/tts-assets-review/'
class Page(HTMLParser):
 def __init__(self): super().__init__(); self.images=[];self.refs=[];self.sections=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='section':self.sections+=1
  if tag=='img':self.images.append(a['src'])
  for k in ['src','href']:
   if k in a:self.refs.append(a[k])
  for u in re.findall(r'url\(([^)]+)\)',a.get('style','')):self.refs.append(u.strip('\"\''))
def sha(b):return hashlib.sha256(b).hexdigest()
def verify():
 report=json.loads((ROOT/'tts-faction-assets-report.json').read_text(encoding='utf-8'))
 html=(ROOT/'index.html').read_text(encoding='utf-8');p=Page();p.feed(html)
 assert p.sections==30 and len(p.images)==121
 assert 'referenced-chatgpt-conversation' not in html
 assert 'Tabletop Simulator' not in html and 'file://' not in html
 expected={}
 for f in report['factions']:
  for c in f['candidates']:
   rel=c['relativeFile'];path=(ROOT/rel).resolve()
   assert path.is_relative_to(ROOT) and path.is_file()
   assert sha(path.read_bytes())==c['sha256']
   assert Path(c['copiedFile'])==path
   expected[rel]=c['sha256']
 for ref in p.refs:
  assert not urlsplit(ref).scheme and not ref.startswith('/')
  assert (ROOT/ref).resolve().is_relative_to(ROOT) and (ROOT/ref).is_file()
 def check(item):
  rel,digest=item
  with urlopen(urljoin(BASE,rel),timeout=30) as response:
   assert response.status==200 and response.headers.get_content_type().startswith('image/')
   assert sha(response.read())==digest
  return rel
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex: checked=list(ex.map(check,expected.items()))
 with urlopen(BASE,timeout=30) as response:
  served=response.read().decode('utf-8');assert response.status==200
  assert 'TI4 · Símbolos de facção' in served and '/@vite/client' in served
  assert '<style>' in served and 'function filter()' in served
 result={'url':BASE,'entry':str(ROOT/'index.html'),'status':'passed','sections':p.sections,'imageElements':len(p.images),'uniqueImageFiles':len(expected),'httpImagesVerified':len(checked),'hashesVerified':True,'allGalleryDependenciesInsideDelivery':True,'ttsCacheAccessed':False,'investigationRerun':False,'browserTests':'Recorded separately in delivery-test.md'}
 (ROOT/'delivery-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':verify()
