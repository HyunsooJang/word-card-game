const STORAGE_WORDS_KEY = "wordCardGame.words";
const STORAGE_CARD_COUNT_KEY = "wordCardGame.cardCount";
const STORAGE_MODE_KEY = "wordCardGame.vowelMode";
const STORAGE_START_PHASE_KEY = "wordCardGame.startPhase";
const STORAGE_BLANK_MODE_KEY = "wordCardGame.blankMode";

const LONG_VOWEL_SOUND = {
  a: "ay",
  e: "ee",
  i: "eye",
  o: "oh",
  u: "yoo",
};

const VOWELS = "aeiou";
const ALPHABET = "abcdefghijklmnopqrstuvwxyz";
const PREFERRED_VOICE_NAMES = [
  "Samantha",
  "Ava",
  "Karen",
  "Moira",
  "Nicky",
  "Google US English",
];

const wordInput = document.querySelector("#wordInput");
const cardCountInput = document.querySelector("#cardCountInput");
const vowelModeInput = document.querySelector("#vowelModeInput");
const startPhaseInput = document.querySelector("#startPhaseInput");
const blankModeInput = document.querySelector("#blankModeInput");
const ttsProviderText = document.querySelector("#ttsProviderText");
const ttsVoiceText = document.querySelector("#ttsVoiceText");
const saveWordsBtn = document.querySelector("#saveWordsBtn");
const startBtn = document.querySelector("#startBtn");
const goSetupBtn = document.querySelector("#goSetupBtn");

const setupView = document.querySelector("#setupView");
const studyView = document.querySelector("#studyView");

const remainingCount = document.querySelector("#remainingCount");
const passCount = document.querySelector("#passCount");
const failCount = document.querySelector("#failCount");
const hiddenPassCount = document.querySelector("#hiddenPassCount");
const hiddenFailCount = document.querySelector("#hiddenFailCount");
const blankPassCount = document.querySelector("#blankPassCount");
const blankFailCount = document.querySelector("#blankFailCount");
const phaseText = document.querySelector("#phaseText");
const currentMode = document.querySelector("#currentMode");
const statusText = document.querySelector("#statusText");
const cardsContainer = document.querySelector("#cards");

const judgePanel = document.querySelector("#judgePanel");
const selectedWordText = document.querySelector("#selectedWordText");
const blendText = document.querySelector("#blendText");
const listenBtn = document.querySelector("#listenBtn");
const failBtn = document.querySelector("#failBtn");
const passBtn = document.querySelector("#passBtn");

const hiddenPanel = document.querySelector("#hiddenPanel");
const hiddenOptions = document.querySelector("#hiddenOptions");
const hiddenFeedback = document.querySelector("#hiddenFeedback");
const hiddenListenBtn = document.querySelector("#hiddenListenBtn");
const hiddenHintBtn = document.querySelector("#hiddenHintBtn");
const hiddenHintBox = document.querySelector("#hiddenHintBox");

const blankPanel = document.querySelector("#blankPanel");
const blankModeText = document.querySelector("#blankModeText");
const blankWordRow = document.querySelector("#blankWordRow");
const blankWordText = document.querySelector("#blankWordText");
const blankGapSection = document.querySelector("#blankGapSection");
const blankInput = document.querySelector("#blankInput");
const blankListenBtn = document.querySelector("#blankListenBtn");
const checkBlankBtn = document.querySelector("#checkBlankBtn");
const blankArrangeSection = document.querySelector("#blankArrangeSection");
const arrangeAnswerText = document.querySelector("#arrangeAnswerText");
const arrangeLetters = document.querySelector("#arrangeLetters");
const arrangeResetBtn = document.querySelector("#arrangeResetBtn");
const checkArrangeBtn = document.querySelector("#checkArrangeBtn");
const blankTypingSection = document.querySelector("#blankTypingSection");
const typingInput = document.querySelector("#typingInput");
const checkTypingBtn = document.querySelector("#checkTypingBtn");
const blankFeedback = document.querySelector("#blankFeedback");

const state = {
  phase: "reading",
  mode: "short",
  readingSource: [],
  pendingWords: [],
  visibleCards: [],
  selectedWord: null,
  pass: 0,
  fail: 0,
  hiddenPending: [],
  hiddenCurrent: null,
  hiddenLastWrong: "",
  hiddenPass: 0,
  hiddenFail: 0,
  blankPending: [],
  blankCurrent: null,
  blankMode: "gap",
  startPhase: "reading",
  blankArrangeSelection: [],
  blankPass: 0,
  blankFail: 0,
  tts: {
    available: false,
    providerLabel: "브라우저 음성 확인 중",
    loading: false,
    selectedVoice: null,
    selectedVoiceKey: "",
    currentVoiceLabel: "확인 중",
  },
  inRound: false,
};

function showSetupView() {
  setupView.classList.remove("hidden");
  studyView.classList.add("hidden");
}

function showStudyView() {
  setupView.classList.add("hidden");
  studyView.classList.remove("hidden");
}

function normalizeWordType(typeRaw) {
  return typeRaw === "long" ? "long" : "short";
}

function parseWordEntries(text) {
  const entries = text
    .split(/[\n,]+/)
    .map((token) => token.trim().toLowerCase())
    .filter(Boolean)
    .map((token) => {
      const [wordRaw, typeRaw] = token.split("|").map((value) => value.trim());
      return {
        word: (wordRaw || "").replace(/[^a-z]/g, ""),
        type: normalizeWordType(typeRaw),
      };
    })
    .filter((entry) => entry.word.length > 0);

  const deduped = [];
  const seen = new Set();
  entries.forEach((entry) => {
    const key = `${entry.word}|${entry.type}`;
    if (!seen.has(key)) {
      seen.add(key);
      deduped.push(entry);
    }
  });

  return deduped;
}

function serializeWordEntries(entries) {
  return entries.map((entry) => (entry.type === "short" ? entry.word : `${entry.word}|long`)).join("\n");
}

function shuffle(list) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function normalizeCardCount(value) {
  const number = Number.parseInt(value, 10);
  if (Number.isNaN(number)) return 6;
  return Math.max(1, Math.min(20, number));
}

function normalizeMode(value) {
  if (value === "all" || value === "long") return value;
  return "short";
}

function normalizeStartPhase(value) {
  if (value === "hidden" || value === "blank") return value;
  return "reading";
}

function normalizeBlankMode(value) {
  if (value === "arrange" || value === "typing") return value;
  return "gap";
}

function saveSettings(showMessage = true) {
  const entries = parseWordEntries(wordInput.value);
  const mode = normalizeMode(vowelModeInput.value);
  const startPhase = normalizeStartPhase(startPhaseInput.value);
  const blankMode = normalizeBlankMode(blankModeInput.value);

  localStorage.setItem(STORAGE_WORDS_KEY, JSON.stringify(entries));
  localStorage.setItem(STORAGE_CARD_COUNT_KEY, String(normalizeCardCount(cardCountInput.value)));
  localStorage.setItem(STORAGE_MODE_KEY, mode);
  localStorage.setItem(STORAGE_START_PHASE_KEY, startPhase);
  localStorage.setItem(STORAGE_BLANK_MODE_KEY, blankMode);

  if (showMessage) {
    window.alert(`단어 ${entries.length}개를 저장했습니다.`);
  }
}

function loadSettings() {
  const savedWords = localStorage.getItem(STORAGE_WORDS_KEY);
  const savedCardCount = localStorage.getItem(STORAGE_CARD_COUNT_KEY);
  const savedMode = localStorage.getItem(STORAGE_MODE_KEY);
  const savedStartPhase = localStorage.getItem(STORAGE_START_PHASE_KEY);
  const savedBlankMode = localStorage.getItem(STORAGE_BLANK_MODE_KEY);

  if (savedWords) {
    try {
      const parsed = JSON.parse(savedWords);
      if (Array.isArray(parsed) && parsed.length > 0) {
        if (typeof parsed[0] === "string") {
          const fallbackEntries = parsed.map((word) => ({ word, type: "short" }));
          wordInput.value = serializeWordEntries(fallbackEntries);
        } else {
          wordInput.value = serializeWordEntries(parsed);
        }
      }
    } catch {
      // Keep default UI when saved payload is invalid.
    }
  }

  if (savedCardCount) {
    cardCountInput.value = String(normalizeCardCount(savedCardCount));
  }

  vowelModeInput.value = normalizeMode(savedMode || "short");
  startPhaseInput.value = normalizeStartPhase(savedStartPhase || "reading");
  blankModeInput.value = normalizeBlankMode(savedBlankMode || "gap");
}

function filterEntriesByMode(entries, mode) {
  if (mode === "all") return entries;
  return entries.filter((entry) => entry.type === mode);
}

function pickVisibleCards(words, count) {
  return shuffle(words).slice(0, Math.min(count, words.length));
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function replaceCharAt(word, index, char) {
  return word.slice(0, index) + char + word.slice(index + 1);
}

function mutateDelete(word) {
  if (word.length <= 3) return "";
  const idx = randomInt(1, word.length - 2);
  return word.slice(0, idx) + word.slice(idx + 1);
}

function mutateDuplicate(word) {
  const idx = randomInt(0, word.length - 1);
  return word.slice(0, idx + 1) + word[idx] + word.slice(idx + 1);
}

function mutateSwap(word) {
  if (word.length < 3) return "";
  const idx = randomInt(0, word.length - 2);
  return word.slice(0, idx) + word[idx + 1] + word[idx] + word.slice(idx + 2);
}

function mutateVowel(word) {
  const vowelIndices = word.split("").map((char, idx) => (VOWELS.includes(char) ? idx : -1)).filter((idx) => idx >= 0);
  if (vowelIndices.length === 0) return "";

  const idx = vowelIndices[randomInt(0, vowelIndices.length - 1)];
  const current = word[idx];
  const options = VOWELS.split("").filter((v) => v !== current);
  return replaceCharAt(word, idx, options[randomInt(0, options.length - 1)]);
}

function mutateConsonant(word) {
  const indices = word.split("").map((char, idx) => (!VOWELS.includes(char) ? idx : -1)).filter((idx) => idx >= 0);
  if (indices.length === 0) return "";

  const idx = indices[randomInt(0, indices.length - 1)];
  const current = word[idx];
  const options = ALPHABET.split("").filter((c) => c !== current && !VOWELS.includes(c));
  return replaceCharAt(word, idx, options[randomInt(0, options.length - 1)]);
}

function mutateInsert(word) {
  const idx = randomInt(0, word.length);
  const char = ALPHABET[randomInt(0, ALPHABET.length - 1)];
  return word.slice(0, idx) + char + word.slice(idx);
}

function generateSimilarWords(target, count) {
  const result = new Set();
  const mutators = [mutateDelete, mutateDuplicate, mutateSwap, mutateVowel, mutateConsonant, mutateInsert];

  for (let tries = 0; tries < 120 && result.size < count; tries += 1) {
    const mutate = mutators[randomInt(0, mutators.length - 1)];
    const candidate = mutate(target);
    if (!candidate || candidate === target || candidate.length < 2) continue;
    result.add(candidate);
  }

  while (result.size < count) {
    const fallback = `${target}${ALPHABET[randomInt(0, ALPHABET.length - 1)]}`;
    if (fallback !== target) result.add(fallback);
  }

  return [...result].slice(0, count);
}

function getBlendUnits(entry) {
  const letters = entry.word.split("");
  if (entry.type === "short") {
    return letters;
  }

  const isSilentE = entry.word.endsWith("e") && entry.word.length >= 3;
  const firstVowelIndex = letters.findIndex((char) => VOWELS.includes(char));

  if (isSilentE && firstVowelIndex !== -1 && firstVowelIndex < letters.length - 2) {
    const base = entry.word.slice(0, -1).split("");
    return base.map((char, index) => (index === firstVowelIndex ? LONG_VOWEL_SOUND[char] || char : char));
  }

  return letters.map((char, index) => {
    if (index === firstVowelIndex) {
      return LONG_VOWEL_SOUND[char] || char;
    }
    return char;
  });
}

function getBlendReadout(entry) {
  const units = getBlendUnits(entry);
  return `${units.join(" + ")} -> ${entry.word}`;
}

function getBlankModeLabel(mode) {
  if (mode === "arrange") return "arrange";
  if (mode === "typing") return "typing";
  return "gap";
}

function getBlankInstruction(mode) {
  if (mode === "arrange") return "단어를 듣고 알파벳을 순서대로 눌러 주세요.";
  if (mode === "typing") return "단어를 듣고 전체 철자를 입력해 주세요.";
  return "빈칸에 들어갈 글자를 입력해 주세요.";
}

function updateStats() {
  remainingCount.textContent = String(state.pendingWords.length);
  passCount.textContent = String(state.pass);
  failCount.textContent = String(state.fail);
  hiddenPassCount.textContent = String(state.hiddenPass);
  hiddenFailCount.textContent = String(state.hiddenFail);
  blankPassCount.textContent = String(state.blankPass);
  blankFailCount.textContent = String(state.blankFail);
  phaseText.textContent = state.phase === "blank" ? `blank:${getBlankModeLabel(state.blankMode)}` : state.phase;
  currentMode.textContent = state.mode;
}

function getVoiceKey(voice) {
  return `${voice.name}::${voice.lang}::${voice.voiceURI || ""}`;
}

function getDisplayVoiceLabel(voice) {
  return voice ? `${voice.name} (${voice.lang})` : "default";
}

function selectBestVoice(voices, preferredVoiceKey = "") {
  if (voices.length === 0) {
    return null;
  }

  if (preferredVoiceKey) {
    const previousVoice = voices.find((voice) => getVoiceKey(voice) === preferredVoiceKey);
    if (previousVoice) {
      return previousVoice;
    }
  }

  const rankedVoices = [...voices].sort((left, right) => {
    const leftScore = Number(Boolean(left.localService)) + Number(Boolean(left.default)) * 0.5;
    const rightScore = Number(Boolean(right.localService)) + Number(Boolean(right.default)) * 0.5;
    return rightScore - leftScore;
  });

  for (const preferredName of PREFERRED_VOICE_NAMES) {
    const exactMatch = rankedVoices.find((voice) => voice.name === preferredName);
    if (exactMatch) {
      return exactMatch;
    }
  }

  return (
    rankedVoices.find((voice) => voice.lang === "en-US") ||
    rankedVoices.find((voice) => voice.lang && voice.lang.startsWith("en-US")) ||
    rankedVoices.find((voice) => voice.lang && voice.lang.startsWith("en")) ||
    rankedVoices[0]
  );
}

function stopCurrentAudio() {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
  state.tts.loading = false;
}

function updateTtsUi() {
  ttsProviderText.textContent = state.tts.providerLabel;
  ttsVoiceText.textContent = state.tts.currentVoiceLabel;

  const readingReady = state.tts.available && state.phase === "reading" && Boolean(state.selectedWord);
  const hiddenReady = state.tts.available && state.phase === "hidden" && Boolean(state.hiddenCurrent);
  const blankReady = state.tts.available && state.phase === "blank" && Boolean(state.blankCurrent);

  listenBtn.disabled = state.tts.loading || !readingReady;
  hiddenListenBtn.disabled = state.tts.loading || !hiddenReady;
  blankListenBtn.disabled = state.tts.loading || !blankReady;
}

async function loadTtsConfig() {
  if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
    state.tts.available = false;
    state.tts.selectedVoice = null;
    state.tts.selectedVoiceKey = "";
    state.tts.providerLabel = "브라우저 음성 미지원";
    state.tts.currentVoiceLabel = "미지원";
    updateTtsUi();
    return;
  }

  const voices = window.speechSynthesis.getVoices().filter((voice) => voice.lang && voice.lang.startsWith("en"));
  state.tts.available = true;
  state.tts.selectedVoice = selectBestVoice(voices, state.tts.selectedVoiceKey);
  state.tts.selectedVoiceKey = state.tts.selectedVoice ? getVoiceKey(state.tts.selectedVoice) : "";
  state.tts.providerLabel = state.tts.selectedVoice
    ? `브라우저 음성 (${state.tts.selectedVoice.name})`
    : "브라우저 음성 (default)";
  state.tts.currentVoiceLabel = getDisplayVoiceLabel(state.tts.selectedVoice);
  updateTtsUi();
}

async function playPronunciation(text) {
  if (!state.tts.available || !text) {
    return;
  }

  stopCurrentAudio();
  state.tts.loading = true;
  if (!state.tts.selectedVoice) {
    await loadTtsConfig();
  }
  updateTtsUi();

  try {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = state.tts.selectedVoice?.lang || "en-US";
    utterance.rate = 0.9;
    utterance.pitch = 1;

    if (state.tts.selectedVoice) {
      utterance.voice = state.tts.selectedVoice;
    }
    state.tts.currentVoiceLabel = getDisplayVoiceLabel(utterance.voice || state.tts.selectedVoice);
    updateTtsUi();

    utterance.addEventListener(
      "end",
      () => {
        state.tts.loading = false;
        updateTtsUi();
      },
      { once: true },
    );
    utterance.addEventListener(
      "error",
      () => {
        state.tts.loading = false;
        updateTtsUi();
        statusText.textContent = "발음 재생에 실패했습니다.";
      },
      { once: true },
    );

    window.speechSynthesis.speak(utterance);
  } catch (error) {
    stopCurrentAudio();
    updateTtsUi();
    statusText.textContent = error.message || "발음 재생에 실패했습니다.";
  }
}

function hideJudgePanel() {
  judgePanel.classList.add("hidden");
  state.selectedWord = null;
  blendText.textContent = "-";
  updateTtsUi();
}

function showJudgePanel(entry) {
  state.selectedWord = entry;
  selectedWordText.textContent = `${entry.word} (${entry.type})`;
  blendText.textContent = getBlendReadout(entry);
  judgePanel.classList.remove("hidden");
  updateTtsUi();
}

function hideHiddenPanel() {
  hiddenPanel.classList.add("hidden");
  hiddenFeedback.textContent = "";
  hiddenOptions.innerHTML = "";
  hiddenHintBox.innerHTML = "";
  hiddenHintBtn.disabled = true;
  state.hiddenLastWrong = "";
  updateTtsUi();
}

function showHiddenPanel() {
  hiddenPanel.classList.remove("hidden");
  updateTtsUi();
}

function showBlankPanel() {
  blankPanel.classList.remove("hidden");
  blankModeText.textContent = getBlankModeLabel(state.blankMode);
  updateTtsUi();
}

function hideBlankPanel() {
  blankPanel.classList.add("hidden");
  blankModeText.textContent = getBlankModeLabel(state.blankMode);
  blankWordRow.classList.add("hidden");
  blankWordText.textContent = "-";
  blankFeedback.textContent = "";
  blankInput.value = "";
  blankInput.disabled = false;
  typingInput.value = "";
  typingInput.disabled = false;
  arrangeAnswerText.textContent = "-";
  arrangeLetters.innerHTML = "";
  checkBlankBtn.disabled = false;
  checkArrangeBtn.disabled = false;
  checkTypingBtn.disabled = false;
  arrangeResetBtn.disabled = false;
  blankGapSection.classList.add("hidden");
  blankArrangeSection.classList.add("hidden");
  blankTypingSection.classList.add("hidden");
  updateTtsUi();
}

function renderBlankModePanel(question) {
  blankModeText.textContent = getBlankModeLabel(question.mode);
  blankWordRow.classList.toggle("hidden", question.mode !== "gap");
  blankGapSection.classList.toggle("hidden", question.mode !== "gap");
  blankArrangeSection.classList.toggle("hidden", question.mode !== "arrange");
  blankTypingSection.classList.toggle("hidden", question.mode !== "typing");
}

function renderCards() {
  cardsContainer.innerHTML = "";

  if (state.phase !== "reading" || !state.inRound || state.pendingWords.length === 0) {
    return;
  }

  state.visibleCards.forEach((entry) => {
    const isSelected = state.selectedWord && state.selectedWord.word === entry.word && state.selectedWord.type === entry.type;
    const button = document.createElement("button");
    button.type = "button";
    button.className = `card ${isSelected ? "is-selected" : "card-face-down"}`;
    button.textContent = isSelected ? entry.word : "?";
    button.disabled = Boolean(state.selectedWord && !isSelected);
    button.setAttribute("role", "listitem");

    button.addEventListener("click", () => {
      if (state.selectedWord || state.phase !== "reading") return;

      showJudgePanel(entry);
      renderCards();
      statusText.textContent = "블렌딩을 보고 읽어본 뒤, 부모가 Pass/Fail을 선택해 주세요.";
    });

    cardsContainer.append(button);
  });
}

function renderPhaseVisibility() {
  if (state.phase === "reading") {
    cardsContainer.classList.remove("hidden");
    hideHiddenPanel();
    hideBlankPanel();
    return;
  }

  if (state.phase === "hidden") {
    cardsContainer.classList.add("hidden");
    hideJudgePanel();
    showHiddenPanel();
    hideBlankPanel();
    return;
  }

  if (state.phase === "blank") {
    cardsContainer.classList.add("hidden");
    hideJudgePanel();
    hideHiddenPanel();
    showBlankPanel();
    return;
  }

  cardsContainer.classList.add("hidden");
  hideJudgePanel();
  hideHiddenPanel();
  hideBlankPanel();
}

function nextReadingTurn() {
  if (state.pendingWords.length === 0) {
    startHiddenPhase();
    updateStats();
    return;
  }

  const cardCount = normalizeCardCount(cardCountInput.value);
  state.visibleCards = pickVisibleCards(state.pendingWords, cardCount);
  hideJudgePanel();
  renderPhaseVisibility();
  renderCards();
  updateStats();
  statusText.textContent = "카드를 눌러 블렌딩으로 읽어보세요.";
}

function handleJudge(result) {
  const selected = state.selectedWord;
  if (!selected || state.phase !== "reading") return;

  const index = state.pendingWords.findIndex(
    (entry) => entry.word === selected.word && entry.type === selected.type,
  );
  if (index === -1) return;

  const entry = state.pendingWords[index];
  state.pendingWords.splice(index, 1);

  if (result === "pass") {
    state.pass += 1;
  } else {
    state.fail += 1;
    state.pendingWords.push(entry);
  }

  nextReadingTurn();
}

function buildHiddenQuestion(entry) {
  const distractors = generateSimilarWords(entry.word, 2);
  const options = shuffle([entry.word, ...distractors]);

  return {
    entry,
    options,
  };
}

function buildDiffAlignment(target, picked) {
  const m = target.length;
  const n = picked.length;
  const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));

  for (let i = 0; i <= m; i += 1) dp[i][0] = i;
  for (let j = 0; j <= n; j += 1) dp[0][j] = j;

  for (let i = 1; i <= m; i += 1) {
    for (let j = 1; j <= n; j += 1) {
      if (target[i - 1] === picked[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1];
      } else {
        dp[i][j] = Math.min(
          dp[i - 1][j - 1] + 1,
          dp[i - 1][j] + 1,
          dp[i][j - 1] + 1,
        );
      }
    }
  }

  const aligned = [];
  let i = m;
  let j = n;

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && target[i - 1] === picked[j - 1] && dp[i][j] === dp[i - 1][j - 1]) {
      aligned.push({ t: target[i - 1], p: picked[j - 1], match: true });
      i -= 1;
      j -= 1;
      continue;
    }

    if (i > 0 && j > 0 && dp[i][j] === dp[i - 1][j - 1] + 1) {
      aligned.push({ t: target[i - 1], p: picked[j - 1], match: false });
      i -= 1;
      j -= 1;
      continue;
    }

    if (i > 0 && dp[i][j] === dp[i - 1][j] + 1) {
      aligned.push({ t: target[i - 1], p: "∅", match: false });
      i -= 1;
      continue;
    }

    aligned.push({ t: "∅", p: picked[j - 1], match: false });
    j -= 1;
  }

  return aligned.reverse();
}

function renderDiffWordLine(aligned, key) {
  return aligned
    .map((cell) => {
      const value = key === "target" ? cell.t : cell.p;
      const cls = cell.match ? "" : "diff-bad";
      return `<span class="${cls}">${value}</span>`;
    })
    .join("");
}

function showHiddenDiff(target, picked) {
  const aligned = buildDiffAlignment(target, picked);
  const targetLine = renderDiffWordLine(aligned, "target");
  const pickedLine = renderDiffWordLine(aligned, "picked");

  hiddenHintBox.innerHTML = `
    <div>힌트: 다른 부분을 확인해 보세요.</div>
    <div class="diff-grid">
      <div><span class="diff-row-label">정답</span>${targetLine}</div>
      <div><span class="diff-row-label">선택</span>${pickedLine}</div>
    </div>
  `;
}

function renderHiddenQuestion() {
  if (!state.hiddenCurrent) return;

  hiddenFeedback.textContent = "";
  hiddenHintBox.innerHTML = "";
  hiddenHintBtn.disabled = true;
  state.hiddenLastWrong = "";
  hiddenOptions.innerHTML = "";
  updateTtsUi();

  state.hiddenCurrent.options.forEach((optionWord) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "hidden-card";
    button.textContent = optionWord;

    button.addEventListener("click", () => {
      if (state.phase !== "hidden" || !state.hiddenCurrent) return;
      handleHiddenChoice(optionWord, button);
    });

    hiddenOptions.append(button);
  });
}

function handleHiddenChoice(optionWord, selectedButton) {
  const current = state.hiddenCurrent;
  if (!current) return;

  const target = current.entry.word;
  if (optionWord === target) {
    const buttons = hiddenOptions.querySelectorAll("button");
    buttons.forEach((btn) => {
      btn.disabled = true;
      if (btn.textContent === target) {
        btn.classList.add("is-correct");
      }
    });
    state.hiddenPass += 1;
    hiddenFeedback.textContent = "Pass! 정확한 단어를 찾았어요.";
    hiddenHintBtn.disabled = true;
    setTimeout(() => {
      nextHiddenTurn();
    }, 550);
    return;
  }

  state.hiddenFail += 1;
  state.hiddenLastWrong = optionWord;
  selectedButton.classList.add("is-wrong");
  selectedButton.disabled = true;
  hiddenHintBtn.disabled = false;
  hiddenFeedback.textContent = "틀렸어요. 다시 선택해 보세요. 필요하면 힌트 보기를 누르세요.";
  hiddenHintBox.innerHTML = "";
  updateStats();
}

function startHiddenPhase(isDirectStart = false) {
  stopCurrentAudio();
  state.phase = "hidden";
  state.hiddenPending = shuffle(state.readingSource.map((entry) => ({ ...entry })));
  state.hiddenCurrent = null;
  state.hiddenLastWrong = "";
  state.hiddenPass = 0;
  state.hiddenFail = 0;

  statusText.textContent = isDirectStart
    ? "숨은 단어 찾기부터 바로 시작합니다."
    : "읽기 단계 완료! 이제 숨은 단어 찾기를 진행합니다.";
  renderPhaseVisibility();
  nextHiddenTurn();
}

function nextHiddenTurn() {
  if (state.phase !== "hidden") return;

  if (state.hiddenPending.length === 0) {
    startBlankPhase();
    updateStats();
    return;
  }

  const pickIndex = randomInt(0, state.hiddenPending.length - 1);
  const [entry] = state.hiddenPending.splice(pickIndex, 1);
  state.hiddenCurrent = buildHiddenQuestion(entry);
  state.hiddenLastWrong = "";

  renderPhaseVisibility();
  renderHiddenQuestion();
  updateStats();
  statusText.textContent = "정확한 철자 카드를 선택해 주세요.";
}

function startBlankPhase(isDirectStart = false) {
  stopCurrentAudio();
  state.phase = "blank";
  state.blankPending = shuffle(state.readingSource.map((entry) => ({ ...entry })));
  state.blankCurrent = null;
  state.blankArrangeSelection = [];
  state.blankPass = 0;
  state.blankFail = 0;

  statusText.textContent = isDirectStart
    ? `blank ${getBlankModeLabel(state.blankMode)} 모드부터 바로 시작합니다.`
    : "숨은 단어 찾기 완료! 이제 빈칸 채우기를 진행합니다.";
  renderPhaseVisibility();
  nextBlankTurn();
}

function buildBlankQuestion(entry) {
  if (state.blankMode === "arrange") {
    return {
      entry,
      mode: "arrange",
      letters: shuffle(entry.word.split("").map((char, index) => ({ char, id: `${char}-${index}` }))),
    };
  }

  if (state.blankMode === "typing") {
    return {
      entry,
      mode: "typing",
      prompt: `${"_ ".repeat(entry.word.length).trim()} (${entry.type})`,
    };
  }

  const index = randomInt(0, entry.word.length - 1);
  const chars = entry.word.split("");
  chars[index] = "_";

  return {
    entry,
    mode: "gap",
    index,
    prompt: `${chars.join("")} (${entry.type})`,
    answer: entry.word[index],
  };
}

function renderArrangeAnswer() {
  if (!state.blankCurrent || state.blankCurrent.mode !== "arrange") return;
  const wordLength = state.blankCurrent.entry.word.length;
  const selected = state.blankArrangeSelection.join(" ");
  const placeholders = Array.from({ length: wordLength - state.blankArrangeSelection.length }, () => "_").join(" ");
  arrangeAnswerText.textContent = [selected, placeholders].filter(Boolean).join(" ").trim() || "_";
}

function renderArrangeLetters() {
  if (!state.blankCurrent || state.blankCurrent.mode !== "arrange") return;

  arrangeLetters.innerHTML = "";
  state.blankCurrent.letters.forEach((letter, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "letter-chip";
    button.textContent = letter.char;
    button.disabled = state.blankCurrent.usedIndices.includes(index);
    button.addEventListener("click", () => {
      if (state.phase !== "blank" || state.blankCurrent?.mode !== "arrange") return;
      state.blankCurrent.usedIndices.push(index);
      state.blankArrangeSelection.push(letter.char);
      renderArrangeAnswer();
      renderArrangeLetters();
    });
    arrangeLetters.append(button);
  });
}

function renderBlankQuestion() {
  if (!state.blankCurrent) return;

  renderBlankModePanel(state.blankCurrent);
  blankFeedback.textContent = "";
  blankInput.value = "";
  blankInput.disabled = false;
  typingInput.value = "";
  typingInput.disabled = false;
  checkBlankBtn.disabled = false;
  checkArrangeBtn.disabled = false;
  checkTypingBtn.disabled = false;
  arrangeResetBtn.disabled = false;

  if (state.blankCurrent.mode === "gap") {
    blankWordText.textContent = state.blankCurrent.prompt;
    blankInput.maxLength = 1;
    return;
  }

  if (state.blankCurrent.mode === "arrange") {
    renderArrangeAnswer();
    renderArrangeLetters();
    return;
  }
}

function completeBlankTurn(isPass, successText, failText) {
  if (!state.blankCurrent) return;

  if (isPass) {
    state.blankPass += 1;
    blankFeedback.textContent = successText;
    checkBlankBtn.disabled = true;
    checkArrangeBtn.disabled = true;
    checkTypingBtn.disabled = true;
    arrangeResetBtn.disabled = true;
    blankInput.disabled = true;
    typingInput.disabled = true;
    arrangeLetters.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });
    updateStats();
    setTimeout(() => {
      nextBlankTurn();
    }, 650);
    return;
  }

  state.blankFail += 1;
  updateStats();

  if (state.blankCurrent.mode === "gap") {
    state.blankPending.push({ ...state.blankCurrent.entry });
    blankFeedback.textContent = failText;
    checkBlankBtn.disabled = true;
    checkArrangeBtn.disabled = true;
    checkTypingBtn.disabled = true;
    arrangeResetBtn.disabled = true;
    blankInput.disabled = true;
    typingInput.disabled = true;
    arrangeLetters.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });
    setTimeout(() => {
      nextBlankTurn();
    }, 650);
    return;
  }

  blankFeedback.textContent = failText;

  if (state.blankCurrent.mode === "arrange") {
    resetArrangeAnswer();
    return;
  }

  typingInput.value = "";
  typingInput.focus();
}

function nextBlankTurn() {
  if (state.phase !== "blank") return;

  if (state.blankPending.length === 0) {
    state.phase = "done";
    state.inRound = false;
    state.blankCurrent = null;
    state.blankArrangeSelection = [];
    stopCurrentAudio();
    renderPhaseVisibility();
    updateStats();
    statusText.textContent = "완료! reading + hidden + blank 단계를 모두 pass 했습니다.";
    return;
  }

  const pickIndex = randomInt(0, state.blankPending.length - 1);
  const [entry] = state.blankPending.splice(pickIndex, 1);
  const question = buildBlankQuestion(entry);

  state.blankCurrent = {
    ...question,
    usedIndices: [],
  };
  state.blankArrangeSelection = [];

  renderPhaseVisibility();
  renderBlankQuestion();
  updateStats();
  updateTtsUi();
  statusText.textContent = getBlankInstruction(state.blankMode);

  if (state.tts.available) {
    playPronunciation(state.blankCurrent.entry.word);
  }
}

function checkBlankAnswer() {
  if (state.phase !== "blank" || !state.blankCurrent || state.blankCurrent.mode !== "gap") return;

  const typed = blankInput.value.trim().toLowerCase();
  if (!typed) {
    blankFeedback.textContent = "글자 1개를 입력해 주세요.";
    return;
  }

  if (typed[0] === state.blankCurrent.answer) {
    completeBlankTurn(true, "Pass! 잘했어요.", "");
    return;
  }

  completeBlankTurn(false, "", `Fail. 정답은 '${state.blankCurrent.answer}' 였어요.`);
}

function resetArrangeAnswer() {
  if (!state.blankCurrent || state.blankCurrent.mode !== "arrange") return;
  state.blankCurrent.usedIndices = [];
  state.blankArrangeSelection = [];
  renderArrangeAnswer();
  renderArrangeLetters();
}

function checkArrangeAnswer() {
  if (state.phase !== "blank" || !state.blankCurrent || state.blankCurrent.mode !== "arrange") return;

  const typed = state.blankArrangeSelection.join("");
  if (typed.length !== state.blankCurrent.entry.word.length) {
    blankFeedback.textContent = "모든 알파벳을 순서대로 눌러 주세요.";
    return;
  }

  if (typed === state.blankCurrent.entry.word) {
    completeBlankTurn(true, "Pass! 순서를 잘 맞췄어요.", "");
    return;
  }

  completeBlankTurn(false, "", "Fail. 다시 순서대로 눌러 주세요.");
}

function checkTypingAnswer() {
  if (state.phase !== "blank" || !state.blankCurrent || state.blankCurrent.mode !== "typing") return;

  const typed = typingInput.value.trim().toLowerCase();
  if (!typed) {
    blankFeedback.textContent = "단어 전체를 입력해 주세요.";
    return;
  }

  if (typed === state.blankCurrent.entry.word) {
    completeBlankTurn(true, "Pass! 단어를 잘 쳤어요.", "");
    return;
  }

  completeBlankTurn(false, "", "Fail. 다시 입력해 주세요.");
}

function startRound() {
  const entries = parseWordEntries(wordInput.value);
  if (entries.length === 0) {
    window.alert("단어를 1개 이상 입력해 주세요.");
    showSetupView();
    return;
  }

  const mode = normalizeMode(vowelModeInput.value);
  const startPhase = normalizeStartPhase(startPhaseInput.value);
  const blankMode = normalizeBlankMode(blankModeInput.value);
  const filteredEntries = filterEntriesByMode(entries, mode);

  if (filteredEntries.length === 0) {
    window.alert(`현재 모드(${mode})에 맞는 단어가 없습니다.`);
    showSetupView();
    return;
  }

  saveSettings(false);
  stopCurrentAudio();

  state.phase = startPhase;
  state.mode = mode;
  state.startPhase = startPhase;
  state.blankMode = blankMode;
  state.readingSource = filteredEntries.map((entry) => ({ ...entry }));
  state.pendingWords = shuffle(filteredEntries.map((entry) => ({ ...entry })));
  state.visibleCards = [];
  state.selectedWord = null;
  state.pass = 0;
  state.fail = 0;
  state.hiddenPending = [];
  state.hiddenCurrent = null;
  state.hiddenLastWrong = "";
  state.hiddenPass = 0;
  state.hiddenFail = 0;
  state.blankPending = [];
  state.blankCurrent = null;
  state.blankArrangeSelection = [];
  state.blankPass = 0;
  state.blankFail = 0;
  state.inRound = true;

  showStudyView();
  if (startPhase === "hidden") {
    state.pendingWords = [];
    startHiddenPhase(true);
    return;
  }

  if (startPhase === "blank") {
    state.pendingWords = [];
    startBlankPhase(true);
    return;
  }

  nextReadingTurn();
}

saveWordsBtn.addEventListener("click", () => saveSettings(true));
startBtn.addEventListener("click", startRound);
goSetupBtn.addEventListener("click", () => {
  stopCurrentAudio();
  showSetupView();
});
passBtn.addEventListener("click", () => handleJudge("pass"));
failBtn.addEventListener("click", () => handleJudge("fail"));
listenBtn.addEventListener("click", () => {
  if (state.selectedWord) {
    playPronunciation(state.selectedWord.word);
  }
});
hiddenListenBtn.addEventListener("click", () => {
  if (state.hiddenCurrent) {
    playPronunciation(state.hiddenCurrent.entry.word);
  }
});
checkBlankBtn.addEventListener("click", checkBlankAnswer);
arrangeResetBtn.addEventListener("click", resetArrangeAnswer);
checkArrangeBtn.addEventListener("click", checkArrangeAnswer);
hiddenHintBtn.addEventListener("click", () => {
  if (!state.hiddenCurrent || !state.hiddenLastWrong) return;
  showHiddenDiff(state.hiddenCurrent.entry.word, state.hiddenLastWrong);
});
blankListenBtn.addEventListener("click", () => {
  if (state.blankCurrent) {
    playPronunciation(state.blankCurrent.entry.word);
  }
});
checkTypingBtn.addEventListener("click", checkTypingAnswer);
blankInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    checkBlankAnswer();
  }
});
typingInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    checkTypingAnswer();
  }
});

if ("speechSynthesis" in window) {
  window.speechSynthesis.onvoiceschanged = () => {
    loadTtsConfig();
  };
}

loadSettings();
state.mode = normalizeMode(vowelModeInput.value);
state.startPhase = normalizeStartPhase(startPhaseInput.value);
state.blankMode = normalizeBlankMode(blankModeInput.value);
updateStats();
loadTtsConfig();
updateTtsUi();
showSetupView();
