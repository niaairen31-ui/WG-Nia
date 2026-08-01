<script>
  /* TICKET-0057. THE graph. One component, one engine, one contract.

     The primitive NEVER fetches and NEVER writes. It renders nodes and
     edges and reports interactions through callbacks. Every network call
     belongs to a consumer -- which keeps canon writes on the consumer side
     of the seam, where the sanctioned endpoints already are.

     Capability is declared by the PRESENCE of a callback, not by a boolean
     axis: no `onMoveNode` means no drag, no `onConnect` means no
     select-to-connect, no `onDeleteEdge`/`onEdgeClick` means edges are not
     clickable, no `onNodeClick`/`onNodeDblClick` means a click/dbl-click
     reports nothing beyond the existing connect/select behaviour. Booleans
     would have had to be invented in pairs nothing sets independently; a
     callback is evidenced by its consumer or it is absent.

     `layout` is the FIRST boolean-shaped axis this contract admits
     (TICKET-0058, BRIEF-0058-c) -- and only because two consumers now set
     it differently: Lieux/review stay 'positional' (stored coordinates,
     circular fallback); the relations consumer's global/ego graph has no
     stored coordinates at all and needs 'force' (TICKET-0057 E1's
     no-axis-unexercised rule is satisfied the moment a second consumer
     exists, not before).

     No scoped style block. This component renders INSIDE the legacy
     iframe document, and Svelte's scoped CSS is injected into the shell's
     head, where it would never reach. Styling is by SVG attributes
     referencing the legacy CSS variables, plus legacy class names. */

  let {
    nodes = [],
    edges = [],
    dashedKinds = [],
    layout = 'positional',
    onConnect = null,
    onDeleteEdge = null,
    onEdgeClick = null,
    onMoveNode = null,
    onNodeClick = null,
    onNodeDblClick = null,
  } = $props();

  const GRAPH_W = 960;
  const GRAPH_H = 480;
  const NODE_R = 20;
  const DRAG_THRESHOLD = 5;
  const FORCE_ITERATIONS = 300;

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

  /** Plain, library-free force layout (RECON-0058-a M1(b)): Coulomb-like
   *  repulsion (k²/d) between every node pair, a spring pulling each edge
   *  toward its rest length k, and a weak centring force, fixed at 300
   *  iterations with linear cooling. M1 measured this exact method
   *  (repulsion + spring-to-rest-length + centring, 300 iterations,
   *  960x480) as sub-millisecond and legible at the pilot's scale (7
   *  nodes/8 edges) and still well under the 2000ms gate at 10x synthetic
   *  scale -- its result file does not record literal tuning constants
   *  beyond iteration count and viewport, so `k` follows the standard
   *  Fruchterman-Reingold characteristic distance (sqrt(area/n)) rather
   *  than an invented figure. Initial placement is a deterministic circle
   *  (not Math.random) so identical input always lays out identically;
   *  Math.random is used only to break an exact coincidence of two nodes. */
  function forcePlace(ns, es) {
    const n = ns.length;
    if (n === 0) return [];
    const cx = GRAPH_W / 2, cy = GRAPH_H / 2;
    const k = Math.sqrt((GRAPH_W * GRAPH_H) / n);
    const pos = ns.map((node, i) => {
      const angle = (2 * Math.PI * i) / n;
      const r = Math.min(cx, cy) * 0.5;
      return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
    });
    const idOf = new Map(ns.map((node, i) => [node.id, i]));
    const pairs = es
      .map(e => [idOf.get(e.entity_a_id), idOf.get(e.entity_b_id)])
      .filter(([a, b]) => a != null && b != null && a !== b);

    for (let iter = 0; iter < FORCE_ITERATIONS; iter++) {
      const disp = pos.map(() => ({ x: 0, y: 0 }));
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          let dx = pos[i].x - pos[j].x, dy = pos[i].y - pos[j].y;
          let d2 = dx * dx + dy * dy;
          if (d2 < 0.01) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; d2 = dx * dx + dy * dy; }
          const d = Math.sqrt(d2);
          const force = (k * k) / d;
          disp[i].x += (dx / d) * force; disp[i].y += (dy / d) * force;
          disp[j].x -= (dx / d) * force; disp[j].y -= (dy / d) * force;
        }
      }
      for (const [a, b] of pairs) {
        const dx = pos[a].x - pos[b].x, dy = pos[a].y - pos[b].y;
        const d = Math.max(Math.sqrt(dx * dx + dy * dy), 0.01);
        const force = (d * d) / k;
        disp[a].x -= (dx / d) * force; disp[a].y -= (dy / d) * force;
        disp[b].x += (dx / d) * force; disp[b].y += (dy / d) * force;
      }
      for (let i = 0; i < n; i++) {
        disp[i].x += (cx - pos[i].x) * 0.01;
        disp[i].y += (cy - pos[i].y) * 0.01;
      }
      const temp = Math.max(k * 0.1 * (1 - iter / FORCE_ITERATIONS), 0.01);
      for (let i = 0; i < n; i++) {
        const dl = Math.max(Math.hypot(disp[i].x, disp[i].y), 0.01);
        pos[i].x += (disp[i].x / dl) * Math.min(dl, temp);
        pos[i].y += (disp[i].y / dl) * Math.min(dl, temp);
        pos[i].x = Math.min(GRAPH_W - NODE_R, Math.max(NODE_R, pos[i].x));
        pos[i].y = Math.min(GRAPH_H - NODE_R, Math.max(NODE_R, pos[i].y));
      }
    }
    return ns.map((node, i) => ({ ...node, x: pos[i].x, y: pos[i].y }));
  }

  let selectedNodeId = $state(null);
  let dragOverride = $state(null); // { nodeId, x, y } while a drag is in progress (positional layout only)

  let placed = $derived.by(() => {
    if (layout === 'force') return forcePlace(nodes, edges);
    const base = autoPlace(nodes);
    if (!dragOverride) return base;
    return base.map(n => (n.id === dragOverride.nodeId ? { ...n, x: dragOverride.x, y: dragOverride.y } : n));
  });

  let nodeMap = $derived(Object.fromEntries(placed.map(n => [n.id, n])));

  // Zoom/pan (force layout only, TICKET-0058 M2 PORT — the primitive's
  // positional consumers have never needed it; M1's 10x legibility caveat
  // is exactly why the force consumer does).
  let zoomScale = $state(1);
  let panX = $state(0), panY = $state(0);
  let viewBox = $derived(
    layout === 'force'
      ? `${panX.toFixed(1)} ${panY.toFixed(1)} ${(GRAPH_W / zoomScale).toFixed(1)} ${(GRAPH_H / zoomScale).toFixed(1)}`
      : `0 0 ${GRAPH_W} ${GRAPH_H}`
  );

  function handleWheel(e) {
    if (layout !== 'force') return;
    e.preventDefault();
    const rect = e.currentTarget.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / rect.width;
    const my = (e.clientY - rect.top) / rect.height;
    const oldW = GRAPH_W / zoomScale, oldH = GRAPH_H / zoomScale;
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    zoomScale = Math.min(Math.max(zoomScale * factor, 0.25), 6);
    const newW = GRAPH_W / zoomScale, newH = GRAPH_H / zoomScale;
    panX += (oldW - newW) * mx;
    panY += (oldH - newH) * my;
  }

  let panDrag = null;
  function handleCanvasMouseDown(e) {
    if (layout !== 'force') return;
    const rect = e.currentTarget.getBoundingClientRect();
    const view = e.currentTarget.ownerDocument.defaultView;
    panDrag = {
      clientX0: e.clientX, clientY0: e.clientY, panX0: panX, panY0: panY,
      scaleX: (GRAPH_W / zoomScale) / rect.width, scaleY: (GRAPH_H / zoomScale) / rect.height,
      moved: false, view,
    };
    view.addEventListener('mousemove', handlePanMove, { passive: true });
    view.addEventListener('mouseup', handlePanUp);
  }
  function handlePanMove(e) {
    if (!panDrag) return;
    const dx = e.clientX - panDrag.clientX0, dy = e.clientY - panDrag.clientY0;
    if (!panDrag.moved && Math.hypot(dx, dy) > DRAG_THRESHOLD) panDrag.moved = true;
    if (!panDrag.moved) return;
    panX = panDrag.panX0 - dx * panDrag.scaleX;
    panY = panDrag.panY0 - dy * panDrag.scaleY;
  }
  function handlePanUp() {
    if (!panDrag) return;
    panDrag.view.removeEventListener('mousemove', handlePanMove);
    panDrag.view.removeEventListener('mouseup', handlePanUp);
    panDrag = null;
  }

  let drag = null; // transient press state; not rendered directly, so plain

  function handleNodeMouseDown(e, nodeId) {
    e.stopPropagation();
    if (layout === 'force' || !onMoveNode) {
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

  /** onNodeClick always fires on a plain click, a notification orthogonal
   *  to the two-tap connect flow below it -- the relations consumer uses
   *  it (both modes) to populate its own info card, a concern the
   *  primitive never renders itself. */
  function handleNodeClick(nodeId) {
    if (onConnect) {
      if (!selectedNodeId) {
        selectedNodeId = nodeId;
        onNodeClick?.(nodeId);
        return;
      }
      const a = selectedNodeId;
      selectedNodeId = null;
      onNodeClick?.(nodeId);
      if (a === nodeId) return;
      // Undirected dedup: refuse to create B->A when A-B already exists.
      const dup = edges.some(e =>
        (e.entity_a_id === a && e.entity_b_id === nodeId) ||
        (e.entity_a_id === nodeId && e.entity_b_id === a)
      );
      if (dup) return;
      onConnect(a, nodeId);
      return;
    }
    selectedNodeId = (selectedNodeId === nodeId) ? null : nodeId;
    onNodeClick?.(nodeId);
  }

  function handleNodeDblClick(e, nodeId) {
    e.stopPropagation();
    onNodeDblClick?.(nodeId);
  }

  function handleEdgeClick(e, edgeId) {
    e.stopPropagation();
    if (onEdgeClick) { onEdgeClick(edgeId); return; }
    onDeleteEdge?.(edgeId);
  }

  function handleCanvasClick() {
    if (selectedNodeId) selectedNodeId = null;
  }
</script>

<svg viewBox={viewBox} width="100%" height="300"
     style="display:block; background:var(--bg)"
     onclick={handleCanvasClick}
     onwheel={layout === 'force' ? handleWheel : undefined}
     onmousedown={layout === 'force' ? handleCanvasMouseDown : undefined}>
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
          style={(onDeleteEdge || onEdgeClick) ? 'cursor:pointer' : undefined}
          onclick={(onDeleteEdge || onEdgeClick) ? (e) => handleEdgeClick(e, edge.id) : undefined}
        />
      {/if}
    {/each}
    {#each placed as node (node.id)}
      <g
        style={onMoveNode ? 'cursor:grab' : undefined}
        onmousedown={(onMoveNode || onConnect || onNodeClick) ? (e) => handleNodeMouseDown(e, node.id) : undefined}
        ondblclick={onNodeDblClick ? (e) => handleNodeDblClick(e, node.id) : undefined}
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
