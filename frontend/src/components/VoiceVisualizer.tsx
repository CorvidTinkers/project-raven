'use client';

import React from 'react';

interface VoiceVisualizerProps {
  isActive: boolean;
  isMuted: boolean;
  amplitude?: number;
}

const VoiceVisualizer: React.FC<VoiceVisualizerProps> = ({ isActive, isMuted, amplitude = 0 }) => {
  return (
    <div className={`w-48 h-48 rounded-full flex items-center justify-center transition-all duration-300 ${
      isActive 
        ? isMuted ? 'bg-slate-700/50 scale-90' : 'bg-blue-500/10 scale-110 shadow-[0_0_50px_rgba(59,130,246,0.2)]'
        : 'bg-slate-800'
    }`}
    style={{
      transform: isActive && !isMuted ? `scale(${1 + amplitude * 0.5})` : undefined
    }}>
      <div className="flex items-center gap-1.5 h-16">
        {[...Array(12)].map((_, i) => (
          <div
            key={i}
            className={`w-1.5 rounded-full transition-all duration-75 ${
              isActive && !isMuted 
                ? 'bg-blue-400' 
                : 'bg-slate-600'
            }`}
            style={{
              height: isActive && !isMuted 
                ? `${Math.max(15, amplitude * 100 * (0.5 + Math.random() * 0.5))}%` 
                : '8px',
            }}
          />
        ))}
      </div>
    </div>
  );
};


export default VoiceVisualizer;
