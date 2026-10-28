"""Index explicit local SQL declarations; never connects or executes SQL."""
from pathlib import Path
import csv,re

ROOT=Path(__file__).resolve().parents[1]
PATTERNS={
    'CREATE_TABLE':r'\bCREATE\s+(?:OR\s+REPLACE\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.]+)',
    'CREATE_VIEW':r'\bCREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([\w.]+)',
    'ADD_COLUMN':r'\bALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?([\w.]+)\s+ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)',
}

def main():
    rows=[]
    for p in sorted((ROOT/'sql').glob('*.sql')):
        text=p.read_text(encoding='utf-8-sig')
        # This indexes script text, including dynamic statement strings. It is
        # deliberately not an effective-DDL parser or a live object inventory.
        for kind,pattern in PATTERNS.items():
            for hit in re.finditer(pattern,text,re.I):
                rows.append(dict(source_file='sql/'+p.name,line=text[:hit.start()].count('\n')+1,declaration=kind,object=hit[1].upper(),column=hit[2].upper() if kind=='ADD_COLUMN' else ''))
    rows.sort(key=lambda r:(r['source_file'],r['line'],r['object']))
    with (ROOT/'review/SQL_OBJECT_INDEX.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['source_file','line','declaration','object','column'])
        writer.writeheader();writer.writerows(rows)
    print(f'Indexed {len(rows)} source declarations; no database objects inspected or changed.')

if __name__=='__main__':main()
