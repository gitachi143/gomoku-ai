const BOARD_SIZE = 15;
const EMPTY = " ";
const BLACK = "X";
const WHITE = "O";

// existing DOM refs
const sideSelect = document.getElementById("sideSelect");
const newBtn = document.getElementById("newBtn");
const startBoardBtn = document.getElementById("startBoardBtn");
const statusEl = document.getElementById("status");
const boardEl = document.getElementById("board");
const boardFrameEl = document.getElementById("boardFrame");
const intersectionsEl = document.getElementById("intersections");
const coordColsEl = document.getElementById("coordCols");
const coordRowsEl = document.getElementById("coordRows");

// new DOM refs for agent selection and game mode
const modeSelect = document.getElementById("modeSelect");
const agentSelect = document.getElementById("agentSelect");
const blackAgentSelect = document.getElementById("blackAgentSelect");
const whiteAgentSelect = document.getElementById("whiteAgentSelect");
const sideField = document.getElementById("sideField");
const agentField = document.getElementById("agentField");
const blackAgentField = document.getElementById("blackAgentField");
const whiteAgentField = document.getElementById("whiteAgentField");
const stopBtn = document.getElementById("stopBtn");

// game state
let grid = [];
let toMove = BLACK;
let gameOver = false;
let winner = null;
let isDraw = false;
let lastMove = null;
/** @type {Set<string> | null} */
let winningCells = null;

// mode state
let currentMode = "human_vs_ai";
let aiLoopRunning = false;
let aiLoopAbort = false;

function emptyGrid() {
  const g = [];
  for (let r = 0; r < BOARD_SIZE; r++) {
    const row = [];
    for (let c = 0; c < BOARD_SIZE; c++) row.push(EMPTY);
    g.push(row);
  }
  return g;
}

function cloneGrid(g) {
  return g.map((row) => row.slice());
}

function setStatus(text) {
  statusEl.textContent = text;
}

function humanSideStone() {
  return sideSelect.value === "white" ? WHITE : BLACK;
}

function deriveLastMove(prev, next, humanCoord) {
  const added = [];
  for (let r = 0; r < BOARD_SIZE; r++) {
    for (let c = 0; c < BOARD_SIZE; c++) {
      const p = prev?.[r]?.[c] ?? EMPTY;
      if (p === EMPTY && next[r][c] !== EMPTY) added.push([r, c]);
    }
  }
  if (added.length === 0) return null;
  if (added.length === 1) return { r: added[0][0], c: added[0][1] };
  if (humanCoord) {
    const [hr, hc] = humanCoord;
    const other = added.find(([r, c]) => r !== hr || c !== hc);
    if (other) return { r: other[0], c: other[1] };
  }
  const last = added[added.length - 1];
  return { r: last[0], c: last[1] };
}

function findWinningSegment(g, stone) {
  const dirs = [
    [1, 0],
    [0, 1],
    [1, 1],
    [1, -1],
  ];
  for (let r = 0; r < BOARD_SIZE; r++) {
    for (let c = 0; c < BOARD_SIZE; c++) {
      if (g[r][c] !== stone) continue;
      for (const [dr, dc] of dirs) {
        const pr = r - dr;
        const pc = c - dc;
        if (
          pr >= 0 &&
          pr < BOARD_SIZE &&
          pc >= 0 &&
          pc < BOARD_SIZE &&
          g[pr][pc] === stone
        ) {
          continue;
        }
        const line = [];
        let nr = r;
        let nc = c;
        while (
          nr >= 0 &&
          nr < BOARD_SIZE &&
          nc >= 0 &&
          nc < BOARD_SIZE &&
          g[nr][nc] === stone
        ) {
          line.push([nr, nc]);
          nr += dr;
          nc += dc;
        }
        if (line.length >= 5) return line;
      }
    }
  }
  return null;
}

function computeWinningHighlight(g, w, draw) {
  if (!draw && w && w !== EMPTY) {
    const seg = findWinningSegment(g, w);
    if (seg) {
      return new Set(seg.map(([rr, cc]) => `${rr},${cc}`));
    }
  }
  return null;
}

function buildCoords() {
  const letters = "ABCDEFGHIJKLMNO";
  coordColsEl.innerHTML = "";
  for (let c = 0; c < BOARD_SIZE; c++) {
    const el = document.createElement("span");
    el.className = "coord-cell";
    el.textContent = letters[c];
    el.style.left = `calc(var(--pad) + ${c} * var(--gap))`;
    el.style.top = "50%";
    coordColsEl.appendChild(el);
  }
  coordRowsEl.innerHTML = "";
  for (let r = 0; r < BOARD_SIZE; r++) {
    const el = document.createElement("span");
    el.className = "coord-cell";
    el.textContent = String(r + 1);
    el.style.left = "50%";
    el.style.top = `calc(var(--pad) + ${r} * var(--gap))`;
    coordRowsEl.appendChild(el);
  }
}

function intersectionPositionStyle(r, c) {
  return {
    left: `calc(var(--pad) + ${c} * var(--gap))`,
    top: `calc(var(--pad) + ${r} * var(--gap))`,
  };
}

function renderBoard() {
  intersectionsEl.innerHTML = "";

  for (let r = 0; r < BOARD_SIZE; r++) {
    for (let c = 0; c < BOARD_SIZE; c++) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "intersection";
      btn.dataset.row = String(r);
      btn.dataset.col = String(c);
      const pos = intersectionPositionStyle(r, c);
      btn.style.left = pos.left;
      btn.style.top = pos.top;

      const preview = document.createElement("span");
      preview.className = "stone preview";
      if (humanSideStone() === BLACK) preview.classList.add("black");
      else preview.classList.add("white");
      preview.setAttribute("aria-hidden", "true");

      const stone = document.createElement("span");
      stone.className = "stone";
      stone.setAttribute("aria-hidden", "true");

      const lastMarker = document.createElement("span");
      lastMarker.className = "last-marker";
      lastMarker.setAttribute("aria-hidden", "true");

      const v = grid[r][c];
      if (v === BLACK) {
        stone.classList.add("black", "is-visible");
      } else if (v === WHITE) {
        stone.classList.add("white", "is-visible");
      }

      if (lastMove && lastMove.r === r && lastMove.c === c && v !== EMPTY) {
        btn.classList.add("is-last");
      }

      if (winningCells && winningCells.has(`${r},${c}`)) {
        btn.classList.add("is-winning");
      }

      // disable clicks in ai-vs-ai mode or when it's not human's turn
      const canClick =
        currentMode === "human_vs_ai" &&
        !gameOver &&
        toMove === humanSideStone() &&
        v === EMPTY;
      btn.disabled = !canClick;

      btn.appendChild(preview);
      btn.appendChild(stone);
      btn.appendChild(lastMarker);

      btn.addEventListener("click", () => handleCellClick(r, c));

      intersectionsEl.appendChild(btn);
    }
  }
}

function setBoardWaiting(waiting) {
  boardEl.classList.toggle("board--waiting", waiting);
}

function isGridEmpty(g) {
  return g.every((row) => row.every((cell) => cell === EMPTY));
}

function updateStatusLine() {
  const idle = gameOver && !winner && !isDraw && isGridEmpty(grid);
  const ended = gameOver && (winner || isDraw);
  statusEl.classList.toggle("status--gameover", !!ended);

  if (idle) {
    setStatus("Choose a side, then start on the board.");
    return;
  }
  if (gameOver) {
    if (winner === BLACK) setStatus("Black wins.");
    else if (winner === WHITE) setStatus("White wins.");
    else if (isDraw) setStatus("Draw.");
    else setStatus("Game over.");
    return;
  }

  const side = toMove === BLACK ? "Black" : "White";

  // ai-vs-ai status
  if (currentMode === "ai_vs_ai") {
    if (aiLoopRunning) {
      setStatus(`${side} thinking...`);
    } else {
      setStatus(`AI vs AI paused. ${side} to move.`);
    }
    return;
  }

  // human-vs-ai status
  const yours = toMove === humanSideStone();
  setStatus(yours ? `Your turn (${side}).` : `AI thinking (${side} to move)...`);
}

function applyServerState(data, opts = {}) {
  const prev = opts.prevGrid ?? null;
  const humanCoord = opts.humanMove ?? null;

  grid = data.grid;
  toMove = data.to_move;
  gameOver = !!data.game_over;
  winner = data.winner ?? null;
  isDraw = !!data.is_draw;

  lastMove = deriveLastMove(prev, data.grid, humanCoord);
  winningCells = computeWinningHighlight(grid, winner, isDraw);
  renderBoard();
  updateStatusLine();
}

// fetch available agents from backend and populate dropdowns
async function loadAgents() {
  try {
    const res = await fetch("/api/agents");
    const data = await res.json();
    const names = data.agents || [];
    for (const sel of [agentSelect, blackAgentSelect, whiteAgentSelect]) {
      sel.innerHTML = "";
      for (const name of names) {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        sel.appendChild(opt);
      }
    }
    // default to alphabeta if available
    if (names.includes("alphabeta")) {
      agentSelect.value = "alphabeta";
      blackAgentSelect.value = "alphabeta";
      whiteAgentSelect.value = "alphabeta";
    }
  } catch (e) {
    // fallback: add alphabeta as only option
    for (const sel of [agentSelect, blackAgentSelect, whiteAgentSelect]) {
      sel.innerHTML = '<option value="alphabeta">alphabeta</option>';
    }
  }
}

// show/hide controls based on selected mode
function updateModeControls() {
  currentMode = modeSelect.value;
  const isHvA = currentMode === "human_vs_ai";
  sideField.style.display = isHvA ? "" : "none";
  agentField.style.display = isHvA ? "" : "none";
  blackAgentField.style.display = isHvA ? "none" : "";
  whiteAgentField.style.display = isHvA ? "none" : "";
}

async function apiNew() {
  // stop any running ai-vs-ai loop
  aiLoopAbort = true;

  setStatus("Starting...");
  gameOver = true;
  lastMove = null;
  winningCells = null;
  renderBoard();

  currentMode = modeSelect.value;

  let url;
  if (currentMode === "ai_vs_ai") {
    const ba = blackAgentSelect.value;
    const wa = whiteAgentSelect.value;
    url = `/api/new?mode=ai_vs_ai&black_agent=${encodeURIComponent(ba)}&white_agent=${encodeURIComponent(wa)}`;
  } else {
    const side = sideSelect.value;
    const agent = agentSelect.value;
    url = `/api/new?side=${encodeURIComponent(side)}&agent=${encodeURIComponent(agent)}`;
  }

  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) {
    setStatus(data.error || "Failed to start game.");
    grid = emptyGrid();
    gameOver = true;
    lastMove = null;
    winningCells = null;
    renderBoard();
    statusEl.classList.remove("status--gameover");
    return;
  }
  boardFrameEl.classList.add("board--has-session");
  applyServerState(data, { prevGrid: emptyGrid() });

  // start auto-play loop for ai-vs-ai
  if (currentMode === "ai_vs_ai" && !gameOver) {
    startAiLoop();
  }
}

// ai-vs-ai: request one move at a time with delay between moves
async function startAiLoop() {
  aiLoopRunning = true;
  aiLoopAbort = false;
  stopBtn.style.display = "";

  const delay = (ms) => new Promise((r) => setTimeout(r, ms));

  while (!gameOver && !aiLoopAbort) {
    await delay(500);
    if (aiLoopAbort) break;

    const prevGrid = cloneGrid(grid);
    setBoardWaiting(true);

    const res = await fetch("/api/ai_move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        grid: grid,
        black_agent: blackAgentSelect.value,
        white_agent: whiteAgentSelect.value,
      }),
    });
    const data = await res.json();
    setBoardWaiting(false);

    if (!res.ok) {
      setStatus(data.error || "AI move failed.");
      break;
    }

    applyServerState(data, { prevGrid });
  }

  aiLoopRunning = false;
  stopBtn.style.display = "none";
}

async function handleCellClick(row, col) {
  // no clicks in ai-vs-ai mode
  if (currentMode === "ai_vs_ai") return;

  const r = row;
  const c = col;
  if (gameOver || toMove !== humanSideStone()) return;
  if (grid[r][c] !== EMPTY) return;

  const preMoveGrid = cloneGrid(grid);
  const preMoveToMove = toMove;
  const preMoveLastMove = lastMove ? { r: lastMove.r, c: lastMove.c } : null;
  const preMoveWinningCells = winningCells;

  const humanStone = humanSideStone();
  grid = cloneGrid(preMoveGrid);
  grid[r][c] = humanStone;
  lastMove = { r, c };
  toMove = humanStone === BLACK ? WHITE : BLACK;
  winningCells = null;

  setStatus("Sending move...");
  setBoardWaiting(true);
  renderBoard();

  const res = await fetch("/api/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      grid: preMoveGrid,
      human_side: sideSelect.value,
      to_move: preMoveToMove,
      move: [r, c],
      agent: agentSelect.value,
    }),
  });
  const data = await res.json();
  setBoardWaiting(false);

  if (!res.ok) {
    grid = preMoveGrid;
    lastMove = preMoveLastMove;
    winningCells = preMoveWinningCells;
    toMove = preMoveToMove;
    setStatus(data.error || "Move failed.");
    renderBoard();
    return;
  }
  applyServerState(data, { prevGrid: preMoveGrid, humanMove: [r, c] });
}

// event listeners
modeSelect.addEventListener("change", updateModeControls);

newBtn.addEventListener("click", () => {
  apiNew();
});

startBoardBtn.addEventListener("click", () => {
  apiNew();
});

stopBtn.addEventListener("click", () => {
  aiLoopAbort = true;
});

// init
buildCoords();
grid = emptyGrid();
gameOver = true;
lastMove = null;
winningCells = null;
renderBoard();
updateStatusLine();
loadAgents();
