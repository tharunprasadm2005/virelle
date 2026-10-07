import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';

interface Toast {
  id: number;
  msg: string;
  ok: boolean;
}

const Ctx = createContext<(msg: string, ok?: boolean) => void>(() => {});

export function useToast(): (msg: string, ok?: boolean) => void {
  return useContext(Ctx);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);
  const push = useCallback((msg: string, ok = true) => {
    const id = ++idRef.current;
    setToasts((t) => [...t, { id, msg, ok }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500);
  }, []);
  return (
    <Ctx.Provider value={push}>
      {children}
      <div aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} id="tf-toast" className={'show ' + (t.ok ? 'ok' : 'err')}>
            {t.msg}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
