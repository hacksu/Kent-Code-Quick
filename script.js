"use strict";

/* ---------- Word list ---------- */

// Possible answers. Guesses in this list are accepted instantly; other guesses
// are checked against an online dictionary (and accepted if it's unreachable).
const WORDS = `
about above abuse actor acute admit adopt adult after again agent agree ahead alarm album
alert alien align alike alive allow alone along alter amber amend among angel anger angle
angry apart apple apply arena argue arise armor array arrow aside asset audio audit avoid
award aware awful bacon badge badly baker basic basin basis batch beach beard beast began
begin begun being below bench berry birth black blade blame bland blank blast blaze bleak
blend bless blind block blood bloom board boast bonus boost booth bound brain brake brand
brass brave bread break breed brick bride brief bring brink broad broke brown brush build
built bunch burst buyer cabin cable camel candy canoe cargo carry catch cause cedar chain
chair chalk champ chant chaos charm chart chase cheap cheat check cheek cheer chess chest
chick chief child chill china choir chord chose civic civil claim clash class clean clear
clerk click cliff climb cling clock close cloth cloud clown coach coast cocoa coral couch
could count court cover crack craft crane crash crate crawl crazy cream creek crest crime
crisp cross crowd crown crude cruel crush crust curve cycle daily dairy dance dealt death
debut decay delay delta dense depth derby devil diary dirty ditch dizzy dodge doing donor
doubt dough dozen draft drain drama drank drawn dread dream dress dried drift drill drink
drive drone drove dwarf eager eagle early earth easel eaten ebony eight elbow elder elect
elite empty enemy enjoy enter entry equal equip erase error erupt essay event every exact
exist extra fable faint fairy faith false fancy fatal fault feast fence ferry fever fiber
field fiery fifth fifty fight final flame flash fleet flesh float flock flood floor flour
fluid flute focus foggy force forge forth forty forum found frame frank fraud fresh front
frost froze fruit fully funny fuzzy gauge ghost giant given glare glass gleam glide globe
gloom glory glove going grace grade grain grand grant grape graph grasp grass grave great
greed green greet grief grill grind groan groom gross group grove growl grown guard guess
guest guide guild guilt habit happy harsh haste hatch haunt heart heavy hedge hello hence
hinge hobby honey honor horse hotel house hover human humor hurry ideal image imply index
inner input irony issue ivory jelly jewel joint jolly judge juice juicy jumbo knife knock
known label labor large laser later laugh layer learn lease least leave legal lemon level
lever light limit linen liver local lodge logic loose lover lower loyal lucky lunar lunch
magic major maker mango manor maple march match mayor meant medal media melon mercy merge
merit merry metal meter might minor minus mirth model moist money month moral motor mound
mount mouse mouth movie muddy music naive nasty naval nerve never newly night ninja noble
noise north novel nurse nylon ocean offer often olive onion opera orbit order organ other
otter ought ounce outer owner oxide ozone paint panel panic paper party pasta paste patch
pause peace peach pearl pedal penny perch phase phone photo piano piece pilot pinch pitch
pixel pizza place plain plane plant plate plaza plead pluck plumb plume point polar porch
pound power press price pride prime print prior prize probe proof proud prove proxy pulse
punch pupil puppy purse quack queen query quest queue quick quiet quilt quite quota quote
radar radio raise rally ranch range rapid ratio raven reach react ready realm rebel refer
reign relax relay reply rider ridge rifle right rigid rinse risky rival river roast robin
robot rocky rouge rough round route royal rugby ruler rural rusty saint salad salon sauce
scale scare scarf scene scent scope score scout scrap sense serve setup seven shade shake
shall shame shape share shark sharp sheep sheet shelf shell shift shine shiny shirt shock
shore short shout sight silky silly since sixth skill skirt skull slate sleep slice slide
slope smart smell smile smoke snack snake solar solid solve sorry sound south space spare
spark speak spear speed spell spend spice spicy spike spine spoke spoon sport spray squad
stack staff stage stain stair stake stale stamp stand stark start state steak steam steel
steep stern stick stiff still sting stock stone stood stool store storm story stove strap
straw strip stuck study stuff style sugar suite sunny super surge swamp swear sweat sweep
sweet swept swift swing sword syrup table taste teach tease teeth tempo thank theft theme
there thick thief thing think third thorn those three threw throw thumb tiger tight timer
tired title toast today token topic torch total touch tough tower toxic trace track trade
trail train trait trash treat trend trial tribe trick tried troop truck truly trunk trust
truth tulip tumor twice twist ultra uncle under union unity until upper upset urban usage
usual utter vague valid value valve vapor vault venue verse video vigor vinyl viral virus
visit vital vivid vocal vodka voice voter wagon waste watch water weary weave wedge weird
whale wheat wheel where which while whirl white whole whose widow width wince witch woman
world worry worse worst worth would wound woven wrath wreck wrist write wrong wrote yacht
yearn yeast yield young youth zebra
`.trim().split(/\s+/).filter((w) => /^[a-z]{5}$/.test(w));

const WORD_SET = new Set(WORDS);
const ROWS = 6;
const COLS = 5;
const FLIP_MS = 250;              // matches the CSS flip animation duration
const EPOCH = new Date(2021, 5, 19); // day 0 of the daily puzzle
const STORAGE_GAME = "wordle-game";
const STORAGE_STATS = "wordle-stats";

/* ---------- Storage helpers ---------- */

function load(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function save(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable, so play on without persistence */
  }
}

/* ---------- Game state ---------- */

function todayIndex() {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((today - EPOCH) / 86400000);
}

function dailyWord(dayIndex) {
  // Step through the list with a large prime so consecutive days feel random.
  return WORDS[(dayIndex * 7919) % WORDS.length];
}

let state;
let stats = load(STORAGE_STATS, {
  played: 0,
  wins: 0,
  streak: 0,
  maxStreak: 0,
  dist: [0, 0, 0, 0, 0, 0],
});
let current = "";     // letters typed in the active row
let busy = false;     // blocks input while validating / animating

function newDailyState() {
  const day = todayIndex();
  return { mode: "daily", day, solution: dailyWord(day), guesses: [], status: "playing" };
}

function newPracticeState() {
  let word;
  do {
    word = WORDS[Math.floor(Math.random() * WORDS.length)];
  } while (state && word === state.solution);
  return { mode: "practice", solution: word, guesses: [], status: "playing" };
}

function saveState() {
  // Only the daily puzzle is persisted; practice games are throwaway.
  if (state.mode === "daily") save(STORAGE_GAME, state);
}

/* ---------- Evaluation ---------- */

function evaluate(guess, solution) {
  const result = Array(COLS).fill("absent");
  const remaining = {};

  for (let i = 0; i < COLS; i++) {
    if (guess[i] === solution[i]) {
      result[i] = "correct";
    } else {
      remaining[solution[i]] = (remaining[solution[i]] || 0) + 1;
    }
  }
  for (let i = 0; i < COLS; i++) {
    if (result[i] !== "correct" && remaining[guess[i]] > 0) {
      result[i] = "present";
      remaining[guess[i]]--;
    }
  }
  return result;
}

async function isValidWord(word) {
  if (WORD_SET.has(word)) return true;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 3000);
  try {
    const res = await fetch(
      `https://api.dictionaryapi.dev/api/v2/entries/en/${word}`,
      { signal: controller.signal }
    );
    return res.ok;
  } catch {
    return true; // offline or API down, so don't punish the player
  } finally {
    clearTimeout(timer);
  }
}

/* ---------- DOM ---------- */

const boardEl = document.getElementById("board");
const keyboardEl = document.getElementById("keyboard");
const toastsEl = document.getElementById("toasts");
const keyEls = {};

const KEY_ROWS = ["qwertyuiop", "asdfghjkl", "ZxcvbnmB"]; // Z = Enter, B = Backspace

function buildBoard() {
  boardEl.innerHTML = "";
  for (let r = 0; r < ROWS; r++) {
    const row = document.createElement("div");
    row.className = "row";
    for (let c = 0; c < COLS; c++) {
      const tile = document.createElement("div");
      tile.className = "tile";
      row.appendChild(tile);
    }
    boardEl.appendChild(row);
  }
}

function buildKeyboard() {
  KEY_ROWS.forEach((letters, i) => {
    const row = document.createElement("div");
    row.className = "key-row";
    if (i === 1) row.appendChild(spacer());
    for (const ch of letters) {
      const btn = document.createElement("button");
      btn.className = "key";
      if (ch === "Z") {
        btn.textContent = "Enter";
        btn.dataset.key = "Enter";
        btn.classList.add("wide");
      } else if (ch === "B") {
        btn.textContent = "<<";
        btn.dataset.key = "Backspace";
        btn.classList.add("wide");
        btn.setAttribute("aria-label", "Backspace");
      } else {
        btn.textContent = ch;
        btn.dataset.key = ch;
        keyEls[ch] = btn;
      }
      row.appendChild(btn);
    }
    if (i === 1) row.appendChild(spacer());
    keyboardEl.appendChild(row);
  });

  keyboardEl.addEventListener("click", (e) => {
    const btn = e.target.closest(".key");
    if (!btn) return;
    btn.blur();
    handleKey(btn.dataset.key);
  });
}

function spacer() {
  const s = document.createElement("div");
  s.className = "key-spacer";
  return s;
}

function rowEl(r) {
  return boardEl.children[r];
}

function tileEl(r, c) {
  return rowEl(r).children[c];
}

function renderCurrentRow() {
  const r = state.guesses.length;
  if (r >= ROWS) return;
  for (let c = 0; c < COLS; c++) {
    const tile = tileEl(r, c);
    const letter = current[c] || "";
    if (tile.textContent !== letter) {
      tile.textContent = letter;
      tile.classList.toggle("filled", !!letter);
    }
  }
}

const RANK = { absent: 1, present: 2, correct: 3 };

function colorKey(letter, status) {
  const el = keyEls[letter];
  const prev = el.dataset.status;
  if (!prev || RANK[status] > RANK[prev]) {
    if (prev) el.classList.remove(prev);
    el.classList.add(status);
    el.dataset.status = status;
  }
}

function paintRow(r, guess, result) {
  for (let c = 0; c < COLS; c++) {
    const tile = tileEl(r, c);
    tile.textContent = guess[c];
    tile.className = `tile ${result[c]}`;
    colorKey(guess[c], result[c]);
  }
}

function revealRow(r, guess, result) {
  return new Promise((resolve) => {
    for (let c = 0; c < COLS; c++) {
      const tile = tileEl(r, c);
      setTimeout(() => {
        tile.classList.add("flip");
        tile.addEventListener("animationend", function half() {
          tile.removeEventListener("animationend", half);
          tile.className = `tile ${result[c]} flip-out`;
          tile.addEventListener("animationend", function done() {
            tile.removeEventListener("animationend", done);
            tile.classList.remove("flip-out");
            if (c === COLS - 1) resolve();
          });
        });
      }, c * FLIP_MS * 1.2);
    }
  }).then(() => {
    for (let c = 0; c < COLS; c++) colorKey(guess[c], result[c]);
  });
}

function bounceRow(r) {
  for (let c = 0; c < COLS; c++) {
    const tile = tileEl(r, c);
    setTimeout(() => tile.classList.add("bounce"), c * 100);
  }
}

function shakeRow(r) {
  const row = rowEl(r);
  row.classList.remove("shake");
  void row.offsetWidth; // restart animation
  row.classList.add("shake");
  row.addEventListener("animationend", () => row.classList.remove("shake"), { once: true });
}

function toast(message, duration = 1200) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  toastsEl.prepend(el);
  if (duration === Infinity) return;
  setTimeout(() => {
    el.classList.add("fade");
    el.addEventListener("transitionend", () => el.remove(), { once: true });
  }, duration);
}

function clearToasts() {
  toastsEl.innerHTML = "";
}

/* ---------- Input ---------- */

function handleKey(key) {
  if (busy || state.status !== "playing") return;
  if (document.querySelector(".modal:not(.hidden)")) return;

  if (key === "Enter") {
    submitGuess();
  } else if (key === "Backspace") {
    current = current.slice(0, -1);
    renderCurrentRow();
  } else if (/^[a-z]$/i.test(key) && current.length < COLS) {
    current += key.toLowerCase();
    renderCurrentRow();
  }
}

async function submitGuess() {
  const r = state.guesses.length;
  if (current.length < COLS) {
    shakeRow(r);
    toast("Not enough letters");
    return;
  }

  busy = true;
  const guess = current;
  const valid = await isValidWord(guess);
  if (!valid) {
    busy = false;
    shakeRow(r);
    toast("Not in word list");
    return;
  }

  const result = evaluate(guess, state.solution);
  state.guesses.push(guess);
  current = "";

  const won = guess === state.solution;
  if (won) state.status = "won";
  else if (state.guesses.length === ROWS) state.status = "lost";
  saveState();

  await revealRow(r, guess, result);
  busy = false;

  if (state.status !== "playing") endGame();
}

const WIN_MESSAGES = ["Genius", "Magnificent", "Impressive", "Splendid", "Great", "Phew"];

function endGame() {
  const won = state.status === "won";
  recordStats(won, state.guesses.length);

  if (won) {
    bounceRow(state.guesses.length - 1);
    toast(WIN_MESSAGES[state.guesses.length - 1], 2000);
  } else {
    toast(state.solution.toUpperCase(), Infinity);
  }
  setTimeout(() => openModal("stats-modal"), 2200);
}

/* ---------- Stats ---------- */

function recordStats(won, tries) {
  if (state.mode !== "daily") return; // practice games don't affect stats
  stats.played++;
  if (won) {
    stats.wins++;
    stats.streak++;
    stats.maxStreak = Math.max(stats.maxStreak, stats.streak);
    stats.dist[tries - 1]++;
  } else {
    stats.streak = 0;
  }
  save(STORAGE_STATS, stats);
}

function renderStats() {
  document.getElementById("stat-played").textContent = stats.played;
  document.getElementById("stat-win").textContent =
    stats.played ? Math.round((stats.wins / stats.played) * 100) : 0;
  document.getElementById("stat-streak").textContent = stats.streak;
  document.getElementById("stat-max").textContent = stats.maxStreak;

  const distEl = document.getElementById("distribution");
  distEl.innerHTML = "";
  const max = Math.max(1, ...stats.dist);
  stats.dist.forEach((count, i) => {
    const row = document.createElement("div");
    row.className = "dist-row";
    const label = document.createElement("div");
    label.textContent = i + 1;
    const bar = document.createElement("div");
    bar.className = "dist-bar";
    if (state.status === "won" && state.guesses.length === i + 1) {
      bar.classList.add("highlight");
    }
    bar.style.width = `${(count / max) * 100}%`;
    bar.textContent = count;
    row.append(label, bar);
    distEl.appendChild(row);
  });

  const over = state.status !== "playing";
  document.getElementById("stats-footer").classList.toggle("hidden", !over);
  document.querySelector(".countdown").classList.toggle("hidden", state.mode !== "daily");
}

let countdownTimer = null;

function startCountdown() {
  const el = document.getElementById("countdown");
  const tick = () => {
    const now = new Date();
    const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    const diff = Math.max(0, midnight - now);
    const h = String(Math.floor(diff / 3600000)).padStart(2, "0");
    const m = String(Math.floor((diff % 3600000) / 60000)).padStart(2, "0");
    const s = String(Math.floor((diff % 60000) / 1000)).padStart(2, "0");
    el.textContent = `${h}:${m}:${s}`;
  };
  tick();
  clearInterval(countdownTimer);
  countdownTimer = setInterval(tick, 1000);
}

function shareText() {
  const emoji = { correct: "🟩", present: "🟨", absent: "⬛" };
  const score = state.status === "won" ? state.guesses.length : "X";
  const title = state.mode === "daily" ? `Wordle ${state.day}` : "Wordle (practice)";
  const grid = state.guesses
    .map((g) => evaluate(g, state.solution).map((s) => emoji[s]).join(""))
    .join("\n");
  return `${title} ${score}/${ROWS}\n\n${grid}`;
}

async function share() {
  const text = shareText();
  try {
    await navigator.clipboard.writeText(text);
    toast("Copied results to clipboard");
  } catch {
    toast("Couldn't copy results");
  }
}

/* ---------- Modals ---------- */

function openModal(id) {
  if (id === "stats-modal") {
    renderStats();
    startCountdown();
  }
  document.getElementById(id).classList.remove("hidden");
}

function closeModal(modal) {
  modal.classList.add("hidden");
  if (modal.id === "stats-modal") clearInterval(countdownTimer);
}

document.querySelectorAll(".modal").forEach((modal) => {
  modal.addEventListener("click", (e) => {
    if (e.target === modal || e.target.closest(".close-btn")) closeModal(modal);
  });
});

/* ---------- Setup ---------- */

function restore() {
  buildBoard();
  current = "";
  Object.values(keyEls).forEach((el) => {
    el.classList.remove("correct", "present", "absent");
    delete el.dataset.status;
  });
  state.guesses.forEach((g, r) => paintRow(r, g, evaluate(g, state.solution)));
  if (state.status === "lost") toast(state.solution.toUpperCase(), Infinity);
}

function startPractice() {
  if (busy) return;
  clearToasts();
  state = newPracticeState();
  saveState();
  restore();
  toast("Practice game: new random word");
}

document.addEventListener("keydown", (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.key === "Escape") {
    document.querySelectorAll(".modal:not(.hidden)").forEach(closeModal);
    return;
  }
  if (e.key === "Enter" || e.key === "Backspace" || /^[a-z]$/i.test(e.key)) {
    e.preventDefault();
    handleKey(e.key);
  }
});

document.getElementById("help-btn").addEventListener("click", () => openModal("help-modal"));
document.getElementById("stats-btn").addEventListener("click", () => openModal("stats-modal"));
document.getElementById("new-btn").addEventListener("click", (e) => {
  e.currentTarget.blur();
  startPractice();
});
document.getElementById("share-btn").addEventListener("click", share);

function init() {
  buildKeyboard();

  const saved = load(STORAGE_GAME, null);
  const today = todayIndex();
  if (saved && saved.mode === "daily" && saved.day === today) {
    state = saved;
  } else {
    state = newDailyState();
    saveState();
  }
  restore();

  if (load(STORAGE_STATS, null) === null && state.guesses.length === 0) {
    openModal("help-modal");
  }
}

init();
