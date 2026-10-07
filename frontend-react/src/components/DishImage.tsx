/** Dish image with hotlink-safe referrer policy and a letter tile fallback. */
export default function DishImage({ name, url, cls = 'dish' }: { name: string; url?: string | null; cls?: string }) {
  const initial = (name || '?').trim().charAt(0).toUpperCase();
  if (!url) {
    return (
      <div className={`${cls} dish-fallback`} aria-label={name}>
        <span>{initial}</span>
      </div>
    );
  }
  return (
    <img
      className={cls}
      src={url}
      alt={name}
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={(e) => {
        const el = e.target as HTMLImageElement;
        el.style.display = 'none';
        const d = document.createElement('div');
        d.className = `${cls} dish-fallback`;
        const s = document.createElement('span');
        s.textContent = initial;
        d.appendChild(s);
        el.parentNode?.insertBefore(d, el);
      }}
    />
  );
}
