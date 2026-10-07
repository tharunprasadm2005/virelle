/** Modern inline SVG icons (stroke style, currentColor). No emoji, no clip-art. */

interface P {
  size?: number;
  className?: string;
}

function base(size: number, className: string | undefined, path: JSX.Element) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {path}
    </svg>
  );
}

export function IconSearch({ size = 18, className }: P) {
  return base(size, className, <><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.5" y2="16.5" /></>);
}
export function IconHeart({ size = 18, className }: P) {
  return base(size, className, <path d="M12 20.5C7 16.5 3.5 13.3 3.5 9.5 3.5 7 5.5 5 8 5c1.6 0 3.1.8 4 2.1C12.9 5.8 14.4 5 16 5c2.5 0 4.5 2 4.5 4.5 0 3.8-3.5 7-8.5 11z" />);
}
export function IconThumbUp({ size = 18, className }: P) {
  return base(size, className, <><path d="M7 11v9H4a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1h3z" /><path d="M7 11l4.2-7.4A1.6 1.6 0 0 1 14 5.7V10h6.3a1.7 1.7 0 0 1 1.7 2.1l-1.5 6.4a1.7 1.7 0 0 1-1.7 1.3H7" /></>);
}
export function IconThumbDown({ size = 18, className }: P) {
  return base(size, className, <><path d="M17 13V4h3a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1h-3z" /><path d="M17 13l-4.2 7.4A1.6 1.6 0 0 1 10 18.3V14H3.7A1.7 1.7 0 0 1 2 11.9l1.5-6.4A1.7 1.7 0 0 1 5.2 4.2H17" /></>);
}
export function IconPot({ size = 18, className }: P) {
  return base(size, className, <><path d="M4 10h16v2a8 8 0 0 1-8 8 8 8 0 0 1-8-8v-2z" /><path d="M2 10h20" /><path d="M9 6c0-1.5 1-1.5 1-3M14 6c0-1.5 1-1.5 1-3" /></>);
}
export function IconClock({ size = 16, className }: P) {
  return base(size, className, <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></>);
}
export function IconServings({ size = 16, className }: P) {
  return base(size, className, <><path d="M4 12h16a8 8 0 0 1-16 0z" /><path d="M9 12V6M12 12V4.5M15 12V6" /></>);
}
export function IconStar({ size = 16, className }: P) {
  return base(size, className, <path d="M12 3.5l2.6 5.3 5.9.9-4.2 4.1 1 5.8-5.3-2.8-5.3 2.8 1-5.8L2.5 9.7l5.9-.9L12 3.5z" />);
}
export function IconPlus({ size = 18, className }: P) {
  return base(size, className, <><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></>);
}
export function IconCheck({ size = 18, className }: P) {
  return base(size, className, <path d="M4.5 12.5l5 5 10-11" />);
}
export function IconX({ size = 18, className }: P) {
  return base(size, className, <><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></>);
}
export function IconBag({ size = 18, className }: P) {
  return base(size, className, <><path d="M5.5 8h13l-1 12.5h-11L5.5 8z" /><path d="M9 8V6.5a3 3 0 0 1 6 0V8" /></>);
}
export function IconCalendar({ size = 18, className }: P) {
  return base(size, className, <><rect x="4" y="5.5" width="16" height="15" rx="2.5" /><line x1="4" y1="10" x2="20" y2="10" /><line x1="9" y1="3" x2="9" y2="7" /><line x1="15" y1="3" x2="15" y2="7" /></>);
}
export function IconLeaf({ size = 18, className }: P) {
  return base(size, className, <><path d="M5 19C5 9 12 4 20 4c0 8-5 15-15 15z" /><path d="M5 19c3-5 7-9 11-11" /></>);
}
export function IconFlame({ size = 18, className }: P) {
  return base(size, className, <path d="M12 3s5.5 4.5 5.5 9.5a5.5 5.5 0 0 1-11 0C6.5 9 9 6.5 9 6.5c.5 1.5 1.5 2.5 1.5 2.5C11 7 11.5 4.5 12 3z" />);
}
export function IconReceipt({ size = 18, className }: P) {
  return base(size, className, <><path d="M6 3.5h12V20l-3-2-3 2-3-2-3 2V3.5z" /><line x1="9.5" y1="8.5" x2="14.5" y2="8.5" /><line x1="9.5" y1="12" x2="14.5" y2="12" /></>);
}
export function IconSpark({ size = 18, className }: P) {
  return base(size, className, <><path d="M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.4L12 3z" /><path d="M18.5 15.5l.9 2.6 2.6.9-2.6.9-.9 2.6-.9-2.6-2.6-.9 2.6-.9.9-2.6z" /></>);
}
