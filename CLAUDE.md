# GTYC Project Context

## Project Overview

Small yacht club management system — "Frankenproject" assembled from multiple existing sources, delivered as two products:

1. **Simple Version** (current scope) — Digital copy of the paper-based bar roster and event booking system.
2. **Professional Version** (future) — Comprehensive admin system with messaging, filing, email notifications, membership management.

## Tech Stack

- **Django 6.x** / Python 3.14 / SQLite (`GTYC.sqlite3`)
- **Bootstrap 5 + Bootstrap Icons** (CDN, no build step)
- **Gunicorn + WhiteNoise + Zrok** (deployment to "Bertha" — old PC at the club)
- Vanilla JavaScript, no frameworks

## Source Projects (Reference)

- **WordPress Plugin** (`/usr/local/var/www/Mallacoota/wp-content/plugins/location_booking_V2`): Bootstrap card UI pattern for DOM elements, two-panel layout, filter bar.
- **Django dots project** (`/usr/local/var/www/dots/`): Event CRUD, email-based auth, mailer service, notification system, filing system.

## Three Django Apps

### `accounts` — Email-based auth
- Custom User model (email as USERNAME_FIELD, no username)
- Case-insensitive email login
- **Roles:** Member (default, public only), Committee Member
- **Titles** (honorific, display only): Commodore, Vice-Commodore, Secretary, Treasurer, Events Officer
- **Permission flags** (control actual access):
  - `can_admin_club` — can administer events and roster
  - `is_event_officer` — can approve/reject/delete events (implies admin access)
- `can_admin` property: True if `can_admin_club` or `is_event_officer`
- `can_approve_events` property: True if `is_event_officer`
- Titles do NOT control access — they are purely symbolic/honorific

### `roster` — Bar Staff Roster
- StaffMember is NOT linked to User (bar staff may not have accounts)
- Rotation computed on-the-fly from an anchor point
- Manual overrides REPLACE the rostered person for that week only (rotation continues unchanged)
- Special event staff appear on roster but don't disturb Friday rotation
- Public page: dates + names only (no phone numbers)
- Print view: A4, matches the current spreadsheet look

### `events` — Event Booking
- Event types include "Club Hire with Bar" which defaults to unapproved
- Approval is a simple flag (no workflow/process), Event Officer toggles it
- Bar staff assigned to events create RosterDate records
- Public page: title + date/time only

## Key Design Decisions

- StaffMember ≠ User (bar staff may not have accounts)
- Rotation algorithm walks forward from anchor, overrides don't break cycle
- Django admin is for system admin only, not club admin
- Club admin gets purpose-built Bootstrap UI
- Titles are honorific only; permission flags control access
- Login page is the default landing page (root URL redirects to login)

## Committee Members (Dev/Seed)

| Name | Title | Admin | Event Officer |
|------|-------|-------|---------------|
| Tanya Flanagan | — | No | No |
| Tim Barrenger | Treasurer | No | No |
| Matt Potito | Commodore | No | No |
| Geoff Coogan | — | No | No |
| Paul Hardy | Secretary | Yes | No |
| Dick Woolcock | — | No | No |
| Graeme Butcher | — | No | No |
| Derek Smith | — | Yes | No |
| Peter Shields | Events Officer | Yes | Yes |

- admin@gtyc.com (superuser, system admin only)
- {firstname.lastname}@gtyc.com for all committee members
- All passwords: `lake.last.night`

## Running Locally

```bash
cd /usr/local/var/www/gtyc
.venv/bin/python manage.py runserver 0.0.0.0:8099
```
