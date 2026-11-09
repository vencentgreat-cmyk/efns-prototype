import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const out=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(out,'Latest_Data_Dictionary.json'),'utf8'));
const counts=JSON.parse(await fs.readFile(path.join(out,'Coverage_and_Preservation.json'),'utf8'));
const wb=Workbook.create();
const overview=wb.worksheets.add('Overview');
overview.showGridLines=false;
overview.getRange('A2:B9').values=[['EFNS current data dictionary',null],['Snapshot',counts.captured_at],['Tables',counts.tables],['Table fields',counts.table_columns],['Views',counts.views],['View outputs',counts.view_columns],['All entries',data.length],['Declared FK relationships',counts.foreign_key_relationships]];
overview.getRange('A2:B9').format.font={name:'Arial',size:11};
overview.getRange('A2').format.font={name:'Arial',size:16,bold:true};
overview.getRange('A:A').format.columnWidth=34;
overview.getRange('B:B').format.columnWidth=42;
overview.getRange('A11:B14').values=[['Reading rule','Meaning'],['NULL','Unknown is not zero'],['No default declared','Not the same as an explicit SQL NULL default'],['Evidence','Metadata and code facts do not approve business units or formulas']];
overview.getRange('A11:B14').format.wrapText=true;overview.getRange('A11:B14').format.rowHeight=38;
const technical=['Schema','Table','Column','Object kind','SQL type','Nullable','Default','Declared keys','Non-null count','Zero count','Object rows'];
const descriptions=['Schema','Table','Column','Definition','Source and transformation','Units and codes','Historical exception','Code evidence','Metadata evidence'];
function sheet(name,columns,widths){
 const s=wb.worksheets.add(name);s.showGridLines=false;
 const values=[columns,...data.map(r=>columns.map(c=>r[c]??null))];
 s.getRangeByIndexes(0,0,values.length,columns.length).values=values;
 const used=s.getRangeByIndexes(0,0,values.length,columns.length);
 used.format.font={name:'Arial',size:11};used.format.verticalAlignment='top';used.format.wrapText=true;
 used.format.rowHeight=name==='Technical metadata'?60:150;
 for(let i=0;i<columns.length;i++)s.getRangeByIndexes(0,i,values.length,1).format.columnWidth=widths[i];
 const head=s.getRangeByIndexes(0,0,1,columns.length);head.format.fill='#374c53';head.format.font={name:'Arial',size:11,bold:true,color:'#ffffff'};head.format.rowHeight=32;
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(3);
 const table=s.tables.add(s.getRangeByIndexes(0,0,values.length,columns.length),true,name==='Technical metadata'?'TechnicalDictionary':'DefinitionDictionary');
 table.style='TableStyleLight1';
 used.format.autofitRows();head.format.rowHeight=32;
 return s;
}
sheet('Technical metadata',technical,[14,31,36,14,24,12,38,65,16,16,16]);
sheet('Definitions',descriptions,[14,31,36,75,85,80,70,80,70]);
wb.recalculate();
for(const name of ['Overview','Technical metadata','Definitions']){
 const last=name==='Overview'?'A1:B14':name==='Technical metadata'?'A1:H4':'A1:E4';
 const preview=await wb.render({sheetName:name,range:last,scale:1,format:'png'});
 await fs.writeFile(path.join(out,name.replaceAll(' ','_')+'_preview.png'),new Uint8Array(await preview.arrayBuffer()));
}
console.log((await wb.inspect({kind:'table',range:'Technical metadata!A1:F3',tableMaxRows:3,tableMaxCols:6,maxChars:1500})).ndjson);
const file=await SpreadsheetFile.exportXlsx(wb);await file.save(path.join(out,'Latest_Data_Dictionary.xlsx'));
console.log(JSON.stringify({entries:data.length,sheets:3,output:'Latest_Data_Dictionary.xlsx'}));
