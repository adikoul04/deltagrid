import { useEffect } from 'react';

import { useSimulationStore } from '../store/simulationStore';

export function useSimulationLoop() {
  const running = useSimulationStore((s) => s.running);
  const mode = useSimulationStore((s) => s.mode);
  const liveRefreshSeconds = useSimulationStore((s) => s.liveRefreshSeconds);
  const replayRefreshSeconds = useSimulationStore((s) => s.replayRefreshSeconds);
  const expiry = useSimulationStore((s) => s.expiry);
  const tick = useSimulationStore((s) => s.tick);

  useEffect(() => {
    const stopSimulation = () => {
      const state = useSimulationStore.getState();
      if (state.running) {
        state.pause();
      }
    };

    window.addEventListener('pagehide', stopSimulation);
    return () => {
      window.removeEventListener('pagehide', stopSimulation);
      stopSimulation();
    };
  }, []);

  useEffect(() => {
    if (!expiry || !running) return;

    void tick();

    const intervalMs = (mode === 'live' ? liveRefreshSeconds : replayRefreshSeconds) * 1000;
    const id = window.setInterval(() => {
      void tick();
    }, intervalMs);

    return () => window.clearInterval(id);
  }, [running, mode, liveRefreshSeconds, replayRefreshSeconds, expiry, tick]);
}
