import { useCallback, useRef } from "react";

/**
 * Plays an alert sound for critical notifications.
 * Uses the Web Audio API to generate a tone without external files.
 */
export function useAlertSound() {
  const audioCtxRef = useRef<AudioContext | null>(null);
  const isPlayingRef = useRef(false);

  const playAlertSound = useCallback(() => {
    if (isPlayingRef.current) return;
    isPlayingRef.current = true;

    try {
      if (!audioCtxRef.current) {
        audioCtxRef.current = new AudioContext();
      }
      const ctx = audioCtxRef.current;

      // Create a two-tone alert beep
      const playTone = (freq: number, startTime: number, duration: number) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = freq;
        osc.type = "sine";
        gain.gain.setValueAtTime(0.3, startTime);
        gain.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
        osc.start(startTime);
        osc.stop(startTime + duration);
      };

      const now = ctx.currentTime;
      // Three ascending beeps
      playTone(880, now, 0.15);
      playTone(1100, now + 0.2, 0.15);
      playTone(1320, now + 0.4, 0.2);

      setTimeout(() => {
        isPlayingRef.current = false;
      }, 700);
    } catch {
      isPlayingRef.current = false;
    }
  }, []);

  return { playAlertSound };
}
