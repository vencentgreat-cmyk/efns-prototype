# Documentation Method and Platform References

Accessed 13 October 2026. These references inform organization and technical
platform interpretation, not EFNS business facts. No products were installed.

## Dataedo

- [AdventureWorks catalogue](https://dataedo.com/samples/html/AdventureWorks/)
- [Sales.Store example](https://dataedo.com/samples/html/AdventureWorks/doc/AdventureWorks_2/tables/Sales_Store_196.html)
- [Documenting tables and views](https://docs.dataedo.com/data-catalog/documenting/documentation-tips/document-tables-and-views/)

The catalogue separates modules, tables, columns and dependencies. The example
shows a table's description alongside columns and key relationships. The manual
uses a consistent table specification followed by exact field metadata, rather
than reproducing AdventureWorks business meaning. The sample site displayed an
“Action cannot be finished” banner, but its catalogue/table content was readable.

## MySQL Sakila

- [Manual](https://dev.mysql.com/doc/sakila/en/)
- [Rental table](https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-rental.html)
- [Payment table](https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-payment.html)
- [Usage examples](https://dev.mysql.com/doc/sakila/en/sakila-usage.html)

The table descriptions explain the represented event and its participant roles.
The usage chapter places queries in operational context. EFNS adopts that
explanatory method, not rental/payment concepts, indexes or MySQL enforcement.

## SchemaSpy

- [Project documentation](https://github.com/schemaspy/schemaspy)
- [Customer example](https://schemaspy.org/samples/chinook/tables/Customer.html)
- [Relationship example](https://schemaspy.org/samples/chinook/relationships.html)

The examples distinguish column metadata, key references and relationship views.
EFNS provides metadata-backed modules, a complete relation list and readable
individual relationship sheets. No SchemaSpy generation or inference was run
against EFNS, and equal column names do not authorize adding relationships.

## Snowflake

- [Constraint overview](https://docs.snowflake.com/en/sql-reference/constraints-overview)
- [CREATE TABLE constraint behavior](https://docs.snowflake.com/en/sql-reference/sql/create-table-constraint)

The standard-table and hybrid-table enforcement models differ. The actual EFNS
table-type metadata, ENFORCED values and GET_DDL must be interpreted together.
Current EFNS standard-table PK/FK/UNIQUE declarations are not engine-enforced;
NOT NULL and the declared Flock Bird Count CHECK are enforced. This does not
replace application validation or eliminate cross-session uniqueness races.

No externally sourced unit, enum, balance formula or referential association has
been introduced into the EFNS dictionary from these examples.
