# Tracely public landing page

Design proposal · 2026-10-07 · Not yet implemented

## Purpose

Introduce Tracely in approachable language, show what works today, and invite visitors to create an account or sign in. Make the page creative and fun while keeping product claims accurate. This document specifies a future public page; it does not change the existing application or authentication flows.

## Creative direction: Signal playground

An illustrated workspace where scattered application events become readable evidence. Curved tracks, rounded event cards, small status lights, and dotted connectors give the page personality. Use editorial spacing and a clear reading order so the playful graphics support the story.

Avoid an all-purple appearance, generic gradient blobs, fake customer logos, invented metrics, and claims of automatic root-cause diagnosis.

### Visual foundations

| Role | Color | Use |
|---|---|---|
| Canvas | Warm cream `#FFF9EF` | Main page background |
| Ink | Deep navy `#172D42` | Headings, body text, outlines |
| Action | Coral `#F36B53` | Primary buttons with navy text, error accents |
| Fresh accent | Mint `#C8EBDD` | Feature panels and success states |
| Highlight | Butter yellow `#FFE49B` | Upcoming section and small highlights |
| Secondary accent | Sky blue `#A9D8ED` | Connectors and supporting illustrations |
| Surface | White `#FFFFFF` | Product preview and cards |

Use navy for readable text on light accent surfaces. Validate final contrast in implementation; do not use color alone to distinguish errors, success, or availability. Purple may appear inside an authentic product screenshot, but should not dominate the landing page.

- Typography: retain the application's existing font where practical; use large, expressive headings, comfortable body text, and monospace only for event snippets.
- Shape: rounded cards, pill labels, thin navy outlines, and restrained offset shadows. Slight rotations belong on decorative elements, not readable body copy.
- Layout: a centered content width around 1160px, generous section spacing, and short paragraphs. Desktop hero uses two columns; mobile becomes a single column with copy and actions first.
- Icons: reuse the existing icon library. Build illustrations from SVG and HTML/CSS; no new image-generation assets are required.

## Page structure and copy

### 1. Navigation

Left: Tracely wordmark. Right: **How it works**, **Features**, **Sign in**, and **Create an account**. Section links scroll to their corresponding content. Keep account actions easy to find on mobile without crowding the header.

The page is public and must not require authentication. Account buttons connect to the existing sign-up/sign-in experience when implemented; exact route wiring must be checked against the application at that time.

### 2. Hero

Eyebrow: **FOLLOW THE SIGNAL.**

Headline: **Something broke. Follow the signal.**

Supporting copy: Bring your application events together, spot repeated failures, and see the evidence behind them.

Primary action: **Create an account**  
Secondary action: **Sign in**

Visual: event cards travel along curved tracks. Several coral error cards gather into an **Incident detected** card, while mint successful-request cards continue along their path. Include short example labels such as `payment-api`, `500`, and `Request failed`.

Persistent label: **Illustrated workflow**. This graphic illustrates the working detector concept; it is not a screenshot of an available live incident dashboard.

### 3. Product preview

Heading: **Your events, with room to investigate.**

Copy: Choose a project, filter the noise, and inspect the details of a request.

Show a browser frame based on the existing live Events page: project selector, service/level/text/time filters, a short event table, and an expandable event detail. Use synthetic content only, with no real account details, credentials, or customer data.

Persistent label: **Interactive demo · sample events**.

On desktop, the browser frame may start slightly tilted and straighten on hover or keyboard focus. Selecting a sample event reveals its status, latency, timestamp, and safe sample metadata. On mobile, use a flat frame with a compact list and a readable detail view rather than shrinking an entire desktop screenshot.

The demo should work without a backend connection or visitor account. Keep any preview interactivity separate from real project data.

### 4. How it works

Heading: **From your app to a clearer picture.**

| Step | Copy | Illustration |
|---|---|---|
| Connect your app | Create a project and get an ingestion key. | Application window connecting to a project card |
| Send the signals | Collect requests, errors, and useful context. | Small event cards moving along a track |
| Spot repeated failures | The detector tracks sustained failures and recovery. | A cluster of failures followed by a recovery marker |

Use a connecting path across the three steps on desktop and a vertical connector on mobile. A small dot can travel along the path once as the section enters view.

### 5. Available today

Heading: **Built and working today.**

| Feature card | Description |
|---|---|
| Your own workspace | Email or Google sign-in, plus password recovery. |
| Projects & keys | Separate application data and manage ingestion access. |
| Live event explorer | Search, filter, and inspect stored events. |
| Background detection | Persistent incident opening, updates, and recovery. |

Visible qualification: **Detection runs today; live incident screens are still being built.**

The current product is a local development setup. Do not imply that this proposal includes a hosted service, managed deployment, or production guarantees. Password-reset delivery depends on configured email delivery. Recheck availability before publishing the page.

### 6. Upcoming capabilities

Pale-yellow panel with the heading **Next on the workbench**.

Visible status: **Upcoming—not available yet**.

- Exception grouping
- Live incident views
- Evidence-based investigations
- Optional local AI assistance

Use outlined cards or small sketches, visually distinct from available features. Do not include release dates, functioning product controls, or claims that AI identifies proven causes.

### 7. Closing call to action and footer

Headline: **Less guessing. More evidence.**

Copy: Start with one project and follow your first signal.

Actions: **Create an account** and **Already here? Sign in**.

Footer: Tracely wordmark and a short line, **Make sense of the signals.** Only add documentation, privacy, or other links when their destinations actually exist.

## Motion and interaction

| Element | Behavior |
|---|---|
| Hero illustration | Short event-flow sequence on entry; settle into a static composition within five seconds |
| Product frame | Subtle straighten/lift on hover and focus; flat on touch devices |
| How-it-works connector | One short progress animation on entering view |
| Feature cards and buttons | Small color/position transitions, approximately 150–250ms |

Prefer CSS transforms and opacity, with IntersectionObserver for entry triggers if needed. Avoid heavy animation libraries for this page. Keep text and controls usable before animation starts. No autoplay sound, flashing effects, scroll hijacking, or continuous distracting loops.

Respect `prefers-reduced-motion`: show the final static illustration, remove travel/rotation effects, and preserve all information. Any future animation lasting more than five seconds needs a pause control.

## Responsive and accessibility requirements

- Maintain clear heading order, semantic navigation/sections, visible focus states, and descriptive button labels.
- All preview interactions must support keyboard use; dialogs must handle focus, Escape, and focus return.
- Keep decorative SVGs hidden from assistive technology; provide an accessible description for graphics that explain the workflow.
- Use comfortable text sizes and touch targets, at least 44px for primary controls. Prevent page-level horizontal overflow.
- Stack content naturally on narrow screens; do not rely on hover for information or actions.
- Preserve text contrast and status labels in every animation state.
- Keep the initial page lightweight: reuse fonts/icons, avoid video backgrounds, and reserve graphic dimensions to prevent layout shifts.

## Implementation boundaries

Build the public landing page without redesigning the authenticated workspace or changing auth/session behavior. Preserve existing account creation, Google linking, sign-in, recovery, and session expiration. Do not implement upcoming features as part of the landing-page work.

Before implementation, confirm the public-page and account-screen routing so an existing session and an unauthenticated visitor each receive a predictable experience. Hosting and deployment are separate decisions; this proposal does not publish anything.

## Acceptance checklist

- [ ] Public page contains hero, product preview, how it works, available features, upcoming capabilities, and account calls to action.
- [ ] Cream/navy/coral/mint palette is implemented consistently and is not predominantly purple.
- [ ] Graphics feel playful, with lightweight animation and a complete reduced-motion experience.
- [ ] Preview data and illustrations are explicitly labeled; product claims match implemented capabilities.
- [ ] Sign-up and sign-in actions reach the correct existing screens without breaking authenticated behavior.
- [ ] Desktop/mobile layouts, keyboard access, focus behavior, contrast, and overflow are verified.
- [ ] Existing frontend build and relevant authentication/navigation checks pass.

No application code has been changed by creating this design document.
