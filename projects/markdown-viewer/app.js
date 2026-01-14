// Initialize Mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    securityLevel: 'loose',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
});

// DOM Elements
const editor = document.getElementById('editor');
const preview = document.getElementById('preview');
const fullscreenBtn = document.getElementById('fullscreenBtn');
const divider = document.getElementById('divider');
const container = document.getElementById('container');

// Sample markdown content
const sampleMarkdown = `# Markdown Viewer with Mermaid

Welcome to the **Markdown Viewer**! This editor supports real-time preview and Mermaid diagrams.

## Features

- Real-time markdown preview
- Mermaid diagram support
- Fullscreen mode (press F11 or click button)
- Resizable panes
- Dark theme

## Code Example

\`\`\`javascript
function greet(name) {
    return \`Hello, \${name}!\`;
}
\`\`\`

## Mermaid Flowchart

\`\`\`mermaid
flowchart TD
    A[Start] --> B{Is it working?}
    B -->|Yes| C[Great!]
    B -->|No| D[Debug]
    D --> B
    C --> E[End]
\`\`\`

## Mermaid Sequence Diagram

\`\`\`mermaid
sequenceDiagram
    participant User
    participant Editor
    participant Preview
    User->>Editor: Type markdown
    Editor->>Preview: Render HTML
    Preview-->>User: Display result
\`\`\`

## Mermaid Class Diagram

\`\`\`mermaid
classDiagram
    class MarkdownViewer {
        +editor: HTMLElement
        +preview: HTMLElement
        +render()
        +toggleFullscreen()
    }
\`\`\`

## Table Example

| Feature | Status |
|---------|--------|
| Markdown | Done |
| Mermaid | Done |
| Fullscreen | Done |

## Blockquote

> This is a beautiful markdown viewer with Mermaid support!

---

*Start editing to see the magic happen!*
`;

// Configure marked
marked.setOptions({
    breaks: true,
    gfm: true
});

// Custom renderer for mermaid code blocks
const renderer = new marked.Renderer();
const originalCodeRenderer = renderer.code.bind(renderer);

renderer.code = function(code, language) {
    if (language === 'mermaid') {
        return `<div class="mermaid">${code}</div>`;
    }
    return originalCodeRenderer(code, language);
};

marked.setOptions({ renderer });

// Render markdown to preview
let mermaidId = 0;

async function renderMarkdown() {
    const markdown = editor.value;

    // Convert markdown to HTML
    const html = marked.parse(markdown);
    preview.innerHTML = html;

    // Render mermaid diagrams
    const mermaidElements = preview.querySelectorAll('.mermaid');

    for (const element of mermaidElements) {
        const code = element.textContent;
        const id = `mermaid-${mermaidId++}`;

        try {
            const { svg } = await mermaid.render(id, code);
            element.innerHTML = svg;
        } catch (error) {
            element.innerHTML = `<pre style="color: #f44336;">Mermaid Error: ${error.message}</pre>`;
        }
    }
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Debounced render
const debouncedRender = debounce(renderMarkdown, 300);

// Editor input handler
editor.addEventListener('input', debouncedRender);

// Fullscreen toggle
function toggleFullscreen() {
    document.body.classList.toggle('fullscreen');

    if (document.body.classList.contains('fullscreen')) {
        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen();
        }
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }
}

fullscreenBtn.addEventListener('click', toggleFullscreen);

// Keyboard shortcut for fullscreen
document.addEventListener('keydown', (e) => {
    if (e.key === 'F11') {
        e.preventDefault();
        toggleFullscreen();
    }

    // ESC to exit fullscreen
    if (e.key === 'Escape' && document.body.classList.contains('fullscreen')) {
        document.body.classList.remove('fullscreen');
    }
});

// Handle browser fullscreen change
document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement) {
        document.body.classList.remove('fullscreen');
    }
});

// Resizable divider
let isResizing = false;

divider.addEventListener('mousedown', (e) => {
    isResizing = true;
    divider.classList.add('dragging');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
});

document.addEventListener('mousemove', (e) => {
    if (!isResizing) return;

    const containerRect = container.getBoundingClientRect();
    const percentage = ((e.clientX - containerRect.left) / containerRect.width) * 100;

    if (percentage > 20 && percentage < 80) {
        const editorPane = document.querySelector('.editor-pane');
        const previewPane = document.querySelector('.preview-pane');

        editorPane.style.flex = `0 0 ${percentage}%`;
        previewPane.style.flex = `0 0 ${100 - percentage}%`;
    }
});

document.addEventListener('mouseup', () => {
    isResizing = false;
    divider.classList.remove('dragging');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
});

// Initialize with sample content
editor.value = sampleMarkdown;
renderMarkdown();
