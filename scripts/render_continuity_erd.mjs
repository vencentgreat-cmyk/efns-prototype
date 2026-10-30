import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire('C:/Users/Egg Farmers/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/package.json');
const {instance}=require('@viz-js/viz');
const sharp=require('sharp');
const out=path.resolve('docs/identity_history_2026-10-14');
const spec=JSON.parse(fs.readFileSync(path.join(out,'Actual_ERD_Spec.json'),'utf8'));
const owned=['RAW.SOURCE_FILE','RAW.INTAKE_LOCK','RAW.PRODUCTION_MATCH_DECISION','CORE.FLOCK_EVENT','APP.RECORD_REVISION'];
const fks=spec.foreign_keys.filter(r=>owned.includes(r.fk_schema_name+'.'+r.fk_table_name));
const included=[...new Set([...owned,...fks.map(r=>r.pk_schema_name+'.'+r.pk_table_name)])];
const key=(s)=>s.replaceAll('.','_');
const esc=(s)=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
let dot='digraph G { graph [rankdir=TB,bgcolor="white",pad=0.3,nodesep=0.6,ranksep=0.9,splines=polyline,label="EFNS evidence and business history\nActual declared relationships, 14 October 2026\nDashed: non-identifying; grey: repeated parent; polymorphic references have no invented edge",labelloc=t,fontname="Arial",fontsize=16];node [shape=plain,fontname="Arial",fontsize=14];edge [fontname="Arial",fontsize=11];';
for(const full of included){
 const [schema,table]=full.split('.');
 const repeat=!owned.includes(full);
 const pks=spec.primary_keys.filter(r=>r.schema_name===schema&&r.table_name===table).map(r=>r.column_name);
 const fields=spec.columns.filter(r=>r.TABLE_SCHEMA===schema&&r.TABLE_NAME===table&&(!repeat||pks.includes(r.COLUMN_NAME)));
 dot+=`${key(full)} [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="7" BGCOLOR="${repeat?'#eeeeee':'white'}"><TR><TD ALIGN="LEFT" BGCOLOR="${repeat?'#dfe2e4':'#dfeef0'}"><B>${full}${repeat?' [repeated]':''}</B></TD></TR>${fields.map((r,i)=>`<TR><TD PORT="p${i}" ALIGN="LEFT">${esc(r.COLUMN_NAME)}${pks.includes(r.COLUMN_NAME)?' [PK]':''}${fks.some(f=>f.fk_schema_name===schema&&f.fk_table_name===table&&f.fk_column_name===r.COLUMN_NAME)?' [FK]':''}${r.IS_NULLABLE==='YES'?' (optional)':''}</TD></TR>`).join('')}</TABLE>>];`;
}
const groups=new Map();
for(const f of fks){const name=f.fk_schema_name+'.'+f.fk_table_name+'.'+f.fk_name;groups.set(name,[...(groups.get(name)||[]),f]);}
for(const members of groups.values()){
 const f=members[0],parent=f.pk_schema_name+'.'+f.pk_table_name,child=f.fk_schema_name+'.'+f.fk_table_name;
 const optional=members.some(m=>spec.columns.find(c=>c.TABLE_SCHEMA===m.fk_schema_name&&c.TABLE_NAME===m.fk_table_name&&c.COLUMN_NAME===m.fk_column_name).IS_NULLABLE==='YES');
 dot+=`${key(parent)} -> ${key(child)} [dir=both,arrowtail="${optional?'odottee':'teetee'}",arrowhead="crowodot",style=dashed,color="#46545a",label="${esc(members.map(m=>m.fk_column_name).join(' + '))}"];`;
}
dot+='}';
const viz=await instance();
const svg=viz.renderString(dot,{format:'svg',engine:'dot'});
fs.writeFileSync(path.join(out,'Evidence_and_History_ERD.dot'),dot);
fs.writeFileSync(path.join(out,'Evidence_and_History_ERD.svg'),svg);
await sharp(Buffer.from(svg),{density:130}).png().toFile(path.join(out,'Evidence_and_History_ERD.png'));
console.log(JSON.stringify({tables:included.length,declared_relationships:groups.size}));
