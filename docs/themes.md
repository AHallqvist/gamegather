# Themes

The header offers **System**, **Light**, and **Dark** on every page. Light keeps
the original design. System is the default and follows the device's appearance,
including changes while the page is open. An explicit theme overrides the device.

The selection is saved in this browser's `localStorage` under `gamegather.theme`,
not in an account or database. It applies across pages, reloads, and other open
tabs on the same origin. If storage is blocked, switching still works until the
next page load. Without JavaScript, the selector stays hidden and CSS follows the
device preference (Light if dark-mode detection is unavailable).

## How it works

- `app/static/styles.css` defines semantic palette variables and shared components.
  The root palette is Light. Named themes override variables using
  `:root[data-theme="<id>"]` and set their own `color-scheme` for native controls.
- `app/static/theme.js` registers the available themes, resolves the preference,
  and builds the dropdown. It sets `data-theme` on `<html>` before the stylesheet
  loads, preventing a flash of the wrong theme during normal loading. Keep this
  small script synchronous in `app/templates/base.html`, before the stylesheet.
- System is a selection, not a palette: it resolves to Light or Dark. A future
  named theme is applied directly, regardless of the device preference.
- The CSS dark-mode media query is a no-JavaScript fallback. Keep its palette in
  sync with the explicit Dark palette; a JavaScript test checks this.

## Add a theme

For example, to add **Colorful** later:

1. Add a palette **after the existing palettes**, before the component rules, in
   `app/static/styles.css`:

   ```css
   :root[data-theme="colorful"] {
     color-scheme: light;
     --page-background: #fff7ed;
     --surface-background: #fff;
     --text-primary: #31213c;
     --text-muted: #66516d;
     --brand-color: #6b21a8;
     --accent-color: #7e22ce;
     --button-background: #7e22ce;
     --button-hover: #6b21a8;
     --button-text: #fff;
     --secondary-background: #f3e8ff;
     --secondary-hover: #e9d5ff;
     --secondary-text: #6b21a8;
     --focus-ring: #7e22ce;
   }
   ```

   This is an illustrative starting palette, not a shipped theme. Variables you
   omit inherit from Light, **not** from the device's Dark palette. Set
   `color-scheme` to `light` or `dark` explicitly and review inherited values.

2. Register it in the `themes` array in `app/static/theme.js`:

   ```js
   { id: "colorful", label: "Colorful" },
   ```

   Use a stable, lowercase ID; it is stored in users' browsers. The dropdown is
   generated from this list, so no page-template changes are needed. Do not add a
   `system` entry; the script adds it separately. Removed or unknown stored IDs
   automatically fall back to System.

3. Check all pages, interaction states, and contrast before shipping. Update the
   selector-option assertion in `app/tests/theme.test.cjs` for the new entry.

No framework, build step, new routes, or database migration is required.

## Palette variables

All component colors should use these variables rather than hardcoded colors.
Layout, typography, spacing, and radii remain shared across themes.

| Variable | Purpose |
| --- | --- |
| `--page-background` | Page canvas |
| `--surface-background` | Header, cards, forms, inputs, and neutral notices |
| `--text-primary` | Main text and input text |
| `--text-muted` | Supporting text, metadata, and eyebrows |
| `--brand-color` | Header brand |
| `--border-color` | Header and panel borders |
| `--divider-color` | Registration/attendance row dividers |
| `--input-border` | Input and select borders |
| `--accent-color` | Links and prominent counts |
| `--button-background`, `--button-hover`, `--button-text` | Primary button states |
| `--secondary-background`, `--secondary-hover`, `--secondary-text` | Secondary button states |
| `--notice-border` | Neutral notice indicator |
| `--success-background`, `--success-border` | Success notices |
| `--error-color` | Validation text and invalid input borders |
| `--focus-ring` | Keyboard focus outline |
| `--card-shadow` | Full CSS `box-shadow` value for panels |

Prefer at least 4.5:1 contrast for normal text and 3:1 for large text and focus
indicators. Test muted text, links, both button styles (including hover), and
validation messages against their actual backgrounds. Do not rely on color alone
to communicate success or errors.

## Validation

Run the JavaScript tests with Node.js 18 or newer (no npm install required):

```bash
node --test app/tests/theme.test.cjs
```

The regular Python suite also checks the shared selector and script ordering:

```bash
PYTHONPATH=app python -m unittest discover -s app/tests
```

In a browser, check the listing, creation, public game, organizer, management,
attendance, withdrawal confirmation, and error pages. Verify both themes, keyboard
focus, form validation, success notices, and narrow/mobile layouts. Test a reload
with an explicit saved theme opposite to the device preference, switching back
to System, and a device-preference change. With JavaScript disabled, confirm that
the device preference still applies and no empty selector is shown.
