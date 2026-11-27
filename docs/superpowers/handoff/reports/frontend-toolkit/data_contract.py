"""Compare original chart payloads and CSV values at two reader revisions."""
import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen

ROUTES = (
    '/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT',
    '/comparar/taxas-juro-credito-depositos',
    '/comparar/paises/eletricidade-domestica',
    '/series/ine.hicp_yoy.PT',
    '/calculadas/derived.unemployment_monthly.PT.yoy_change',
)
CSV = ('/series/ine.hicp_yoy.PT.csv', '/calculadas/derived.unemployment_monthly.PT.yoy_change.csv')

class Payloads(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.payloads = []
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag == 'script':
            self.active = 'chart-data' in attrs.get('class','').split()
    def handle_endtag(self,tag):
        if tag == 'script':
            self.active=False
    def handle_data(self,data):
        if self.active:
            self.payloads.append(json.loads(data))


def body(base,route):
    with urlopen(base.rstrip('/')+route,timeout=60) as response:
        assert response.status == 200
        return response.read()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--before',required=True)
    parser.add_argument('--after',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    checks=[]
    for route in ROUTES:
        a,b=Payloads(),Payloads()
        a.feed(body(args.before,route).decode())
        b.feed(body(args.after,route).decode())
        assert a.payloads and a.payloads == b.payloads,route
        checks.append({'route':route,'payload_equal':True,'sha256':hashlib.sha256(json.dumps(a.payloads,sort_keys=True).encode()).hexdigest()})
    for route in CSV:
        a,b=body(args.before,route),body(args.after,route)
        # Only the independently identified export-clock record may vary.
        clean=lambda raw: re.sub(rb'(?m)^.*Exportado a[^\r\n]*',b'Export clock',raw)
        assert clean(a) == clean(b),route
        checks.append({'route':route,'values_equal':True,'raw_hashes':[hashlib.sha256(x).hexdigest() for x in (a,b)]})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'completed':True,'passed':True,'checks':checks},indent=2))
    print(json.dumps({'completed':True,'checks':len(checks)}))


if __name__ == '__main__':
    main()
