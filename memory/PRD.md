# HH Jaba Staff Portal - PRD

## Original Problem Statement
Mobile-first internal ordering system for 5DM employees to order Happy Hour Jaba drinks. Google OAuth with @5dm.africa restriction, 6 flavors at KES 500, credit/M-Pesa payments, admin dashboard.

## Architecture
- **Frontend**: React 19 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + MongoDB (Motor async)
- **Auth**: Emergent Google OAuth + JWT sessions
- **Roles**: Super Admin (mavin@5dm.africa), Admin (yongo@5dm.africa), User (all others)

## What's Been Implemented

### Super Admin System
- [x] Super Admin role assigned to mavin@5dm.africa
- [x] Role Switcher UI (Super Admin/Admin/User) — persistent dropdown in header
- [x] Impersonation: switching to User redirects to customer dashboard
- [x] Limit Bypass: SA ignores 10-bottle daily limit and 30K credit cap
- [x] Maintenance Tab: Reset All Test Data + Reset Daily Counters
- [x] Full chat/dispute/feedback visibility

### Admin Dashboard (9 Tabs for SA, 8 for Admin)
- [x] Pending Orders — auto-refresh, fulfill/cancel with reason
- [x] Stock Management — increment, production info
- [x] Credit Reconciliation — per-user breakdown, generate invoice, share report, delete user
- [x] Monthly Defaulters — per-item breakdown, 3 warning templates, backlog credit entry
- [x] Payment Verification — Dual-entry transaction matching, Force Approve, Reject
- [x] Invoices — credit/cash, delete, print, WhatsApp/Email share
- [x] Feedback — customer messages
- [x] Messages — transaction-linked dispute chat hub
- [x] Maintenance (SA only) — reset data/counters, system info

### Order & Payment Lifecycle
- [x] All orders default to "Pending" — admin must manually fulfill
- [x] Dual-entry transaction matching (admin vs customer code/amount)
- [x] Verification Failed → dispute chat → Force Approve with audit trail
- [x] POP text-based: transaction code, amount, full/partial
- [x] No Carry-Forward credit rule

### Communication
- [x] WhatsApp: wa.me/{phone}?text= with invoice details + Airtel Money 0733878020
- [x] Email: mailto: links
- [x] Defaulter warnings (Overdue, Limit Reached, Suspended)
- [x] Payment approved/rejected/declined notifications
- [x] Admin notification bell, push offer tool

### Deployment Guide
- [x] Created DEPLOYMENT.md with full external hosting instructions (Feb 2026)
  - MongoDB Atlas, Google OAuth replacement, Railway/Render/Fly.io backend, Cloudflare Pages frontend

## Known Issues
- Email notifications broken (Resend API key invalid) — non-blocking

## Prioritized Backlog
### P0
- [ ] M-Pesa Daraja API integration
### P1
- [ ] PDF invoice generation
- [ ] Object Storage for image uploads in chat
### P2
- [ ] Monthly credit auto-reset
- [ ] CSV export, email statements
### P3
- [ ] WebSocket notifications, order scheduling, loyalty points

## Refactoring Needed
- `server.py` (2300+ lines) → Break into route modules
- `AdminDashboard.js` (2200+ lines) → Extract tab components
