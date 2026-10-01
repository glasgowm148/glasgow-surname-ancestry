"""Lossless compact payloads for large public site models."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def pack_model(model):
    strings, schemas, string_ids, schema_ids = [], [], {}, {}
    def enc(x):
        if isinstance(x,str):
            if x not in string_ids: string_ids[x]=len(strings); strings.append(x)
            return -string_ids[x]-1
        if isinstance(x,list): return ['l',[enc(v) for v in x]]
        if isinstance(x,dict):
            keys=tuple(x)
            if keys not in schema_ids: schema_ids[keys]=len(schemas);schemas.append(list(keys))
            return ['o',schema_ids[keys],[enc(v) for v in x.values()]]
        if isinstance(x,(int,float)) and x<0: return ['n',x]
        return x
    value=enc(model)
    return {'format':2,'strings':strings,'schemas':schemas,'value':value}


def unpack_model(packed):
    def dec(x):
        if isinstance(x,(int,float)) and x<0:return packed['strings'][-x-1]
        if isinstance(x,list):
            if x[0]=='l': return [dec(v) for v in x[1]]
            if x[0]=='o':return dict(zip(packed['schemas'][x[1]],(dec(v) for v in x[2])))
            if x[0]=='n':return x[1]
        return x
    return dec(packed['value'])

def build(site_root):
    root = Path(site_root)
    source = root / "assets/research/atlas-model.json"
    target = root / "assets/research/atlas-model-packed.json"
    target.write_text(json.dumps(pack_model(json.loads(source.read_text(encoding="utf-8"))), ensure_ascii=False,separators=(",", ":")), encoding="utf-8")
    boot = Path(__file__).with_name("atlas_boot.js").read_text(encoding="utf-8")
    (root / "assets/research/atlas-boot.js").write_text(boot, encoding="utf-8")
    return target

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("site_root", type=Path)
    build(parser.parse_args().site_root)
