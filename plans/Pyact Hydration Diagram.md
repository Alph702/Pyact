# PyAct Hydration Diagram

This document illustrates the hydration process in PyAct using Mermaid diagrams.

---

## Hydration Process

```mermaid
flowchart TD
    A[Server/Compiler] --> B[Static HTML + CSS]
    B --> C[Browser Render]
    C --> D[PyAct Runtime Initialization]
    D --> E[Scan DOM for Component Markers]
    E --> F[Reconstruct Virtual DOM in Memory]
    F --> G[Attach Event Listeners]
    G --> H[Page Becomes Interactive]

    click B "Static page initially" "Static content visible but not interactive"
    click H "Interactive PyAct app" "Now the page reacts to user input"
```

---

### Explanation

1. **Server/Compiler** generates HTML from `.pyx` code.
2. **Browser Render** paints the static content.
3. **PyAct Runtime** hydrates by building the Virtual DOM.
4. Event listeners are attached.
5. The app is fully interactive, and state-driven updates now work.
