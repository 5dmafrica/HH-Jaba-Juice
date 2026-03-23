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
- [x] Admin dashboard with 7 tabs (Pending, Stock, Reconcile, Defaulters, Credit Inv, Manual, Feedback)
- [x] Pending orders management with auto-refresh
- [x] Stock management with production info
- [x] Credit reconciliation with detailed order breakdown
- [x] Monthly defaulters tracking
- [x] Manual invoice creation
- [x] Credit Purchase Invoice module (create, view, print, delete)
- [x] Share Feedback system (user -> admin)
- [x] Push Offer tool (admin -> all users)
- [x] In-app notification system
- [x] User invoices/notifications pages
- [x] Email notifications (order confirmation)
- [x] **Admin Delete Users** (with confirmation dialog)
- [x] **Share Reconciliation Report** (date picker + email + in-app notification)
- [x] **Real-time Admin Notifications** (polling bell icon with unread badge + toast alerts)
- [x] **Detailed Order Breakdown in Reconciliation** (expandable per-item table: timestamp, flavor, qty, cost, status)
- [x] **Credit Invoice Delete Button Fix** (proper error handling + encodeURIComponent)

## Prioritized Backlog

### P1 (High Priority - Next Phase)
- [ ] M-Pesa Daraja API integration for automated payment verification
- [ ] PDF invoice generation
- [ ] Object Storage integration for image uploads

### P2 (Medium Priority)
- [ ] Monthly auto-reset of credit balances
- [ ] Bulk order rejection
- [ ] Export reports to CSV
- [ ] Email statements for reconciliation

### P3 (Nice to Have)
- [ ] WebSocket-based push notifications
- [ ] Order scheduling
- [ ] Loyalty points system

## Refactoring Needed
- Break down server.py (1700+ lines) into modular routers
- Extract AdminDashboard.js (1400+ lines) tab content into separate components
