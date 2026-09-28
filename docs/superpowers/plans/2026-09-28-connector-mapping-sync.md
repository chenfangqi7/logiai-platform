# Connector / Mapping / Sync incremental implementation

## Goal

Make REST, file, and webhook imports reliable for different TMS/WMS/ERP payloads while preserving the existing demo flow and tenant isolation.

## Sequence and gates

1. Mapping: make the import model explicit, validate transform configs, normalize status and dates, expose target metadata and a read-only preview. Run connector, mapping, and shipment tests.
2. Import: upsert related entities and tracking events, retain source provenance, isolate bad rows, and return useful validation results. Run import, webhook, file, and tenant tests.
3. Sync: persist job history and per-row errors, prevent concurrent runs, support bounded pagination and incremental cursors. Run connector and sync tests.
4. UI: guided transform controls, mapping preview, sync status/history, and actionable error display. Run typecheck/build and browser smoke checks.
5. Final: run the complete server suite and application smoke flow, review the diff for tenant boundaries and secret exposure.

Keep existing endpoints compatible while adding new capabilities. Add migrations only when persistence requires them.
