# 中文审阅指南

本次交付是供制作 Word 的完整英文说明书底稿和事实包，不是新版 PPT，
也未代替 Claude 生成最终 DOCX/PDF。原 PDF、原字典和原文件均保留。

## 本次针对性修订

沿用原 13 October 元数据和查询快照，没有重新扫描数据库。
全部字段按每表 A（类型、nullable、默认值）、B（定义、用途、具体示例）、
C（来源、具体规则、分项证据/确认状态）组织，不再机械复制 520 张字段卡片。
通用空值、约束执行和示意例子规则集中在字典开头。

`Field_Evidence_Index.md` 的 F001–F520 引用与 JSON/CSV 对应，分别支持元数据、
映射、实际赋值/绑定代码、已有查询统计和特定业务确认。统计结果不确认单位；
writer 支持绑定不证明某条历史记录的来源。字段的来源、单位、代码和业务含义
分别判断，不把所有未知事项套在一起。

已补查无 v3 映射字段的表单、导入/纠正 writer 和生成器；无法找到真实写入入口
的字段列在 `metadata/source_explanation_gaps.csv`。特别区分尺寸子表的本地
生成器与 Snowflake 写入功能、RAW 的预留匹配字段，以及应用登录时间字段。

`No default declared` 表示没有声明默认值，不等于 DEFAULT NULL。
Source Total 明确区分 `new_marketings.csv.efc_total` 与工作簿标题 `Total`。
可空 FK 不保证查询保留行，只有实际 JOIN/筛选支持时才这样描述。
五位周编码按真实 parser 写明：世纪位 1 为 1900s、2 为 2000s；不是 1900+CYY。

39 张 FK 单关系详图仍完整保留为配套材料；Word 应按解释需要选用，
无需每条关系机械占一页，但完整关系说明不能遗漏。

## 先读哪些文件

1. `EFNS_Database_Design_Manual.md`：可独立阅读的完整英文底稿；第 8 章已包含全部字段，不只链接 Excel。
2. `Complete_Data_Dictionary.html`：浏览器中便于搜索、阅读字段的版本。
3. `metadata/structure_metadata.json`、`enhanced_dictionary.csv`：实际结构和增强定义的统一事实来源。
4. `erd/`：SVG 和 DOT 可编辑图源、PNG，以及完整字段分片和 39 张关系详图。
5. `Coverage_Check.json`、`evidence/query_receipts.csv`：覆盖检查及真实只读查询回执。
6. `Claude_Word_Production_Prompt.md`：交给 Claude 制作可编辑 Word 和 PDF 的规格。

## 逐章审阅重点

| 章节 | 已补充内容 | 请检查的重点 |
| --- | --- | --- |
| 1 | 文档用途、范围、证据层次 | 当前 DEV 元数据、本地代码、上次部署快照不能混写。 |
| 2 | 真实 Work Plan 范围与查询需求 | Work Plan 不是所有余额公式或单位的批准。 |
| 3 | 27 表分类和完整目录 | 15 个 CORE 业务/参考表，另有 10 RAW、1 APP、1 SECURITY；4 视图不算表。 |
| 4 | Spreadsheet Import / Migration 分路径 | 完整 14 文件迁移、普通 Flock/Quota、固定工作表 Production、独立纠正分别解释。 |
| 5 | Manual Data Entry | 表单不普遍经过 MIGRATION_RAW_ROW；坐标 NULL 与 0 分开。 |
| 6 | 键、可空关系、Snowflake 职责 | 复合 FK 是一条关系；标准表声明不等于数据库强制保证。 |
| 7 | 全部 27 表说明 | 每表的用途、粒度、拆分解释、父子引用、输入、查询、例子及限制。 |
| 8 | 440 表字段和 80 视图字段 | 技术事实可核实；未知单位/代码不能靠字段名补造。 |
| 9 | 7 个完整查询用例和 Production 关联分析 | Source Total 只能用 TOTAL；空值不补零；多子表连接不要放大数量。 |
| 10 | 对账、历史例外、权限和未决事项 | 112 已纠正与 159 待确认区分；675 是额外来源追踪，不是新日期目标。 |
| 11 | 维护、术语、证据索引 | GET_DDL 仅供参考，不可当成此次部署脚本执行。 |

## 本次独立核实结果

13 October 2026 的 DEV 只读核对与原基线一致：27 表、4 视图，440+80=520 个
字段条目；27 PK、39 FK、6 UNIQUE、138 个 NOT NULL 表字段，以及 DDL 中一个
CHECK。PK/FK/UNIQUE 扫描无重复键组、无孤儿引用。这是本次扫描结果，
不表示并发唯一性风险已经彻底解决，也不是定时监控。

原批次为 COMMITTED；纠正批次为 COMMITTED_WITH_PENDING。
当前纠正预览为 112 ALREADY_COMMITTED、0 READY_CORE、159 PENDING。
对账仍为 85,962+112+675+159=86,908；可归属于这次迁移的 CORE 目标为 86,074。

生产全库 45,182 条，Facility/Flock 各 5,100 个非空引用都能匹配父记录；
原 Jensen 40,025 条生产记录这两类引用均为空。不能用全库非空数量证明
Jensen 已提供这些关系。原批次 Producer 有 40,025 个匹配、Grader 有 39,891 个匹配。
其他来源的身份和历史写入证据另列，不能只看 EIMS_IMPORT 标签就说是真实 Jensen 数据。

使用保存的已部署源码快照、本次 DEV 数据及实际应用角色重新自动核对：
1999/21 为 24 个全空值组；2017/15 为 23 组，总和 390,288；CSV/XLSX 与结果一致。
这不是本次真实浏览器验收。用户此前确认的 nullable 1999 分组/CSV 手工通过
保留；全空分组 XLSX、Facility/Flock 筛选及关联场景未新增“手工通过”标记。

## 发现的说明差异

- v1.4 的输入箭头过于笼统：普通 Flock/Quota 导入也使用 IMPORT_BATCH/IMPORT_RAW_ROW；人工表单不普遍走 RAW。
- Production Import 页面目前是 EIMS 3 的 XLSX/XLSM，不是任意 CSV。它会过滤无 Producer # 的工作表行，RAW 并非整个原文件逐字节备份。
- RAW 的历史表头已大写规范化，日期等经过 JSON 序列化；文件字节与 parsed row 要分开说明。
- 原始生产没有 Facility/Flock 引用，但全库其他数据存在有效引用；两种情况都要准确解释。
- 未找到对应 v1.4 PPTX；已完整读取 26 页 PDF，不影响重写说明书。
- 本轮未重新下载线上应用包；代码执行依据是 12 October 保存并核验过的已部署快照，和当前本地代码另做 hash 对比。

## 少量需要确认的问题

请 Sara/Jensen 提供六个 Flock 的跨 Account 原因及有效证据，以及缺失 Flock/Quota
父 GUID；六条和 57 条依赖仍未放行。不要根据“疑似寄养”自行替换引用。

请 Wanda/Sara 确认 TOTAL、quota、住房量值的单位与状态/交易含义，当前存栏和
可用 quota 计算规则，以及 production 的日期/周如何对应 EFC period。
已经确认的 Facility 可先后/同时容纳多群，不再重复提问，也不新增上限。

请 Dr. Lu 重点评审实体与活动拆分、可空角色、复合来源身份、信息性约束与
应用职责，以及查询粒度是否适合需求。未知业务事项可以集中作为评审问题，
不要求先把所有事项关项才能提交文档。

本轮没有改业务代码、DDL、数据库记录、视图、权限或应用部署，也未提交 Git。
