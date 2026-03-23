# HH Jaba Staff Portal - PRD

## Original Problem Statement
Mobile-first internal ordering system for 5DM employees to order Happy Hour Jaba drinks. Features: user authentication with @5dm.africa email validation, multi-flavor ordering (6 flavors at KES 500 each), credit/M-Pesa payments, admin dashboard with pending orders, stock management, reconciliation reports, and monthly defaulter tracking.

## User Personas
1. **5DM Employee** - Orders drinks using credit or M-Pesa
2. **Admin (mavin@5dm.africa, yongo@5dm.africa)** - Manages orders, stock, reconciliation, users

## Core Requirements
- Google OAuth with @5dm.africa email restriction
- Phone number mandatory, T&C acceptance required
- 6 Happy Hour Jaba flavors at KES 500 each (Tamarind, Watermelon, Beetroot, Pineapple, Hibiscus, Mixed Fruit)
- Daily limit: 10 bottles (any payment)
- Weekly credit limit: 10 bottles
- Monthly credit limit: KES 30,000
- M-Pesa manual entry with admin verification
- No Carry-Forward credit rule

## Architecture
- **Frontend**: React 19 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + MongoDB
- **Auth**: Emergent Google OAuth
- **Email**: Resend API (via Emergent LLM key)

## What's Been Implemented
- [x] Landing page with Google OAuth
- [x] Email domain validation (@5dm.africa)
- [x] Profile setup (phone, T&C)
- [x] User dashboard with credit balance
- [x] 6 product flavors with colored cards
- [x] Multi-flavor ordering with quantity limits
- [x] Credit payment (instant fulfillment)
- [x] M-Pesa payment (pending verification)
- [x] Order history with filters
- [x] Admin dashboard with 6 tabs (Pending, Stock, Reconcile, Defaulters, Invoices, Feedback)
- [x] Pending orders management (shows both pending + recent fulfilled, auto-refresh 10s)
- [x] Stock management with production info (increment logic, batch ID, manufacturing date)
- [x] Credit reconciliation with detailed order breakdown + Generate Invoice + Share Report + Delete User
- [x] Monthly defaulters with per-item breakdown (Order ID, Timestamp, Flavor, Qty, Amount)
- [x] Credit Purchase Invoice module (create, view, print, delete, WhatsApp share, Email share)
- [x] Invoice supports both Credit (pay later) and Cash (auto-mark paid) payment types
- [x] UUID-based invoice IDs (HHJ-INV-[Date]-[UUID5]) - no collisions
- [x] Manual Invoices tab REMOVED - consolidated under Invoices
- [x] Share Feedback system (user -> admin)
- [x] Push Offer tool (admin -> all users)
- [x] Real-time admin notifications (bell icon, dropdown, toast alerts, 15s polling)
- [x] User invoices/notifications pages
- [x] Email notifications (order confirmation)
- [x] Admin: fulfill/cancel orders (cancel requires reason)
- [x] Admin: delete users (with confirmation)
- [x] Admin: share reconciliation reports (date range + email + notification)

## Prioritized Backlog

### P1 (High Priority - Next Phase)
- [ ] M-Pesa Daraja API integration for automated payment verification
- [ ] PDF invoice generation (print-to-PDF currently available)
- [ ] Object Storage integration for image uploads

### P2 (Medium Priority)
- [ ] Monthly auto-reset of credit balances
- [ ] Bulk order rejection
- [ ] Export reports to CSV

### P3 (Nice to Have)
- [ ] WebSocket-based push notifications
- [ ] Order scheduling
- [ ] Loyalty points system

## Refactoring Needed
- Break down server.py (~1700 lines) into modular routers
- Extract AdminDashboard.js (~1500 lines) tab content into separate components
