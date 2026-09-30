"""Regression and artifact verification; fixtures only write into temporary directories."""
import copy
import json
import tempfile
import unittest
import contextlib
import io
from pathlib import Path
from html.parser import HTMLParser
import scan_tts as scan

OUT = Path(__file__).resolve().parent.parent
CAT = Path(r'C:\Projetos\ti4-draft\supabase\migrations\20260930150000_content_catalog_and_draft_configuration.sql')

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.images=[]; self.sections=0
    def handle_starttag(self, tag, attrs):
        if tag=='section': self.sections+=1
        if tag=='img': self.images.append(dict(attrs)['src'])

class ScannerTests(unittest.TestCase):
    def test_json_full_recursive_traversal(self):
        data=json.loads('{"ObjectStates":[{"GUID":"a","ContainedObjects":[{"GUID":"b","States":{"2":{"GUID":"c","Custom":{"list":["https://example.test/a.png"]}}}}]}]}')
        nodes=dict(scan.walk(data))
        self.assertEqual(nodes['$.ObjectStates[0].ContainedObjects[0].States.2.GUID'],'c')
        self.assertEqual(nodes['$.ObjectStates[0].ContainedObjects[0].States.2.Custom.list[0]'],'https://example.test/a.png')

    def test_object_local_strings_exclude_descendants(self):
        obj={'Nickname':'Parent','Custom':{'URL':'https://host/a'},'ContainedObjects':[{'Nickname':'Child'}],'States':{'2':{'Nickname':'State'}}}
        self.assertEqual(dict(scan.local_strings(obj,'$')),{'$.Nickname':'Parent','$.Custom.URL':'https://host/a'})

    def test_url_extraction_and_case_sensitive_cache_key(self):
        urls=[m.group().rstrip('.,;') for m in scan.URL.finditer('url="https://Host.test/A.png?x=2&y=3" Lua = \'http://host/b.jpg\'')]
        self.assertEqual(urls,['https://Host.test/A.png?x=2&y=3','http://host/b.jpg'])
        self.assertEqual(scan.key(urls[0]),'httpsHosttestApngx2y3')
        self.assertNotEqual(scan.key(urls[0]),scan.key(urls[0].lower()))
        self.assertEqual(scan.key('https://a/ç-_.png'),'httpsapng')

    def test_safe_copy_spaces_idempotence_and_guards(self):
        with tempfile.TemporaryDirectory(prefix='tts tests ') as t:
            root=Path(t); src=root/'source file.png'; src.write_bytes(b'original')
            destroot=root/'candidate area'; dst=destroot/'nested folder'/'file with spaces.png'
            digest=scan.safe_copy(src,dst,destroot)
            self.assertEqual(digest,scan.sha(src)); self.assertEqual(dst.read_bytes(),b'original')
            self.assertEqual(scan.safe_copy(src,dst,destroot),digest)
            dst.write_bytes(b'other')
            with self.assertRaises(ValueError): scan.safe_copy(src,dst,destroot)
            with self.assertRaises(ValueError): scan.safe_copy(src,destroot/'..'/'escape.png',destroot)
            with self.assertRaises(ValueError): scan.safe_copy(src,src,root)
            self.assertFalse((root/'escape.png').exists()); self.assertEqual(src.read_bytes(),b'original')

    def test_authoritative_catalog(self):
        factions=scan.catalog(CAT)
        self.assertEqual(len(factions),30)
        self.assertEqual(len({f['slug'] for f in factions}),30)
        self.assertNotIn('discordant-stars',{f['contentSet'] for f in factions})
        self.assertEqual(sum('firmament' in f['slug'] for f in factions),1)

    def test_gallery_empty_multiple_and_escaping(self):
        base={'name':'A <script> & "B"','contentSet':'base','status':'missing','candidates':[]}
        c={'relativeFile':'candidates/file with space & quote".png','assetType':'<img>','confidence':'low','dimensions':[32,64],'reason':'<script>alert(1)</script>'}
        multi=copy.deepcopy(base);multi['status']='ambiguous';multi['candidates']=[c,dict(c,relativeFile='candidates/second.png')]
        report={'statistics':{'strong':0,'ambiguous':1,'weak':0,'missing':1,'copiedCandidates':2},'factions':[base,multi]}
        with tempfile.TemporaryDirectory() as t:
            scan.generate_gallery(report,Path(t)); page=(Path(t)/'index.html').read_text(encoding='utf-8')
        p=Parser();p.feed(page)
        self.assertEqual(p.sections,2);self.assertEqual(p.images,[c['relativeFile'],'candidates/second.png'])
        self.assertIn('Nenhum arquivo candidato',page);self.assertIn('&lt;script&gt;',page)
        self.assertNotIn('<script>alert(1)</script>',page)

    def test_report_and_copy_integrity(self):
        report=json.loads((OUT/'tts-faction-assets-report.json').read_text(encoding='utf-8'))
        self.assertEqual({f['slug'] for f in report['factions']},{f['slug'] for f in scan.catalog(CAT)})
        self.assertEqual(report['phase'],'3.1.5')
        self.assertEqual(report['integrity']['metadataChanges'],[])
        for k in ['sourceJsonUnchanged','catalogUnchanged','copiedSourcesSha256Unchanged']:self.assertTrue(report['integrity'][k])
        n=0
        for f in report['factions']:
            for c in f['candidates']:
                n+=1; dst=(OUT/c['relativeFile']).resolve()
                self.assertTrue(dst.is_relative_to(OUT.resolve()))
                self.assertEqual(scan.sha(dst),c['sha256']) # Local delivery hash; cache provenance is not a file dependency.
                self.assertEqual(Path(c['cachedFile']).stem,scan.key(c['sourceUrl']))
                self.assertTrue(c['provenance']);self.assertEqual(c['humanApproval'],'pending')
        self.assertEqual(n,report['statistics']['copiedCandidates'])
        p=Parser();p.feed((OUT/'index.html').read_text(encoding='utf-8'))
        self.assertEqual(p.sections,30);self.assertEqual(len(p.images),n)
        for src in p.images:self.assertTrue((OUT/src).is_file())

    def test_end_to_end_missing_and_exact_cache(self):
        factions=scan.catalog(CAT)
        with tempfile.TemporaryDirectory(prefix='tts end to end ') as t:
            root=Path(t); mods=root/'Mods'; images=mods/'Images';images.mkdir(parents=True)
            source=mods/'Workshop'/'fixture.json';source.parent.mkdir()
            output=root/'review output with spaces'
            urls=[f'https://fixture.test/faction{i}.png' for i in range(30)]
            scan.Image.new('RGBA',(16,16),(255,0,0,255)).save(images/(scan.key(urls[0])+'.png'))
            # A longer stem is deliberately not an exact match for faction 1.
            scan.Image.new('RGB',(16,16)).save(images/(scan.key(urls[1])+'extra.png'))
            data={'SaveName':'Regression fixture','ObjectStates':[],
                  'LuaScript':'\n'.join('id = "testalias'+str(i)+'", tokenName = "'+f['name']+'"' for i,f in enumerate(factions)),
                  'CustomUIAssets':[{'Name':f'testalias{i}Button','URL':u} for i,u in enumerate(urls)]}
            source.write_text(json.dumps(data),encoding='utf-8')
            before=scan.snapshot(mods)
            with contextlib.redirect_stdout(io.StringIO()): report=scan.run(source,mods,CAT,output)
            self.assertEqual(report['statistics']['copiedCandidates'],1)
            self.assertEqual(report['statistics']['missing'],29)
            self.assertEqual(report['statistics']['weak'],1)
            self.assertEqual(report['statistics']['uniqueUrlsMatched'],1)
            self.assertEqual(len(report['factions'][0]['candidates']),1)
            for f in report['factions'][1:]:
                self.assertEqual(f['status'],'missing');self.assertEqual(len(f['unavailable']),1)
                self.assertEqual(f['unavailable'][0]['cacheMatches'],[])
            self.assertEqual(before,scan.snapshot(mods))
            p=Parser();p.feed((output/'index.html').read_text(encoding='utf-8'))
            self.assertEqual(p.sections,30);self.assertEqual(len(p.images),1)

    def test_real_atlas_card_mapping(self):
        report=json.loads((OUT/'tts-faction-assets-report.json').read_text(encoding='utf-8'))
        source=Path(report['sourceJson'])
        if not source.is_absolute():
            self.skipTest('Historical source check requires original TTS JSON; delivery intentionally has no cache dependency.')
        nodes=dict(scan.walk(json.loads(source.read_text(encoding='utf-8-sig'))))
        indices=[]
        for f in report['factions']:
            cards=[c for c in f['candidates'] if c.get('atlas')]
            self.assertEqual(len(cards),1,f['name'])
            c=cards[0];a=c['atlas'];indices.append(a['index'])
            self.assertEqual(a['index'],a['cardId']%100)
            self.assertEqual(a['column'],a['index']%a['columns'])
            self.assertEqual(a['row'],a['index']//a['columns'])
            self.assertLess(a['row'],a['rows'])
            for provenance in c['provenance']:
                obj=nodes[provenance['objectPath']]
                self.assertEqual(obj['CardID'],a['cardId'])
                deck=obj['CustomDeck'][str(obj['CardID']//100)]
                self.assertEqual(deck['FaceURL'],c['sourceUrl'])
                self.assertEqual((deck['NumWidth'],deck['NumHeight']),(a['columns'],a['rows']))
        self.assertEqual(len(indices),30);self.assertEqual(len(set(indices)),30)

if __name__=='__main__':unittest.main(verbosity=2)
