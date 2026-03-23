# HH Jaba Staff Portal - PRD

## Original Problem Statement
Mobile-first internal ordering system for 5DM employees to order Happy Hour Jaba drinks. Features: user authentication with @5dm.africa email validation, multi-flavor ordering (6 flavors at KES 500 each), credit/M-Pesa payments, admin dashboard with pending orders, stock management, reconciliation reports, and monthly defaulter tracking.

## User Personas
1. **5DM Employee** - Orders drinks using credit or M-Pesa
2. **Admin (mavin@5dm.africa, yongo@5dm.africa)** - Manages orders, stock, reconciliation, users

## Architecture
- **Frontend**: React 19 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + MongoDB (Motor async)
- **Auth**: Emergent Google OAuth + JWT sessions
- **Email**: Resend API (via Emergent key)

## Order Lifecycle
1. Customer places order → Status: **PENDING** (all orders, credit or M-Pesa)
2. Admin reviews and clicks Fulfill → Status: **FULFILLED**
3. Admin can Cancel with mandatory reason → Status: **CANCELLED**
4. Fulfilled orders stay in "Total Owed" until payment verified via POP system

## Payment Verification Flow (POP)
1. Admin creates/shares Credit Purchase Invoice to customer
2. Customer pays via Airtel Money (0733878020) or M-Pesa
3. Customer submits POP (text-based: transaction code, amount, payment type full/partial)
4. Admin verifies POP → Approved (credit restored) or Rejected (with reason)
5. Live "Balance Owed" = Total Amount - Sum of Approved Payments

## What's Been Implemented
### Core Features
- [x] Google OAuth with @5dm.africa restriction
- [x] Profile setup (phone, T&C)
- [x] 6 product flavors at KES 500 each
- [x] Multi-flavor ordering (daily limit: 10, monthly credit: 30K KES)
- [x] ALL orders default to "Pending" - admin must manually fulfill
- [x] M-Pesa manual entry with admin verification
- [x] No Carry-Forward credit rule

### Admin Dashboard (7 Tabs)
- [x] **Pending Orders** — Auto-refresh 10s, manual refresh, fulfill/cancel with reason
- [x] **Stock Management** — Increment totals, production info (batch ID, mfg date)
- [x] **Credit Reconciliation** — Per-user expandable order breakdown, generate invoice, share report, delete user
- [x] **Monthly Defaulters** — Per-item breakdown table + 3 warning templates (Overdue, Limit Reached, Suspended) with WhatsApp links + Backlog credit entry
- [x] **Payment Verification** — POP queue with approve/reject (reason required for reject), auto-notifications to customer
- [x] **Invoices (Credit Purchase)** — Create (credit/cash), delete, print/PDF, WhatsApp share, Email share. Cash invoices auto-marked as PAID
- [x] **Feedback** — View customer messages

### Customer Portal
- [x] Dashboard with credit balance, pending, total owed stats
- [x] Order history with status filters
- [x] Invoice viewer with POP submission (Pay button → transaction code, amount, method, type)
- [x] POP status tracking (pending/approved/rejected)
- [x] Notifications page (read/unread)
- [x] Feedback submission

### Notifications & Communication
- [x] Admin notification bell with unread badge + toast alerts (15s polling)
- [x] WhatsApp share (wa.me/{phone}?text= format) on all invoices
- [x] Email share (mailto: links) on all invoices
- [x] Defaulter warning templates with auto WhatsApp link generation
- [x] Payment approved/rejected notifications to customers
- [x] Push Offer tool (admin → all users)

### System
- [x] UUID-based invoice IDs (no collisions)
- [x] Manual Invoices tab REMOVED — consolidated under Invoices
- [x] Real-time admin notifications for new orders + POP submissions

## Prioritized Backlog

### P1 (High Priority)
- [ ] M-Pesa Daraja API integration for automated payment verification
- [ ] PDF invoice generation (currently uses browser print)
- [ ] Object Storage for image-based POP uploads

### P2 (Medium Priority)
- [ ] Monthly auto-reset of credit balances
- [ ] Bulk order rejection
- [ ] CSV export for reports
- [ ] Email-based reconciliation statements

### P3 (Nice to Have)
- [ ] WebSocket-based push notifications
- [ ] Order scheduling
- [ ] Loyalty points system

## Refactoring Needed
- Break down server.py (~2000 lines) into modular routers
- Extract AdminDashboard.js (~1700 lines) tab content into separate components
