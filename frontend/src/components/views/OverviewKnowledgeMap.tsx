import React, { useEffect, useState, useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Node,
  Edge,
  Position,
  Handle
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { UserRole, EntityType, ClassificationLevel } from '../../types';
import { semantiqApi } from '../../services/api';
import {
  Layers,
  Search,
  Filter,
  Shield,
  Activity,
  AlertTriangle,
  Cpu,
  FolderKanban,
  Users,
  FileText,
  FileCheck,
  Building2,
  X,
  ArrowRight,
  ExternalLink,
  Sparkles
} from 'lucide-react';

interface OverviewKnowledgeMapProps {
  currentRole: UserRole;
  onNavigateToReasoning: (presetQuery: string) => void;
}

const TYPE_CONFIG: Record<EntityType, { label: string; color: string; bg: string; border: string; icon: React.FC<{ className?: string }> }> = {
  project: { label: 'Project', color: 'text-indigo-400', bg: 'bg-indigo-950/60', border: 'border-indigo-500/40', icon: FolderKanban },
  system: { label: 'System', color: 'text-cyan-400', bg: 'bg-cyan-950/60', border: 'border-cyan-500/40', icon: Cpu },
  incident: { label: 'Incident', color: 'text-rose-400', bg: 'bg-rose-950/60', border: 'border-rose-500/40', icon: AlertTriangle },
  team: { label: 'Team', color: 'text-emerald-400', bg: 'bg-emerald-950/60', border: 'border-emerald-500/40', icon: Users },
  employee: { label: 'Employee', color: 'text-amber-400', bg: 'bg-amber-950/60', border: 'border-amber-500/40', icon: Users },
  document: { label: 'Document', color: 'text-blue-400', bg: 'bg-blue-950/60', border: 'border-blue-500/40', icon: FileText },
  policy: { label: 'Policy', color: 'text-purple-400', bg: 'bg-purple-950/60', border: 'border-purple-500/40', icon: FileCheck },
  customer: { label: 'Customer', color: 'text-orange-400', bg: 'bg-orange-950/60', border: 'border-orange-500/40', icon: Building2 },
};

const CustomGraphNode = ({ data }: { data: any }) => {
  const config = TYPE_CONFIG[data.type as EntityType] || TYPE_CONFIG.system;
  const Icon = config.icon;

  return (
    <div
      className={`px-3 py-2 rounded-xl border backdrop-blur-md transition-all shadow-lg min-w-[160px] max-w-[220px] ${config.bg} ${config.border} ${
        data.isSelected ? 'ring-2 ring-indigo-400 shadow-indigo-500/20 scale-105' : 'hover:border-slate-400'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-500 !w-2 !h-2" />
      
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center space-x-1.5">
          <Icon className={`w-3.5 h-3.5 ${config.color}`} />
          <span className={`text-[10px] uppercase font-mono tracking-wider font-semibold ${config.color}`}>
            {config.label}
          </span>
        </div>
        <span className={`text-[9px] px-1 py-0.2 rounded font-mono ${
          data.classification === 'RESTRICTED' ? 'bg-rose-500/30 text-rose-300' :
          data.classification === 'CONFIDENTIAL' ? 'bg-amber-500/30 text-amber-300' :
          'bg-slate-700/50 text-slate-300'
        }`}>
          {data.classification}
        </span>
      </div>

      <div className="font-semibold text-xs text-white truncate">{data.name}</div>
      <div className="text-[10px] text-slate-400 font-mono truncate">{data.id}</div>

      <Handle type="source" position={Position.Bottom} className="!bg-slate-500 !w-2 !h-2" />
    </div>
  );
};

const nodeTypes = {
  customNode: CustomGraphNode,
};

export const OverviewKnowledgeMap: React.FC<OverviewKnowledgeMapProps> = ({ currentRole, onNavigateToReasoning }) => {
  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[]; stats: any } | null>(null);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    loadGraph();
  }, [currentRole]);

  const loadGraph = async () => {
    try {
      setLoading(true);
      const data = await semantiqApi.getGraph(currentRole);
      setGraphData(data);

      // Arrange nodes in visual concentric grid by type
      const typeGroups: Record<string, any[]> = {};
      data.nodes.forEach((n: any) => {
        typeGroups[n.type] = typeGroups[n.type] || [];
        typeGroups[n.type].push(n);
      });

      const typeOrder = ['project', 'system', 'incident', 'policy', 'team', 'employee', 'customer'];
      const flowNodes: Node[] = [];

      typeOrder.forEach((t, typeIdx) => {
        const group = typeGroups[t] || [];
        group.forEach((node, nodeIdx) => {
          const col = nodeIdx % 4;
          const row = Math.floor(nodeIdx / 4);
          const x = 80 + col * 240 + (typeIdx % 2) * 50;
          const y = 80 + typeIdx * 200 + row * 100;

          flowNodes.push({
            id: node.id,
            type: 'customNode',
            position: { x, y },
            data: {
              ...node,
              isSelected: false,
            },
          });
        });
      });

      const flowEdges: Edge[] = data.edges.map((e: any) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.relation_type,
        labelStyle: { fill: '#94A3B8', fontSize: 9, fontFamily: 'monospace', fontWeight: 500 },
        labelBgStyle: { fill: '#0F172A', fillOpacity: 0.85 },
        labelBgPadding: [4, 2],
        labelBgBorderRadius: 4,
        style: { stroke: '#334155', strokeWidth: 1.2 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 14,
          height: 14,
          color: '#475569',
        },
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (err) {
      console.error('Failed to load graph:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = (_: any, node: Node) => {
    setSelectedNode(node.data);
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          isSelected: n.id === node.id,
        },
      }))
    );
  };

  const filteredNodes = useMemo(() => {
    return nodes.filter((n) => {
      const data = n.data as any;
      const matchesSearch =
        !searchQuery ||
        (data?.name && data.name.toLowerCase().includes(searchQuery.toLowerCase())) ||
        n.id.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesType = typeFilter === 'ALL' || (data && data.type === typeFilter);
      return matchesSearch && matchesType;
    });
  }, [nodes, searchQuery, typeFilter]);

  return (
    <div className="h-[calc(100vh-110px)] flex flex-col bg-slate-950">
      {/* Top Executive Stats Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 p-4 border-b border-slate-800 bg-slate-925/50">
        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-[11px] text-slate-400 font-mono uppercase">Total Nodes</div>
          <div className="text-xl font-bold text-white font-mono mt-0.5">{graphData?.stats?.total_nodes || 0}</div>
          <div className="text-[10px] text-emerald-400 mt-0.5">Authorized for {currentRole}</div>
        </div>

        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-[11px] text-slate-400 font-mono uppercase">Relationships</div>
          <div className="text-xl font-bold text-white font-mono mt-0.5">{graphData?.stats?.total_edges || 0}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Cross-domain edges</div>
        </div>

        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-[11px] text-slate-400 font-mono uppercase">Active Projects</div>
          <div className="text-xl font-bold text-indigo-300 font-mono mt-0.5">
            {graphData?.stats?.entity_types?.project || 8}
          </div>
          <div className="text-[10px] text-indigo-400 mt-0.5">Turbine & aero lines</div>
        </div>

        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-[11px] text-slate-400 font-mono uppercase">Critical Systems</div>
          <div className="text-xl font-bold text-cyan-300 font-mono mt-0.5">
            {graphData?.stats?.entity_types?.system || 12}
          </div>
          <div className="text-[10px] text-cyan-400 mt-0.5">5-axis CNC & SCADA</div>
        </div>

        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-[11px] text-slate-400 font-mono uppercase">Open Incidents</div>
          <div className="text-xl font-bold text-rose-300 font-mono mt-0.5">
            {graphData?.stats?.entity_types?.incident || 10}
          </div>
          <div className="text-[10px] text-rose-400 mt-0.5">Incident 104 High Sev</div>
        </div>

        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-[11px] text-slate-400 font-mono uppercase">Graph Density</div>
          <div className="text-xl font-bold text-slate-200 font-mono mt-0.5">
            {graphData?.stats?.density || 0.045}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Multi-hop connected</div>
        </div>
      </div>

      {/* Main Graph Canvas Area */}
      <div className="flex-1 relative flex">
        <div className="flex-1 h-full relative">
          {/* Controls Overlay */}
          <div className="absolute top-4 left-4 z-10 flex items-center space-x-3 bg-slate-900/90 p-2 rounded-xl border border-slate-800 shadow-xl backdrop-blur">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search node name or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-indigo-500 w-52"
              />
            </div>

            <div className="flex items-center space-x-1 border-l border-slate-800 pl-3">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Entity Types</option>
                {Object.keys(TYPE_CONFIG).map((t) => (
                  <option key={t} value={t}>
                    {TYPE_CONFIG[t as EntityType].label}s
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* React Flow Viewport */}
          <ReactFlow
            nodes={filteredNodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            onNodeClick={handleNodeClick}
            fitView
            minZoom={0.2}
            maxZoom={1.8}
          >
            <Background color="#1E293B" gap={20} size={1} />
            <Controls className="!bg-slate-900 !border-slate-800" />
          </ReactFlow>
        </div>

        {/* Selected Entity Inspector Side Panel */}
        {selectedNode && (
          <div className="w-80 border-l border-slate-800 bg-slate-925 p-5 overflow-y-auto z-20 flex flex-col justify-between animate-in slide-in-from-right duration-200">
            <div>
              <div className="flex items-start justify-between pb-3 border-b border-slate-800">
                <div>
                  <span className={`text-[10px] uppercase font-mono font-semibold px-2 py-0.5 rounded ${
                    TYPE_CONFIG[selectedNode.type as EntityType]?.bg || 'bg-slate-800'
                  } ${TYPE_CONFIG[selectedNode.type as EntityType]?.color || 'text-slate-300'}`}>
                    {selectedNode.type}
                  </span>
                  <h3 className="font-bold text-base text-white mt-1.5">{selectedNode.name}</h3>
                  <div className="text-xs font-mono text-slate-400">{selectedNode.id}</div>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="py-4 space-y-3">
                <div>
                  <div className="text-[11px] font-mono uppercase text-slate-400">Description</div>
                  <p className="text-xs text-slate-300 mt-0.5 leading-relaxed">{selectedNode.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2">
                  <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                    <div className="text-[10px] font-mono text-slate-400">Security Clearance</div>
                    <div className="text-xs font-mono font-medium text-indigo-300 mt-0.5">
                      {selectedNode.classification}
                    </div>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                    <div className="text-[10px] font-mono text-slate-400">Owner Team</div>
                    <div className="text-xs font-medium text-emerald-300 mt-0.5 truncate">
                      {selectedNode.owner_team || 'General'}
                    </div>
                  </div>
                </div>

                {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                  <div className="pt-2">
                    <div className="text-[11px] font-mono uppercase text-slate-400 mb-1.5">Properties</div>
                    <div className="space-y-1 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 font-mono text-xs">
                      {Object.entries(selectedNode.properties).map(([k, v]) => (
                        <div key={k} className="flex justify-between py-0.5 border-b border-slate-800/50 last:border-0">
                          <span className="text-slate-400">{k}:</span>
                          <span className="text-slate-200 font-medium">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Action CTA */}
            <div className="pt-4 border-t border-slate-800">
              <button
                onClick={() => onNavigateToReasoning(`Analyze dependencies and impact for ${selectedNode.name} (${selectedNode.id})`)}
                className="w-full flex items-center justify-center space-x-2 py-2.5 px-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-all shadow-lg shadow-indigo-600/20"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Reason About This Entity</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
