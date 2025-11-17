// src/hmr-keep-state.ts
if (import.meta.hot) {
  import.meta.hot.on('vite:beforeFullReload', () => {
    sessionStorage.setItem('hmr:last-url', location.href);
    sessionStorage.setItem('hmr:last-scroll', String(window.scrollY));
  });

  window.addEventListener('load', () => {
    const url = sessionStorage.getItem('hmr:last-url');
    const scroll = sessionStorage.getItem('hmr:last-scroll');
    if (url && url !== location.href) history.replaceState(null, '', url);
    if (scroll) window.scrollTo(0, +scroll);
  });
}
