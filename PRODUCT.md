# Vinted Sniper — product truth

## What this is

A self-hosted desktop tool that watches Vinted search results around the clock and pushes
matches to Telegram, Discord, webhooks or ntfy. It is operated by one person, on their own
machine, for hours at a time.

## Who it is for

A reseller. Not a casual browser and not an enterprise team — one operator who cares
whether a listing arrived thirty seconds after it was listed, and who loses money when the
tool misses a drop or floods them with noise. They run it on a second monitor and read it
dozens of times a day.

## The scene that decides the design

Sitting at a desk, often in a dim room, with the dashboard open next to the work they are
actually doing. They glance, they do not admire. Scannability, consistency and a calm
night-time surface outrank expression everywhere.

Mode: **Operate**. The tool disappears into the task.

## What must never break

The Vinted layer is a working, tuned machine and is treated as a stable API the UI
consumes. Endpoint construction, URL normalisation, polling, session rotation, listing
retrieval, filter and taxonomy logic, search management, notification delivery (Telegram,
Discord, webhook, ntfy), deduplication, the database and the background scheduler are all
out of scope for visual work. Templates, CSS and JavaScript carry the redesign; the Python
changes only where the interface genuinely cannot be expressed otherwise.

## Non-negotiable product rules

- **German.** Every string the user can read is German — navigation, labels, buttons,
  empty states, errors, confirmations, tooltips. Vinted's own listing titles stay as they
  are; that is data, not interface. German number and currency formatting throughout.
- **Vinted.de is the default country site** for new searches. Other supported sites stay
  available and the form remembers the site the user already watches most.
- Nothing may claim to have worked when it did not. A failed notification, a dead session
  and an unreachable destination each say so plainly, in their own words.

## What the redesign owns

The entire visual layer: layout, navigation, typography, spacing, colour, surfaces,
tables, forms, the search builder, dialogs, empty/loading/error states, and responsive
behaviour from phone to wide desktop. Existing sections keep their information and their
function; only their presentation changes.

## Visual commitment

**German engineering instrument.** Cool neutral greys, a tight grid, hairline rules,
tabular figures, small radii, and one restrained accent. It should read as a measuring
instrument that someone would ship, not as a landing page. Both a light and a dark
surface are first-class, following the operating system.
