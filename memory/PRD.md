# HH Jaba Staff Portal - PRD

## Original Problem Statement
Mobile-first internal ordering system for 5DM employees to order Happy Hour Jaba drinks. Features: Google OAuth with @5dm.africa restriction, multi-flavor ordering (6 flavors at KES 500), credit/M-Pesa payments, admin dashboard, reconciliation, defaulter tracking.

## Architecture
- **Frontend**: React 19 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + MongoDB (Motor async)
- **Auth**: Emergent Google OAuth + JWT sessions
- **Email**: Resend API

## Order Lifecycle
1. Customer orders → Status: **PENDING** (all orders)
2. Admin fulfills → **FULFILLED** | Admin cancels (reason required) → **CANCELLED**
3. Fulfilled orders stay in "Total Owed" until payment verified

## Payment Verification Flow (Dual-Entry Match)
1. Admin creates Credit Purchase Invoice → shares with customer
2. Customer pays via Airtel Money (0733878020) and submits POP (transaction code + amount)
3. Admin enters their records (code + amount from Airtel Money) → clicks "Match"
4. **Match success** → Auto-approved, credit restored, customer notified
5. **Match fail** → Marked "Verification Failed" with specific reason (code mismatch / amount mismatch)
6. Customer can **Raise Dispute** → opens transaction-linked chat
7. Admin can **Force Approve** after chat resolution (mandatory reason, audit trail recorded)

## What's Been Implemented

### Core Features
- [x] Google OAuth with @5dm.africa restriction + profile setup
- [x] 6 product flavors at KES 500 (daily limit: 10, monthly credit: 30K)
- [x] ALL orders default to "Pending" - admin must manually fulfill
- [x] No Carry-Forward credit rule

### Admin Dashboard (8 Tabs)
- [x] **Pending Orders** — Auto-refresh 10s, fulfill/cancel with reason
- [x] **Stock Management** — Increment totals, production info (batch ID, mfg date)
- [x] **Credit Reconciliation** — Per-user order breakdown, generate invoice, share report, delete user
- [x] **Monthly Defaulters** — Per-item breakdown + 3 warning templates (Overdue, Limit Reached, Suspended) + Backlog credit entry
- [x] **Payment Verification** — Dual-entry transaction matching (Match/Force Approve/Reject), verification_failed flagging
- [x] **Invoices** — Create (credit/cash), delete, print/PDF, WhatsApp/Email share
- [x] **Feedback** — View customer messages
- [x] **Messages** — Centralized dispute chat hub, message counts, quick Force Approve from chat

### Customer Portal
- [x] Dashboard with credit balance, pending, total owed stats
- [x] Order history, invoice viewer with POP submission
- [x] Dispute chat for verification_failed transactions
- [x] Notifications (read/unread), feedback submission

### Transaction Matching & Declines
- [x] Dual-entry match: customer POP vs admin Airtel Money records
- [x] Auto-compare codes (case-insensitive) and amounts (KES 1 tolerance)
- [x] Verification Failed status with specific mismatch reasons
- [x] Payment Declined notifications to customer
- [x] Manual Review queue for failed transactions

### Dispute Resolution
- [x] Transaction-linked chat (customer ↔ admin)
- [x] Chat messages create notifications for the other party
- [x] Admin can Force Approve from chat with audit trail
- [x] Full audit trail on all payment actions (match/reject/force_approve)

### Communication
- [x] WhatsApp share: wa.me/{phone}?text= format with invoice details
- [x] Email share: mailto: links
- [x] Defaulter warning templates (Overdue, Limit Reached, Suspended)
- [x] Payment approved/rejected/declined notifications
- [x] Push Offer tool, admin notification bell with unread badge

## Prioritized Backlog

### P1
- [ ] M-Pesa Daraja API for automated payment verification
- [ ] PDF invoice generation
- [ ] Object Storage for image-based POP/chat uploads

### P2
- [ ] Monthly auto-reset of credit balances
- [ ] CSV export for reports
- [ ] Email-based reconciliation statements

### P3
- [ ] WebSocket push notifications
- [ ] Order scheduling, loyalty points

## Refactoring
- Break down server.py (~2200 lines) into modular routers
- Extract AdminDashboard.js (~2100 lines) tab content into separate components
