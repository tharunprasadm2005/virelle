import { Component, type ReactNode } from 'react';

/** Catches render crashes per-route so one bad page never blanks the app. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, { error: string }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { error: '' };
  }

  static getDerivedStateFromError(e: unknown): { error: string } {
    return { error: e instanceof Error ? e.message : 'Something went wrong' };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="card">
          <h2>Something broke on this page</h2>
          <p className="muted small">{this.state.error}</p>
          <p><button onClick={() => window.location.reload()}>Reload page</button></p>
        </div>
      );
    }
    return this.props.children;
  }
}
