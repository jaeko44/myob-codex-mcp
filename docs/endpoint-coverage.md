# Endpoint Coverage

The MCP has named coverage for:

- General ledger accounts
- Tax codes
- Jobs
- Customers
- Suppliers
- Employees
- Sales invoices
- Sales orders
- Purchase bills
- Customer payments
- Supplier payments
- Bank accounts
- Spend money transactions
- Receive money transactions
- General journals
- Inventory items
- Attachments

For endpoints not yet represented by named tools, use `myob_raw_get` for reads and `myob_raw_prepare_mutation` plus `myob_raw_commit_mutation` for writes.

This gives full API reach without bypassing approval controls.
