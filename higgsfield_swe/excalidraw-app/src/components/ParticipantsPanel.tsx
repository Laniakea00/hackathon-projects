import React from "react";
import type { Participant } from "../types/collab";
import "./ParticipantsPanel.css";

type Props = {
  participants: Participant[];
  onToggleAI?: (id: string, active: boolean) => void;
  onSetAILevel?: (id: string, level: number) => void;
};

export const ParticipantsPanel: React.FC<Props> = ({ participants, onToggleAI, onSetAILevel }) => {
  return (
    <aside className="participants-panel">
      <header>Участники</header>
      <div className="participants-list">
        {participants.map((p) => (
          <div key={p.id} className={`participant ${p.active ? "active" : "inactive"}`}>
            <span className="dot" style={{ background: p.color }} />
            <div className="meta">
              <div className="name">
                {p.name} {p.isAI ? "🤖" : ""}
              </div>
              <div className="status">{p.active ? "online" : "idle"}</div>
            </div>
            {p.isAI && (
              <div className="ai-controls">
                <label>
                  <input
                    type="checkbox"
                    defaultChecked={p.active}
                    onChange={(e) => onToggleAI?.(p.id, e.target.checked)}
                  />
                  Вкл
                </label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  defaultValue={1}
                  onChange={(e) => onSetAILevel?.(p.id, Number(e.target.value))}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
};
