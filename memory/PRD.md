# HH Jaba Staff Portal - PRD

## Original Problem Statement
Mobile-first internal ordering system for 5DM employees to order Happy Hour Jaba drinks. Features: user authentication with @5dm.africa email validation, multi-flavor ordering (5 flavors at KES 500 each), credit/M-Pesa payments, admin dashboard with pending orders, stock management, reconciliation reports, and monthly defaulter tracking with VAT penalties.

## User Personas
1. **5DM Employee** - Orders drinks using credit or M-Pesa
2. **Admin (mavin@5dm.africa, yongo@5dm.africa)** - Manages orders, stock, reconciliation

## Core Requirements
- Google OAuth with @5dm.africa email restriction
- Phone number mandatory, T&C acceptance required
- 5 Happy Hour Jaba flavors at KES 500 each
- Daily limit: 5 bottles (any payment)
- Weekly credit limit: 5 bottles
- Monthly credit limit: KES 10,000
- M-Pesa manual entry with admin verification
- 16% VAT penalty for defaulters

## Architecture
- **Frontend**: React 19 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + MongoDB
- **Auth**: Emergent Google OAuth
- **Email**: Resend API (via Emergent LLM key)

## What's Been Implemented (March 2024)
- [x] Landing page with Google OAuth
- [x] Email domain validation (@5dm.africa)
- [x] Profile setup (phone, T&C)
- [x] User dashboard with credit balance
- [x] 5 product flavors with colored cards
- [x] Multi-flavor ordering with quantity limits
- [x] Credit payment (instant fulfillment)
- [x] M-Pesa payment (pending verification)
- [x] Order history with filters
- [x] Admin dashboard with 5 tabs
- [x] Pending orders management
- [x] Stock management
- [x] Credit reconciliation view
- [x] Monthly defaulters with VAT calculation
- [x] Manual invoice creation
- [x] Email notifications (order confirmation)

## Prioritized Backlog

### P0 (Critical)
- All core features implemented ✓

### P1 (High Priority - Next Phase)
- [ ] PDF invoice generation
- [ ] Email statements for reconciliation
- [ ] M-Pesa API integration (Daraja)

### P2 (Medium Priority)
- [ ] Monthly auto-reset of credit balances
- [ ] Bulk order rejection
- [ ] Export reports to CSV

### P3 (Nice to Have)
- [ ] Push notifications
- [ ] Order scheduling
- [ ] Loyalty points system

## Next Tasks
1. Implement PDF invoice generation using jsPDF
2. Add email statement functionality
3. Integrate M-Pesa Daraja API for automated verification
