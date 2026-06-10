# Accountant Workflows

## Unpaid Invoices

Use:

```text
myob_invoice_list(filter="Status eq 'Open'")
```

## Prepare Invoice

Use:

```text
myob_invoice_prepare_create(json_body={...}, layout="Service")
```

Review the exact payload, approve with `myob_approval_approve`, then commit with `myob_commit_operation`.

## Record Payment

Use:

```text
myob_customer_payment_prepare_record(json_body={...})
```

Payments are high-risk and require explicit approval.

## Spend Money

Use:

```text
myob_spend_money_prepare_create(json_body={...})
```

The prepared operation includes detected financial amounts and the exact MYOB payload.
