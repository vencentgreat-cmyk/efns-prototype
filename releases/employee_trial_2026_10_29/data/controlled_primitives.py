"""Dependency-free supplement encoding/binding primitives (no repository bootstrap)."""
import hashlib
from data.source_evidence import evidence_json

def digest(value):return hashlib.sha256(evidence_json(value).encode()).hexdigest()
def bytehash(value):return hashlib.sha256(bytes(value)).hexdigest()
def unique(rows,key):
    from data.repositories.base import RepositoryError
    result={key(r):r for r in rows}
    if len(result)!=len(rows):raise RepositoryError('Duplicate source or target identity; no count-only verification.')
    return result
def batches(rows,max_rows=500,max_bytes=1024*1024):
    from data.repositories.base import RepositoryError
    out=[];current=[];size=2
    for r in rows:
        length=len(evidence_json(r).encode())
        if length+2>max_bytes:raise RepositoryError('A single evidence row exceeds the safe bind size.')
        if current and (len(current)==max_rows or size+length+2>max_bytes):out.append(current);current=[];size=2
        size+=length+(2 if current else 0);current.append(r)
    if current:out.append(current)
    return out
