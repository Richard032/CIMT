(() => {
    'use strict';
    const filters = new Map();

    function makeFilter(area) {
        const form = Array.from(area.children).find(child => child.matches('form.report-filters'));
        if (!form) return;
        const items = Array.from(area.querySelectorAll('[data-report-item]'))
            .filter(item => item.closest('[data-filter-area]') === area);
        if (items.length === 0) return;
        const fields = Array.from(form.querySelectorAll('[data-filter]'));

        fields.filter(field => field.tagName === 'SELECT').forEach(field => {
            const values = [...new Set(items.map(item => item.dataset[field.dataset.filter] || '').filter(Boolean))].sort();
            values.forEach(value => field.add(new Option(value, value)));
            if (values.length < 2) field.parentElement.hidden = true;
        });

        function apply() {
            let shown = 0;
            items.forEach(item => {
                item.hidden = !fields.every(field => !field.value || (field.dataset.filter === 'search'
                    ? item.textContent.toLocaleLowerCase().includes(field.value.toLocaleLowerCase())
                    : item.dataset[field.dataset.filter] === field.value));
                if (!item.hidden) shown++;
            });
            area.querySelectorAll('[data-filter-container]').forEach(container => {
                const children = items.filter(item => container.contains(item));
                container.hidden = children.length > 0 && children.every(item => item.hidden);
            });
            const scope = fields.filter(field => field.value).map(field => field.dataset.filter + ': ' + field.value);
            form.querySelector('output').textContent = `Showing ${shown} of ${items.length}. ${scope.join(' · ') || 'All records in this section.'}`;
            form.querySelector('[data-no-matches]').hidden = shown > 0;
        }

        function reset(context) {
            fields.forEach(field => { field.value = ''; });
            if (context) fields.forEach(field => {
                if (field.tagName === 'SELECT' && ['device', 'target'].includes(field.dataset.filter))
                    field.value = context.dataset[field.dataset.filter] || '';
            });
            apply();
        }

        form.addEventListener('input', apply);
        form.addEventListener('change', apply);
        form.addEventListener('submit', event => event.preventDefault());
        form.addEventListener('reset', event => { event.preventDefault(); reset(); });
        filters.set(area, reset);
        form.hidden = false;
        apply();
    }

    function revealHash() {
        let id;
        try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
        const target = document.getElementById(id);
        if (!target) return;
        const context = target.closest('[data-report-item]');
        // Deep links must not land in content hidden by an earlier filter choice.
        filters.forEach((reset, area) => { if (area.contains(target)) reset(context); });
        for (let parent = target; parent; parent = parent.parentElement)
            if (parent.tagName === 'DETAILS') parent.open = true;
        target.scrollIntoView({block: 'start'});
        if (target.tagName === 'DETAILS') target.querySelector('summary')?.focus({preventScroll: true});
        else {
            // Move keyboard reading to the destination without adding a tab stop.
            target.setAttribute('tabindex', '-1');
            target.focus({preventScroll: true});
        }
        const section = target.closest('main > section');
        if (section) setCurrent(section.id);
    }

    function setCurrent(id) {
        document.querySelectorAll('.report-nav a').forEach(link => {
            if (link.getAttribute('href') === '#' + id) link.setAttribute('aria-current', 'location');
            else link.removeAttribute('aria-current');
        });
    }

    function setupViewer() {
        const dialog = document.getElementById('evidence-viewer');
        if (!dialog || typeof dialog.showModal !== 'function') return;
        const image = dialog.querySelector('img');
        const caption = dialog.querySelector('#evidence-caption');
        const toolbar = key => dialog.querySelector('[data-viewer="' + key + '"]');
        let opener, gallery = [], index = 0;

        function zoom(enabled) {
            dialog.querySelector('.viewer-image').classList.toggle('zoomed', enabled);
            toolbar('zoom').setAttribute('aria-pressed', String(enabled));
        }

        function show(next) {
            index = Math.max(0, Math.min(gallery.length - 1, next));
            const link = gallery[index];
            image.src = link.href;
            image.alt = link.dataset.caption || link.querySelector('img')?.alt || 'Saved masked screenshot';
            caption.textContent = `${index + 1} of ${gallery.length} · ${image.alt}`;
            toolbar('original').href = link.href;
            toolbar('previous').disabled = index === 0;
            toolbar('next').disabled = index === gallery.length - 1;
            zoom(false);
            if (document.activeElement?.disabled) toolbar('close').focus();
        }

        document.querySelectorAll('a.evidence-link').forEach(link => link.addEventListener('click', event => {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            opener = link;
            const seen = new Set();
            const links = Array.from(document.querySelectorAll('a.evidence-link'));
            // Prefer the saved step order over shortcuts shown earlier in Findings.
            const ordered = links.filter(candidate => candidate.querySelector('img'))
                .concat(links.filter(candidate => !candidate.querySelector('img')));
            gallery = ordered.filter(candidate => {
                if (candidate.dataset.gallery !== link.dataset.gallery || seen.has(candidate.href)) return false;
                seen.add(candidate.href);
                return true;
            });
            show(gallery.findIndex(candidate => candidate.href === link.href));
            dialog.showModal();
            toolbar('close').focus();
        }));
        toolbar('close').addEventListener('click', () => dialog.close());
        toolbar('previous').addEventListener('click', () => show(index - 1));
        toolbar('next').addEventListener('click', () => show(index + 1));
        toolbar('zoom').addEventListener('click', () => zoom(toolbar('zoom').getAttribute('aria-pressed') !== 'true'));
        dialog.addEventListener('close', () => { if (opener) opener.focus(); });
        dialog.addEventListener('keydown', event => {
            if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
                event.preventDefault();
                show(index + (event.key === 'ArrowLeft' ? -1 : 1));
            }
        });
    }

    document.querySelectorAll('[data-filter-area]').forEach(makeFilter);
    window.addEventListener('hashchange', revealHash);
    document.querySelectorAll('a[href^="#"]').forEach(link => link.addEventListener('click', () => {
        if (link.hash === location.hash) revealHash();
    }));
    if (typeof IntersectionObserver === 'function') {
        const observer = new IntersectionObserver(entries => {
            const visible = entries.find(entry => entry.isIntersecting);
            if (visible) setCurrent(visible.target.id);
        }, {rootMargin: '-5% 0px -70% 0px'});
        document.querySelectorAll('main > section').forEach(section => observer.observe(section));
    }
    setupViewer();
    if (location.hash) revealHash();
    else setCurrent('overview');
})();
