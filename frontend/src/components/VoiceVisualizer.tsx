'use client';

import React, { useMemo, useRef } from 'react';

interface VoiceVisualizerProps {
  isActive: boolean;
  isMuted: boolean;
  amplitude?: number;
  isSpeaking?: boolean;
}

// Pre-computed static offsets per bar — set once, never regenerated
const BAR_COUNT = 14;
const BAR_OFFSETS = Array.from({ length: BAR_COUNT }, (_, i) => {
  // Sine wave base shape across bars — center bars taller
  return 0.3 + Math.sin((i / (BAR_COUNT - 1)) * Math.PI) * 0.7;
});

const VoiceVisualizer: React.FC<VoiceVisualizerProps> = ({
  isActive,
  isMuted,
  amplitude = 0,
  isSpeaking = false,
}) => {
  const scale = isActive && !isMuted ? 1 + amplitude * 0.3 : 1;

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: '100%', height: '100%' }}
    >
      {/* Outer glow ring — only when speaking */}
      {isSpeaking && !isMuted && (
        <div
          className="absolute rounded-full border border-blue-500/30 animate-ping"
          style={{
            width: '70%',
            height: '70%',
            animationDuration: '1.5s',
          }}
        />
      )}

      {/* Main orb */}
      <div
        className={`relative flex items-center justify-center rounded-full transition-all duration-200 ${
          isActive && !isMuted
            ? 'bg-blue-500/10 shadow-[0_0_60px_rgba(59,130,246,0.25)]'
            : 'bg-slate-800/60'
        }`}
        style={{
          width: '55%',
          height: '55%',
          transform: `scale(${scale})`,
          transition: 'transform 80ms ease-out',
        }}
      >
        {/* Waveform bars */}
        <div className="flex items-center gap-1 h-14">
          {BAR_OFFSETS.map((offset, i) => {
            const barHeight = isActive && !isMuted
              ? Math.max(12, amplitude * 100 * offset)
              : 6;

            return (
              <div
                key={i}
                className={`rounded-full transition-all ${
                  isActive && !isMuted ? 'bg-blue-400' : 'bg-slate-600'
                }`}
                style={{
                  width: '3px',
                  height: `${barHeight}%`,
                  // CSS animation for idle state breathing
                  animation: !isActive
                    ? `breathe 2.${i % 4}s ease-in-out infinite alternate`
                    : undefined,
                  animationDelay: `${i * 80}ms`,
                  transition: 'height 80ms ease-out',
                }}
              />
            );
          })}
        </div>

        {/* Muted indicator */}
        {isMuted && (
          <div className="absolute inset-0 flex items-center justify-center rounded-full bg-slate-900/60">
            <span className="text-slate-500 text-xs font-bold uppercase tracking-widest">Muted</span>
          </div>
        )}
      </div>

      <style>{`
        @keyframes breathe {
          from { height: 6px; }
          to { height: 18px; }
        }
      `}</style>
    </div>
  );
};

export default VoiceVisualizer;
