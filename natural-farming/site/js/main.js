// Theme toggle (light / dark). The actual theme is applied earlier by an
// inline script in <head> to avoid a flash of unstyled content; this block
// just wires up the toggle button after DOMContentLoaded.
function aiseedSetTheme(theme) {
    try {
        if (theme === 'light' || theme === 'dark') {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('aiseed-theme', theme);
        } else {
            document.documentElement.removeAttribute('data-theme');
            localStorage.removeItem('aiseed-theme');
        }
    } catch (e) { /* localStorage may be blocked */ }
}

document.addEventListener('DOMContentLoaded', function() {
    // Theme toggle button — flips between light and dark explicitly.
    document.querySelectorAll('.theme-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const osDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const isDarkNow = current === 'dark' || (current === null && osDark);
            aiseedSetTheme(isDarkNow ? 'light' : 'dark');
        });
    });

    // Mobile navigation toggle
    const navToggle = document.querySelector('.nav-toggle');
    const nav = document.querySelector('.nav');

    if (navToggle && nav) {
        navToggle.addEventListener('click', () => {
            nav.classList.toggle('active');
            navToggle.classList.toggle('active');
        });
        nav.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                nav.classList.remove('active');
                navToggle.classList.remove('active');
            });
        });
    }

    // Dropdown submenu (nav-group). Click on the parent button toggles
    // `.open` on the group — required for mobile accordion, harmless on
    // desktop (where the submenu also opens on :hover / :focus-within).
    document.querySelectorAll('.nav-group').forEach(group => {
        const parent = group.querySelector('.nav-parent');
        if (!parent) return;
        parent.addEventListener('click', event => {
            event.stopPropagation();
            const willOpen = !group.classList.contains('open');
            document.querySelectorAll('.nav-group.open').forEach(g => {
                if (g !== group) {
                    g.classList.remove('open');
                    const p = g.querySelector('.nav-parent');
                    if (p) p.setAttribute('aria-expanded', 'false');
                }
            });
            group.classList.toggle('open', willOpen);
            parent.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
        });
    });

    // Click outside closes any open dropdown (desktop behaviour).
    document.addEventListener('click', event => {
        if (!event.target.closest('.nav-group')) {
            document.querySelectorAll('.nav-group.open').forEach(g => {
                g.classList.remove('open');
                const p = g.querySelector('.nav-parent');
                if (p) p.setAttribute('aria-expanded', 'false');
            });
        }
    });

    // Series TOC sidebar — mobile hamburger
    const seriesToc = document.getElementById('seriesToc');
    const tocToggle = document.querySelector('.series-toc-toggle');
    const tocClose = document.querySelector('.series-toc-close');
    const tocBackdrop = document.querySelector('.series-toc-backdrop');
    // In-page section list (h2s of the current chapter) injected under the
    // highlighted chapter in the sidebar, with a scroll-following highlight.
    // Built BEFORE the drawer wiring below so the new links also pick up the
    // close-on-tap behaviour on mobile.
    const tocCurrent = seriesToc ? seriesToc.querySelector('.toc-chapter.is-current') : null;
    const proseRoot = document.querySelector('.article-main .prose');
    if (tocCurrent && proseRoot) {
        const sections = Array.from(proseRoot.querySelectorAll('h2'));
        if (sections.length >= 2) {
            const list = document.createElement('ol');
            list.className = 'toc-sections';
            sections.forEach((h, i) => {
                if (!h.id) h.id = 'sec-' + (i + 1);
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = '#' + h.id;
                a.textContent = h.textContent;
                li.appendChild(a);
                list.appendChild(li);
            });
            tocCurrent.insertAdjacentElement('afterend', list);

            const links = Array.from(list.querySelectorAll('a'));
            let activeIdx = -1;
            const setActive = idx => {
                if (idx === activeIdx) return;
                activeIdx = idx;
                links.forEach((a, i) => a.classList.toggle('is-active', i === idx));
            };
            let ticking = false;
            const updateActive = () => {
                ticking = false;
                const fromTop = window.scrollY + 110;
                let idx = -1;
                for (let i = 0; i < sections.length; i++) {
                    if (sections[i].offsetTop <= fromTop) idx = i;
                }
                setActive(idx);
            };
            document.addEventListener('scroll', () => {
                if (!ticking) {
                    ticking = true;
                    window.requestAnimationFrame(updateActive);
                }
            }, { passive: true });
            updateActive();
        }
        // Bring the current chapter (and its section list) into view inside
        // the sidebar's own scroll area.
        const target = tocCurrent.offsetTop - seriesToc.clientHeight / 3;
        if (target > 0) seriesToc.scrollTop = target;
    }

    if (seriesToc && tocToggle) {
        const openToc = () => {
            seriesToc.classList.add('is-open');
            if (tocBackdrop) tocBackdrop.classList.add('is-open');
            document.body.classList.add('series-toc-open');
            tocToggle.setAttribute('aria-expanded', 'true');
        };
        const closeToc = () => {
            seriesToc.classList.remove('is-open');
            if (tocBackdrop) tocBackdrop.classList.remove('is-open');
            document.body.classList.remove('series-toc-open');
            tocToggle.setAttribute('aria-expanded', 'false');
        };
        tocToggle.addEventListener('click', () => {
            seriesToc.classList.contains('is-open') ? closeToc() : openToc();
        });
        if (tocClose) tocClose.addEventListener('click', closeToc);
        if (tocBackdrop) tocBackdrop.addEventListener('click', closeToc);
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && seriesToc.classList.contains('is-open')) {
                closeToc();
            }
        });
        // Tapping a chapter link inside the open mobile drawer should close it
        seriesToc.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                if (seriesToc.classList.contains('is-open')) closeToc();
            });
        });
    }
});
