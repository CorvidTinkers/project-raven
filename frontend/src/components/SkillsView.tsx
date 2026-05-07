'use client';

import React from 'react';
import { Target } from 'lucide-react';

interface Skill {
  skill: string;
  match_level: 'high' | 'medium' | 'low';
  reason?: string;
}

interface SkillsViewProps {
  skills: Skill[];
}

export default function SkillsView({ skills }: SkillsViewProps) {
  return (
    <div className="w-full animate-in fade-in zoom-in-95 duration-700">
      <div className="flex items-center gap-2 mb-6">
        <Target className="text-blue-400" size={20} />
        <h3 className="text-lg font-bold text-white uppercase tracking-tighter">Skill Alignment Matrix</h3>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
        {skills.map((s, i) => (
          <div key={i} className={`group p-5 rounded-2xl border transition-all duration-300 hover:shadow-lg ${
            s.match_level === 'high' ? 'bg-green-500/5 border-green-500/20 hover:border-green-500/40 text-green-400' :
            s.match_level === 'medium' ? 'bg-yellow-500/5 border-yellow-500/20 hover:border-yellow-500/40 text-yellow-400' :
            'bg-slate-800/40 border-slate-700 text-slate-400'
          }`}>
            <div className="flex items-center justify-between mb-2">
              <span className="font-black text-sm uppercase tracking-tight">{s.skill}</span>
              <div className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest ${
                s.match_level === 'high' ? 'bg-green-500/20' :
                s.match_level === 'medium' ? 'bg-yellow-500/20' :
                'bg-slate-700'
              }`}>
                {s.match_level}
              </div>
            </div>
            <p className="text-[11px] opacity-70 leading-relaxed font-medium">
              {s.reason || 'Primary match based on core competencies found in resume.'}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
