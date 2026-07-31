<script>
  /* TICKET-0057. THE graph. One component, one engine, one contract.

     The primitive NEVER fetches and NEVER writes. It renders nodes and
     edges and reports interactions through callbacks. Every network call
     belongs to a consumer -- which keeps canon writes on the consumer side
     of the seam, where the sanctioned endpoints already are.

     Capability is declared by the PRESENCE of a callback, not by a boolean
     axis: no `onMoveNode` means no drag, no `onConnect` means no
     select-to-connect, no `onDeleteEdge` means edges are not clickable.
     Booleans would have had to be invented in pairs nothing sets
     independently; a callback is evidenced by its consumer or it is absent.

     No `<style>` block. This component renders INSIDE the legacy iframe
     document, and Svelte's scoped CSS is injected into the shell's head,
     where it would never reach. Styling is by SVG attributes referencing
     the legacy CSS variables, plus legacy class names. */

  let {
    nodes = [],
    edges = [],
    dashedKinds = [],
    onConnect = null,
    onDeleteEdge = null,
    onMoveNode = null,
  } = $props();

  const GRAPH_W = 960;
  const GRAPH_H = 480;
  const NODE_R = 20;
  const DRAG_THRESHOLD = 5;

  function autoPlace(ns) {
    const nullIds = ns.filter(n => n.coord_x == null).map(n => n.id).sort();
    const cx = GRAPH_W / 2, cy = GRAPH_H / 2;
    const r = Math.min(cx, cy) * 0.72;
    const count = nullIds.length;
    return ns.map(n => {
      if (n.coord_x != null) return { ...n, x: n.coord_x, y: n.coord_y };
      const idx = nullIds.indexOf(n.id);
      if (count === 1) return { ...n, x: cx, y: cy };
      const angle = (2 * Math.PI * idx / count) - Math.PI / 2;
      return { ...n, x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
    });
  }

  let selectedNodeId = $state(null);
  let dragOverride = $state(null); // { nodeId, x, y } while a drag is in progress

  let placed = $derived.by(() => {
    const base = autoPlace(nodes);
    if (!dragOverride) return base;
    return base.map(n => (n.id === dragOverride.nodeId ? { ...n, x: dragOverride.x, y: dragOverride.y } : n));
  });

  let nodeMap = $derived(Object.fromEntries(placed.map(n => [n.id, n])));

  let drag = null; // transient press state; not rendered directly, so plain

  function handleNodeMouseDown(e, nodeId) {
    e.stopPropagation();
    if (!onMoveNode) {
      handleNodeClick(nodeId);
      return;
    }
    const svg = e.currentTarget.ownerSVGElement;
    const rect = svg.getBoundingClientRect();
    const node = nodeMap[nodeId];
    // BRIEF-0057-a M2(b): the drag listeners go on the mounted node's OWN
    // document's window, never the bare `window` (the shell's, across the
    // frame boundary the frame's events never reach).
    const view = e.currentTarget.ownerDocument.defaultView;
    drag = {
      nodeId,
      clientX0: e.clientX, clientY0: e.clientY,
      svgX0: node ? node.x : 0, svgY0: node ? node.y : 0,
      scaleX: GRAPH_W / rect.width, scaleY: GRAPH_H / rect.height,
      moved: false,
      view,
    };
    view.addEventListener('mousemove', handleMouseMove, { passive: true });
    view.addEventListener('mouseup', handleMouseUp);
  }

  function handleMouseMove(e) {
    if (!drag) return;
    const dx = e.clientX - drag.clientX0;
    const dy = e.clientY - drag.clientY0;
    if (!drag.moved && Math.hypot(dx, dy) > DRAG_THRESHOLD) drag.moved = true;
    if (!drag.moved) return;
    dragOverride = {
      nodeId: drag.nodeId,
      x: drag.svgX0 + dx * drag.scaleX,
      y: drag.svgY0 + dy * drag.scaleY,
    };
  }

  function handleMouseUp() {
    if (!drag) return;
    const { nodeId, moved, view } = drag;
    view.removeEventListener('mousemove', handleMouseMove);
    view.removeEventListener('mouseup', handleMouseUp);
    const finalPos = dragOverride;
    drag = null;
    if (moved && finalPos) {
      onMoveNode?.(nodeId, finalPos.x, finalPos.y);
    } else {
      dragOverride = null;
      handleNodeClick(nodeId);
    }
  }

  function handleNodeClick(nodeId) {
    if (!onConnect) {
      selectedNodeId = null;
      return;
    }
    if (!selectedNodeId) {
      selectedNodeId = nodeId;
      return;
    }
    const a = selectedNodeId;
    selectedNodeId = null;
    if (a === nodeId) return;
    // Undirected dedup: refuse to create B->A when A-B already exists.
    const dup = edges.some(e =>
      (e.entity_a_id === a && e.entity_b_id === nodeId) ||
      (e.entity_a_id === nodeId && e.entity_b_id === a)
    );
    if (dup) return;
    onConnect(a, nodeId);
  }

  function handleEdgeClick(e, edgeId) {
    e.stopPropagation();
    onDeleteEdge(edgeId);
  }

  function handleCanvasClick() {
    if (selectedNodeId) selectedNodeId = null;
  }
</script>

<svg viewBox="0 0 {GRAPH_W} {GRAPH_H}" width="100%" height="300"
     style="display:block; background:var(--bg)"
     onclick={handleCanvasClick}>
  {#if nodes.length === 0}
    <text x={GRAPH_W / 2} y={GRAPH_H / 2} text-anchor="middle" fill="var(--muted)" font-size="13">Aucun nœud</text>
  {:else}
    {#each edges as edge (edge.id)}
      {@const a = nodeMap[edge.entity_a_id]}
      {@const b = nodeMap[edge.entity_b_id]}
      {#if a && b}
        <line
          x1={a.x.toFixed(1)} y1={a.y.toFixed(1)}
          x2={b.x.toFixed(1)} y2={b.y.toFixed(1)}
          stroke="var(--muted)" stroke-width="2" stroke-linecap="round"
          stroke-dasharray={dashedKinds.includes(edge.kind) ? '4' : undefined}
          style={onDeleteEdge ? 'cursor:pointer' : undefined}
          onclick={onDeleteEdge ? (e) => handleEdgeClick(e, edge.id) : undefined}
        />
      {/if}
    {/each}
    {#each placed as node (node.id)}
      <g
        style={onMoveNode ? 'cursor:grab' : undefined}
        onmousedown={(onMoveNode || onConnect) ? (e) => handleNodeMouseDown(e, node.id) : undefined}
      >
        <circle cx={node.x.toFixed(1)} cy={node.y.toFixed(1)} r={NODE_R}
          fill={node.id === selectedNodeId ? 'var(--accent)' : 'var(--card)'}
          stroke={node.id === selectedNodeId ? 'var(--accent)' : 'var(--border)'}
          stroke-width={node.id === selectedNodeId ? 2.5 : 1.5} />
        <text x={node.x.toFixed(1)} y={(node.y + NODE_R + 13).toFixed(1)}
          text-anchor="middle" fill="var(--text)" font-size="11"
          style="pointer-events:none;user-select:none">{node.name}</text>
      </g>
    {/each}
  {/if}
</svg>
