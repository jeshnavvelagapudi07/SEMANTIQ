import React, { useEffect, useState } from 'react';
import { UserRole, EvidenceChunk, DocumentItem } from '../../types';
import { semantiqApi } from '../../services/api';
import {
  FileText,
  Search,
  Shield,
  Tag,
  CheckCircle2,
  ExternalLink,
  BookOpen,
  Layers
} from 'lucide-react';

interface EvidencePanelProps {
  currentRole: UserRole;
  onNavigateToReasoning: (presetQuery: string) => void;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ currentRole, onNavigateToReasoning }) => {
  const [evidenceList, setEvidenceList] = useState<EvidenceChunk[]>([]);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceChunk | null>(null);
  const [parentDocument, setParentDocument] = useState<DocumentItem | null>(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEvidence();
  }, [currentRole, search]);

  const loadEvidence = async () => {
    try {
      setLoading(true);
      const res = await semantiqApi.listEvidence(currentRole, search || undefined);
      setEvidenceList(res.evidence);
      if (res.evidence.length > 0 && !selectedEvidence) {
        selectEvidence(res.evidence[0]);
      }
    } catch (err) {
      console.error('Failed to load evidence:', err);
    } finally {
      setLoading(false);
    }
  };

  const selectEvidence = async (ev: EvidenceChunk) => {
    setSelectedEvidence(ev);
    try {
      const res = await semantiqApi.getEvidenceDetail(ev.id, currentRole);
      setParentDocument(res.parent_document || null);
    } catch (err) {
      console.error('Failed to load evidence parent doc:', err);
      setParentDocument(null);
    }
  };

  return (
    <div className="h-[calc(100vh-110px)] flex bg-slate-950 overflow-hidden">
      {/* Left List of Evidence Chunks */}
      <div className="w-96 border-r border-slate-800 bg-slate-925 flex flex-col">
        <div className="p-4 border-b border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-xs font-mono uppercase text-white flex items-center space-x-1.5">
              <FileText className="w-4 h-4 text-indigo-400" />
              <span>Evidence Index ({evidenceList.length})</span>
            </h3>
            <span className="text-[10px] font-mono text-slate-400">Clearance: {currentRole}</span>
          </div>

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search evidence excerpts or doc IDs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-slate-800/50">
          {loading ? (
            <div className="p-8 text-center text-xs text-slate-400 font-mono">Loading evidence index...</div>
          ) : evidenceList.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400 font-mono">No authorized evidence found.</div>
          ) : (
            evidenceList.map((ev) => {
              const isSelected = selectedEvidence?.id === ev.id;
              return (
                <button
                  key={ev.id}
                  onClick={() => selectEvidence(ev)}
                  className={`w-full text-left p-3.5 transition-colors flex flex-col space-y-1.5 ${
                    isSelected ? 'bg-indigo-950/40 border-l-2 border-indigo-500' : 'hover:bg-slate-900/60'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-indigo-300">{ev.id}</span>
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                      ev.classification === 'RESTRICTED' ? 'bg-rose-500/20 text-rose-300' :
                      ev.classification === 'CONFIDENTIAL' ? 'bg-amber-500/20 text-amber-300' :
                      'bg-slate-800 text-slate-300'
                    }`}>
                      {ev.classification}
                    </span>
                  </div>
                  <div className="text-xs text-white font-medium truncate">{ev.doc_title}</div>
                  <div className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">{ev.excerpt}</div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Right Main Detail Pane */}
      <div className="flex-1 bg-slate-950 overflow-y-auto p-8">
        {selectedEvidence ? (
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Header Card */}
            <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      {selectedEvidence.id}
                    </span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      Source: {selectedEvidence.source_type}
                    </span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      {selectedEvidence.classification}
                    </span>
                  </div>
                  <h1 className="text-xl font-bold text-white mt-2">{selectedEvidence.doc_title}</h1>
                  <p className="text-xs font-mono text-slate-400 mt-0.5">Parent Document ID: {selectedEvidence.doc_id}</p>
                </div>

                <button
                  onClick={() => onNavigateToReasoning(`What evidence from ${selectedEvidence.doc_id} applies to active manufacturing incidents?`)}
                  className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-all shadow-md shadow-indigo-600/20 flex items-center space-x-1.5"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Query with this Evidence</span>
                </button>
              </div>

              {/* Verified Grounded Excerpt */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                <div className="text-[11px] font-mono uppercase font-semibold text-indigo-400 flex items-center space-x-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Indexed Grounding Excerpt</span>
                </div>
                <p className="text-sm text-slate-200 leading-relaxed font-sans">{selectedEvidence.excerpt}</p>
              </div>

              {/* Relevant Entities */}
              {selectedEvidence.relevant_entities.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-mono uppercase text-slate-400">Associated Graph Entities:</div>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedEvidence.relevant_entities.map((entId) => (
                      <span key={entId} className="px-2 py-1 rounded bg-slate-800 border border-slate-700 font-mono text-xs text-indigo-200">
                        {entId}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Complete Parent Document (if authorized) */}
            {parentDocument && (
              <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div>
                    <h3 className="font-bold text-sm text-white">{parentDocument.title}</h3>
                    <div className="text-[11px] font-mono text-slate-400">
                      Doc Code: {parentDocument.id} • Version: {parentDocument.version} • Owner: {parentDocument.owner_team}
                    </div>
                  </div>
                  <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-300">
                    Full Document Record
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto">
                  {parentDocument.content}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
            Select an evidence item from the index to view details.
          </div>
        )}
      </div>
    </div>
  );
};
