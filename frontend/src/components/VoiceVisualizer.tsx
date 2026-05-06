'use client';

import React from 'react';

interface VoiceVisualizerProps {
  isActive: boolean;
  isMuted: boolean;
}

const VoiceVisualizer: React.FC<VoiceVisualizerProps> = ({ isActive, isMuted }) => {
  return (
    <div className={`w-48 h-48 rounded-full flex items-center justify-center transition-all duration-500 ${
      isActive 
        ? isMuted ? 'bg-slate-700/50 scale-90' : 'bg-blue-500/10 scale-110 shadow-[0_0_50px_rgba(59,130,246,0.2)]'
        : 'bg-slate-800'
    }`}>
      <div className="flex items-center gap-1.5 h-16">
        {[...Array(8)].map((_, i) => (
          <div
            key={i}
            className={`w-1.5 rounded-full transition-all duration-300 ${
              isActive && !isMuted 
                ? 'bg-blue-400 animate-pulse' 
                : 'bg-slate-600 h-2'
            }`}
            style={{
              height: isActive && !isMuted ? `${20 + (i * 10) % 80}%` : '8px',
              animationDelay: `${i * 0.1}s`
            }}
          />
        ))}
      </div>
    </div>
  );
};

export default VoiceVisualizer;
