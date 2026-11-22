# Module 10 – Dashboard and User Interface

## Objective
A professional, responsive SaaS interface built around the real workflow: upload → process → ask → verify → inspect sources → evaluate.

## Pages
| Page | Route | Purpose |
|---|---|---|
| Landing | `/` | What the product does, how it works, system status, honest note on verification limits |
| Register / Login | `/register`, `/login` | Validated forms; redirect back to the requested page |
| Dashboard | `/dashboard` | Document counts by status, empty state with call to action, system status |
| Chat | `/chat`, `/chat/:id` | Conversation list · messages with claims, citation chips and evidence checks · **source panel** (passage, table, figure, page image) · answer-language selector · document scope |
| Documents | `/documents` | Drag-and-drop upload with progress, live processing stages (polling), reprocess, delete, notifications when processing finishes |
| Document viewer | `/documents/:id?page=n` | Page image beside extracted text, tables rendered from Markdown, figures with descriptions; citations deep-link here |
| Search | `/search` | Retrieval explorer: hybrid / semantic / keyword, rerank on/off, scores |
| Evaluation | `/evaluation` | Stat tiles, charts and tables from the latest benchmark runs |
| Profile & settings | `/profile` | Name, **preferred answer language** (multilingual setting), password change, account deletion |

## Design decisions
- **Workflow first:** citations are the core UI element — chips inside sentences, a persistent source panel, deep links into the viewer at the cited page.
- **Honest verification UI:** underline + badge + confidence per statement, an evidence link, a summary ("3 of 4 statements supported") and a permanent note that automatic checks can be wrong. Colour never carries meaning alone (icon + label + text).
- **States everywhere:** loading spinners and skeleton areas, empty states with a next step, inline errors with retry, toast notifications for background events (document ready/failed, deletion).
- **Dark mode:** class-based (`.dark` on `<html>`), defaults to the OS setting, user toggle stored in localStorage (wrapped in try/catch — storage can be blocked). Chart colours are CSS variables with separately chosen dark values.
- **Responsive:** sticky header; navigation becomes a horizontally scrollable row on phones; chat collapses from three columns to one; tables scroll horizontally.
- **Charts** (Evaluation): plain SVG, one axis, ≤3 series using a colour-blind-validated categorical palette, thin bars with rounded tops and 2 px gaps, recessive grid, legend for 2+ series, hover tooltips, and a **"Show table"** view on every chart.
- **Accessibility:** labelled inputs (`useId`), `role="alert"`/`status` on messages, `aria-label`s on icon buttons, `lang` attribute on Telugu text, keyboard-operable drop zone, visible focus rings.

## Component structure
```
src/
├── api/            client (interceptors), auth, users, documents, search, chat
├── context/        AuthProvider, ThemeProvider, ToastProvider (+ context objects)
├── hooks/          useAuth, useTheme, useToast, usePolling
├── layouts/        AppLayout (header, navigation, theme toggle)
├── routes/         ProtectedRoute, GuestRoute
├── components/
│   ├── ui/         Button, TextField, Alert, Spinner, AuthImage, MarkdownTable, ThemeToggle
│   ├── documents/  UploadDropzone, DocumentList, StatusBadge
│   ├── chat/       AssistantMessage, SourcePanel, Composer
│   └── charts/     ChartFrame (legend + table view), GroupedBarChart, LineChart
├── pages/          one file per route
└── utils/          formatting, validation, document status, verification labels (+ unit tests)
```

## Run
```powershell
cd frontend
npm run dev      # development
npm test         # unit tests (Vitest)
npm run lint     # oxlint
npm run build    # production build in dist/
```

## Interview questions
1. How does the UI communicate uncertainty without overwhelming users?
2. How do you show protected images (`<img>` can't send an Authorization header)?
3. Polling vs WebSockets vs Server-Sent Events for processing progress — trade-offs?
4. How did you implement dark mode, and why not rely only on the OS setting?
5. What makes a chart accessible?
6. How is global state handled (contexts) and why not Redux here?
