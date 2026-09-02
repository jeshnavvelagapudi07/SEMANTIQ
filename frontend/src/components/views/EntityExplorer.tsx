import React, { useEffect, useState } from 'react';
import { UserRole, Entity, EntityType } from '../../types';
import { semantiqApi } from '../../services/api';
import {
  Search,
  Filter,
  Cpu,
  FolderKanban,
  AlertTriangle,
  Users,
  FileCheck,
  Building2,
  GitFork,
  Sparkles,
  ArrowRight,
  Shield,
  Tag
} from 'lucide-react';

interface EntityExplorerProps {
  currentRole: UserRole;
  onNavigateToReasoning: (presetQuery: string) => void;
  onNavigateToPathVisualizer: (sourceId: string, targetId: string) => void;
}

const TYPE_ICONS: Record<EntityType, React.FC<{ className?: string }>> = {
  project: FolderKanban,
  system: Cpu,
  incident: AlertTriangle,
  team: Users,
  employee: Users,
  document: FileCheck,
  policy: FileCheck,
  customer: Building2,
};

export const EntityExplorer: React.FC<EntityExplorerProps> = ({
  currentRole,
  onNavigateToReasoning,
  onNavigateToPathVisualizer,
}) => {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [connectedRels, setConnectedRels] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEntities();
  }, [currentRole, selectedType, search]);

  const loadEntities = async () => {
    try {
      setLoading(true);
      const res = await semantiqApi.listEntities(
        currentRole,
        selectedType === 'ALL' ? undefined : selectedType,
        search || undefined
      );
      setEntities(res.entities);
      if (res.entities.length > 0 && !selectedEntity) {
        selectEntity(res.entities[0]);
      }
    } catch (err) {
      console.error('Failed to load entities:', err);
    } finally {
      setLoading(false);
    }
  };

  const selectEntity = async (entity: Entity) => {
    setSelectedEntity(entity);
    try {
      const res = await semantiqApi.getEntity(entity.id, currentRole);
      setConnectedRels(res.connected_relationships || []);
    } catch (err) {
      console.error('Failed to load entity detail:', err);
      setConnectedRels([]);
    }
  };

  return (
    <div className="h-[calc(100vh-110px)] flex bg-slate-950 overflow-hidden">
      {/* Left Sidebar: Entity List */}
      <div className="w-96 border-r border-slate-800 bg-slate-925 flex flex-col">
        {/* Search & Filters */}
        <div className="p-4 border-b border-slate-800 space-y-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search entities by name or ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center space-x-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Entity Types ({entities.length})</option>
              <option value="project">Projects</option>
              <option value="system">Systems & Machinery</option>
              <option value="incident">Incidents</option>
              <option value="team">Teams</option>
              <option value="employee">Employees</option>
              <option value="policy">Policies</option>
              <option value="customer">Customers</option>
            </select>
          </div>
        </div>

        {/* List Items */}
        <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60">
          {loading ? (
            <div className="p-8 text-center text-xs text-slate-400 font-mono">Loading entities...</div>
          ) : entities.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400 font-mono">No matching entities found.</div>
          ) : (
            entities.map((e) => {
              const Icon = TYPE_ICONS[e.type] || Cpu;
              const isSelected = selectedEntity?.id === e.id;
              return (
                <button
                  key={e.id}
                  onClick={() => selectEntity(e)}
                  className={`w-full text-left p-3.5 transition-colors flex items-start space-x-3 ${
                    isSelected ? 'bg-indigo-950/40 border-l-2 border-indigo-500' : 'hover:bg-slate-900/60'
                  }`}
                >
                  <div className={`p-2 rounded-lg bg-slate-900 border border-slate-800 mt-0.5 ${
                    isSelected ? 'text-indigo-400 border-indigo-500/30' : 'text-slate-400'
                  }`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs text-white truncate">{e.name}</span>
                      <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                        {e.classification}
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-slate-400 mt-0.5">{e.id}</div>
                    <div className="text-[11px] text-slate-400 truncate mt-1">{e.description}</div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Right Main Pane: Deep Entity Profile */}
      <div className="flex-1 bg-slate-950 overflow-y-auto p-8">
        {selectedEntity ? (
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Header Card */}
            <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono uppercase font-semibold px-2.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      {selectedEntity.type}
                    </span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      {selectedEntity.classification}
                    </span>
                  </div>
                  <h1 className="text-2xl font-bold text-white mt-2">{selectedEntity.name}</h1>
                  <p className="text-xs font-mono text-slate-400 mt-0.5">Entity ID: {selectedEntity.id}</p>
                </div>

                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => onNavigateToReasoning(`Why is ${selectedEntity.name} connected to active plant operations?`)}
                    className="flex items-center space-x-1.5 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-all shadow-md shadow-indigo-600/20"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Reason About Entity</span>
                  </button>
                  
                  {selectedEntity.id !== 'INC-104' && (
                    <button
                      onClick={() => onNavigateToPathVisualizer(selectedEntity.id, 'INC-104')}
                      className="flex items-center space-x-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition-all border border-slate-700"
                    >
                      <GitFork className="w-3.5 h-3.5 text-rose-400" />
                      <span>Trace to Incident 104</span>
                    </button>
                  )}
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-slate-800">
                <p className="text-xs text-slate-300 leading-relaxed">{selectedEntity.description}</p>
              </div>

              <div className="grid grid-cols-3 gap-3 mt-4">
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <div className="text-[10px] font-mono text-slate-400 uppercase">Owner Team</div>
                  <div className="text-xs font-medium text-emerald-300 mt-1">{selectedEntity.owner_team || 'General Operations'}</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <div className="text-[10px] font-mono text-slate-400 uppercase">Access Tier</div>
                  <div className="text-xs font-mono font-medium text-indigo-300 mt-1">{selectedEntity.classification} Clearance</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <div className="text-[10px] font-mono text-slate-400 uppercase">Connected Edges</div>
                  <div className="text-xs font-mono font-medium text-cyan-300 mt-1">{connectedRels.length} Relationships</div>
                </div>
              </div>
            </div>

            {/* Custom Properties */}
            {selectedEntity.properties && Object.keys(selectedEntity.properties).length > 0 && (
              <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800">
                <h3 className="text-xs font-mono uppercase font-semibold text-slate-400 tracking-wider mb-3">
                  Technical Specifications & Properties
                </h3>
                <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                  {Object.entries(selectedEntity.properties).map(([k, v]) => (
                    <div key={k} className="flex justify-between p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80">
                      <span className="text-slate-400">{k}:</span>
                      <span className="text-slate-200 font-medium">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Connected Knowledge Graph Relationships */}
            <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-mono uppercase font-semibold text-slate-400 tracking-wider">
                  Connected Graph Relationships ({connectedRels.length})
                </h3>
                <span className="text-[11px] text-slate-400 font-mono">1-Hop Traversal</span>
              </div>

              <div className="grid grid-cols-1 gap-2.5">
                {connectedRels.map((r) => {
                  const isSource = r.source_id === selectedEntity.id;
                  const otherId = isSource ? r.target_id : r.source_id;
                  return (
                    <div
                      key={r.id}
                      className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-slate-700 flex items-center justify-between transition-colors"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="px-2 py-1 rounded bg-indigo-950/60 border border-indigo-500/30 text-indigo-300 font-mono text-[10px] font-semibold">
                          {r.relation_type}
                        </div>
                        <div>
                          <div className="text-xs font-medium text-white flex items-center space-x-2">
                            <span>{isSource ? 'Directly connects to' : 'Referenced by'}</span>
                            <span className="font-mono text-indigo-300 font-bold">{otherId}</span>
                          </div>
                          {r.description && <div className="text-[11px] text-slate-400 mt-0.5">{r.description}</div>}
                        </div>
                      </div>

                      <button
                        onClick={() => onNavigateToPathVisualizer(selectedEntity.id, otherId)}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 text-xs font-mono flex items-center space-x-1 transition-colors"
                      >
                        <span>Visualize Path</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
            Select an entity from the directory to inspect.
          </div>
        )}
      </div>
    </div>
  );
};
