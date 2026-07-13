# Stock & Stir Public Homepage

This package contains a responsive public marketing homepage for GoDaddy or any conventional static web host.

## Files

- `index.html` — all public page content and layout
- `styles.css` — colors, typography, responsive design, and component styling
- `script.js` — mobile navigation, public ingredient demo, and application link map

## Ownership boundary

### Lynsey / public website

Safe to edit in `index.html`:

- Headings and paragraphs
- Public images
- Feature descriptions
- Pricing copy
- About section
- Footer content
- Navigation labels

Safe to edit in `styles.css`:

- Brand colors
- Fonts
- Spacing
- Section backgrounds
- Button appearance

### Engineering / authenticated application

Do not move application logic into this public page.

Engineering owns:

- Login and account creation
- Household inventory
- Pantry, refrigerator, freezer, and fresh-today data
- Cooking Knowledge Base
- Recipe generation
- Candidate ranking
- Cooking timelines
- Subscription permissions
- API calls

The centralized integration points are in `script.js`:

```js
const APP_URLS = {
  login: "/login",
  signup: "/signup",
  "signup-basic": "/signup?plan=basic",
  "signup-premium": "/signup?plan=premium",
  kitchen: "/app/kitchen",
  demo: "/sample-meal"
};
```

Update those URLs when the hosted SNS application routes are available.

## GoDaddy installation

### If using a file-based GoDaddy site or cPanel

1. Open the site root, commonly `public_html`.
2. Back up the current homepage.
3. Upload `index.html`, `styles.css`, and `script.js` into the same directory.
4. Confirm that the page loads at the domain.
5. Test the mobile menu and public ingredient preview.

### If using GoDaddy Website Builder

Website Builder may not permit a full custom three-file site as the primary theme. Use its custom HTML section only if it supports full-width embedded code. A file-based hosting plan is preferable for this page because it preserves the design and allows direct API links later.

## Images

The current page uses public remote images from Unsplash. Replace them with owned Stock & Stir photography before launch when available.

## Launch checklist

- Replace placeholder application routes
- Add real Privacy and Terms pages
- Confirm pricing language
- Replace stock photography as desired
- Remove or revise any feature not ready for beta
- Connect the domain email address
- Test desktop, tablet, and phone
- Verify color contrast and keyboard navigation
