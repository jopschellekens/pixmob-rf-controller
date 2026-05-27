let currentShowId = null
let currentShowName = "Untitled Show"
let uploadedAudioFile = null
let uploadedAudioFilename = null
let showDirty = false
let wakeBeforePlay = true
let sentCommandIndex = 0

document.addEventListener("DOMContentLoaded", async () => {
  await loadCommands()
  renderCommandPalette(document.getElementById("command-palette"))
  initTimeline()

  setupAudioCallbacks()
  setupEventListeners()
  loadShowList()
  newShow()
  checkHackrfStatus()
})

function setupAudioCallbacks() {
  audioCallbacks.onTimeUpdate = (time) => {
    setTimelinePlaybackTime(time)
    const events = getTimelineEvents()
    while (sentCommandIndex < events.length && events[sentCommandIndex].time <= time) {
      const evt = events[sentCommandIndex]
      sendCommandLive(evt.command, evt.repeats || 2)
      sentCommandIndex++
    }
  }
  audioCallbacks.onPlayStateChange = (playing) => {
    document.getElementById("btn-play").textContent = playing ? "⏸" : "▶"
    document.getElementById("btn-play").className = playing ? "btn btn-play playing" : "btn btn-play"
    if (playing) {
      sentCommandIndex = 0
    }
  }
  audioCallbacks.onLoad = (buffer) => {
    const duration = buffer.duration
    const bpm = detectBPM(buffer)
    detectedBPM = bpm
    timelineBPM = bpm

    setTimelineDuration(Math.ceil(duration))
    document.getElementById("audio-info").textContent =
      `Duration: ${formatTime(duration)}  ·  Detected BPM: ${bpm}`
    document.getElementById("auto-bpm").value = bpm
    document.getElementById("waveform-container").classList.remove("hidden")
    document.getElementById("waveform-container").classList.add("visible")

    document.getElementById("btn-auto-generate").textContent = `🤖 Generate Show (${bpm} BPM)`

    setTimeout(() => {
      const wfCanvas = document.getElementById("waveform-canvas")
      if (wfCanvas) {
        const container = wfCanvas.parentElement
        wfCanvas.width = container.clientWidth
        wfCanvas.height = container.clientHeight || 80
        drawWaveform(wfCanvas, buffer)
      }
    }, 100)
  }
}

function setupEventListeners() {
  document.getElementById("btn-new").addEventListener("click", newShow)
  document.getElementById("btn-save").addEventListener("click", saveShow)
  document.getElementById("btn-load").addEventListener("click", () => document.getElementById("show-list-modal").classList.remove("hidden"))
  document.getElementById("btn-export").addEventListener("click", exportShow)

  document.getElementById("btn-play").addEventListener("click", togglePlayback)
  document.getElementById("btn-stop").addEventListener("click", stopPlayback)
  document.getElementById("btn-wake-toggle").addEventListener("click", toggleWakeBeforePlay)
  document.getElementById("btn-wake-now").addEventListener("click", sendWakeNow)
  document.getElementById("btn-send-show").addEventListener("click", sendShowToBands)

  document.getElementById("volume-slider").addEventListener("input", (e) => {
    const v = parseFloat(e.target.value)
    setVolume(v)
    document.getElementById("volume-value").textContent = v
  })

  document.getElementById("audio-upload").addEventListener("change", handleAudioUpload)
  document.getElementById("btn-auto-generate").addEventListener("click", () => {
    if (!uploadedAudioFilename) {
      document.getElementById("audio-upload").click()
      return
    }
    document.getElementById("auto-bpm-display").textContent = `${detectedBPM} BPM`
    document.getElementById("auto-dur-display").textContent = formatTime(getAudioDuration())
    document.querySelectorAll(".color-option input").forEach(cb => cb.checked = true)
    document.getElementById("auto-generate-modal").classList.remove("hidden")
  })

  document.getElementById("audio-upload").addEventListener("click", (e) => {
    e.stopPropagation()
  })

  document.getElementById("show-name").addEventListener("input", (e) => {
    currentShowName = e.target.value || "Untitled Show"
    showDirty = true
    updateTitle()
  })

  document.getElementById("btn-close-modal").addEventListener("click", () => {
    document.getElementById("show-list-modal").classList.add("hidden")
  })
  document.getElementById("btn-close-auto").addEventListener("click", () => {
    document.getElementById("auto-generate-modal").classList.add("hidden")
  })

  const closeInspector = document.getElementById("btn-close-inspector")
  if (closeInspector) {
    closeInspector.addEventListener("click", () => {
      selectedEvent = null
      updateEventInspector(null)
      renderTimeline()
    })
  }

  document.getElementById("btn-mic-mode").addEventListener("click", () => {
    document.getElementById("mic-modal").classList.remove("hidden")
  })
  document.getElementById("btn-close-mic").addEventListener("click", () => {
    stopMicMode()
    document.getElementById("mic-modal").classList.add("hidden")
  })
  document.getElementById("btn-mic-start").addEventListener("click", startMicMode)
  document.getElementById("btn-mic-stop").addEventListener("click", stopMicMode)
  document.getElementById("mic-sensitivity").addEventListener("input", (e) => {
    document.getElementById("mic-sensitivity-val").textContent = e.target.value
  })

  timelineCallbacks.onChange = (events) => {
    showDirty = true
    document.getElementById("event-count").textContent = events.length
  }

  timelineCallbacks.onDurationChange = (duration) => {
    document.getElementById("show-duration").textContent = formatTime(duration)
  }
}

function newShow() {
  if (showDirty && !confirm("Discard unsaved changes?")) return
  currentShowId = null
  currentShowName = "Untitled Show"
  showDirty = false
  clearTimeline()
  setTimelineDuration(30)
  document.getElementById("show-name").value = "Untitled Show"
  document.getElementById("event-count").textContent = "0"
  document.getElementById("show-duration").textContent = "0:30.00"
  document.getElementById("audio-info").textContent = "No audio loaded"
  document.getElementById("waveform-container").classList.add("hidden")
  document.getElementById("waveform-container").classList.remove("visible")
  uploadedAudioFile = null
  uploadedAudioFilename = null
  if (audioBuffer) {
    stopAudio()
    audioBuffer = null
  }
  updateTitle()
}

async function saveShow() {
  const timeline = getTimelineEvents()
  const body = {
    id: currentShowId,
    name: currentShowName,
    bpm: timelineBPM,
    duration: timelineDuration,
    audio_file: uploadedAudioFilename,
    audio_offset: 0,
    timeline: timeline.map((e) => ({
      time: e.time,
      command: e.command,
      label: e.label,
      color: e.color,
      repeats: e.repeats,
      duration: e.duration,
    })),
    groups: [],
  }

  const res = await fetch("/api/shows", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const data = await res.json()
  if (data.success) {
    currentShowId = data.id
    showDirty = false
    updateTitle()
    loadShowList()
    showToast("Show saved!")
  } else {
    showToast("Failed to save show", "error")
  }
}

async function loadShowList() {
  const res = await fetch("/api/shows")
  const shows = await res.json()
  const list = document.getElementById("show-list")
  list.innerHTML = ""

  if (shows.length === 0) {
    list.innerHTML = '<div class="empty-list">No saved shows yet</div>'
    return
  }

  for (const show of shows) {
    const item = document.createElement("div")
    item.className = "show-list-item"
    item.innerHTML = `
      <div class="show-item-info">
        <div class="show-item-name">${show.name}</div>
        <div class="show-item-meta">${show.command_count} commands · ${formatTime(show.duration)} ${show.has_audio ? "🎵" : ""}</div>
      </div>
      <div class="show-item-actions">
        <button class="btn-icon" onclick="loadShow('${show.id}')" title="Load">📂</button>
        <button class="btn-icon" onclick="deleteShow('${show.id}')" title="Delete">🗑️</button>
      </div>
    `
    list.appendChild(item)
  }
}

async function loadShow(showId) {
  if (showDirty && !confirm("Discard unsaved changes?")) return
  const res = await fetch(`/api/shows/${showId}`)
  const show = await res.json()

  currentShowId = show.id
  currentShowName = show.name
  timelineBPM = show.bpm || 120
  timelineDuration = show.duration || 30

  document.getElementById("show-name").value = show.name
  document.getElementById("show-duration").textContent = formatTime(timelineDuration)
  document.getElementById("event-count").textContent = (show.timeline || []).length
  document.getElementById("show-list-modal").classList.add("hidden")

  if (show.audio_file) {
    uploadedAudioFilename = show.audio_file
    document.getElementById("audio-info").textContent = `Audio: ${show.audio_file}`
  }

  loadTimelineEvents(show.timeline || [])
  showDirty = false
  updateTitle()
  showToast("Show loaded!")
}

async function deleteShow(showId) {
  if (!confirm("Delete this show?")) return
  await fetch(`/api/shows/${showId}`, { method: "DELETE" })
  loadShowList()
}

function exportShow() {
  const events = getTimelineEvents()
  const data = {
    name: currentShowName,
    bpm: timelineBPM,
    duration: timelineDuration,
    timeline: events,
    exported: new Date().toISOString(),
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `${currentShowName.replace(/\s+/g, "_")}.pixmob.json`
  a.click()
  URL.revokeObjectURL(url)
}

async function togglePlayback() {
  if (isPlaying) {
    pauseAudio()
  } else {
    if (!audioBuffer) return
    if (wakeBeforePlay && pauseOffset === 0) {
      const wakeBtn = document.getElementById("btn-wake-toggle")
      wakeBtn.classList.add("sending")
      showToast("Sending 30s wake (audio starts immediately)...")
      sendWakeCommand().finally(() => wakeBtn.classList.remove("sending"))
    }
    playAudio(pauseOffset > 0 ? pauseOffset : 0)
  }
}

function stopPlayback() {
  stopAudio()
  setTimelinePlaybackTime(0)
}

function toggleWakeBeforePlay() {
  wakeBeforePlay = !wakeBeforePlay
  const btn = document.getElementById("btn-wake-toggle")
  btn.classList.toggle("active", wakeBeforePlay)
  btn.title = wakeBeforePlay ? "Wake before play: ON" : "Wake before play: OFF"
}

async function sendWakeNow() {
  showToast("Sending 30s wake command...")
  const btn = document.getElementById("btn-wake-now")
  btn.disabled = true
  btn.textContent = "⏳"
  try {
    const res = await fetch("/api/wake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seconds: 30 }),
    })
    const data = await res.json()
    if (data.success) {
      showToast("Wake sent! Wristbands active for ~30s.")
    } else {
      showToast("Wake failed: " + (data.error || "unknown error"), "error")
    }
  } catch (e) {
    showToast("Wake failed: " + e.message, "error")
  }
  btn.disabled = false
  btn.textContent = "🔔 Now"
}

async function checkHackrfStatus() {
  const indicator = document.getElementById("hackrf-status")
  try {
    const res = await fetch("/api/hackrf-status")
    const data = await res.json()
    if (data.success) {
      const board = (data.info || []).join(" | ")
      indicator.className = "hackrf-status online"
      indicator.title = board
      indicator.innerHTML = "📡 Online"
    } else {
      indicator.className = "hackrf-status offline"
      indicator.title = data.error || "Not detected"
      indicator.innerHTML = "📡 Offline"
    }
  } catch {
    indicator.className = "hackrf-status offline"
    indicator.title = "Could not reach server"
    indicator.innerHTML = "📡 Offline"
  }
}

async function sendWakeCommand() {
  try {
    const res = await fetch("/api/wake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seconds: 30 }),
    })
    const data = await res.json()
    if (!data.success) {
      console.error("Wake before play failed:", data.error)
    }
  } catch (e) {
    console.error("Wake before play failed:", e.message)
  }
}

let liveCommandQueue = []

async function sendCommandLive(command, repeats) {
  if (liveCommandQueue.length > 10) return
  const id = Date.now() + Math.random()
  liveCommandQueue.push(id)
  try {
    await fetch("/api/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command, repeats }),
    })
  } catch (e) {
    console.error("Live send failed:", command, e.message)
  }
  liveCommandQueue = liveCommandQueue.filter(x => x !== id)
}

let dropTimeout = null
function triggerDrop() {
  if (dropTimeout) return
  const dropCommands = ["red_fastblink", "turq_blink", "white_blink", "gold_blink", "turq_blink", "red_fastblink", "white_blink", "turq_blink"]
  showToast("💥 Drop!", "info")
  dropTimeout = setTimeout(() => { dropTimeout = null }, 1200)
  for (let i = 0; i < dropCommands.length; i++) {
    setTimeout(() => sendCommandLive(dropCommands[i], 1), i * 150)
  }
  setTimeout(() => sendCommandLive("nothing", 1), dropCommands.length * 150 + 200)
}

async function sendShowToBands() {
  const events = getTimelineEvents()
  if (events.length === 0) {
    showToast("Timeline is empty — generate a show first", "error")
    return
  }

  const btn = document.getElementById("btn-send-show")
  btn.disabled = true
  btn.textContent = "⏳ 0/" + events.length

  if (wakeBeforePlay) {
    document.getElementById("btn-wake-toggle").classList.add("sending")
    showToast("Sending 30s wake...")
    await sendWakeCommand()
    document.getElementById("btn-wake-toggle").classList.remove("sending")
  }

  showToast(`Starting show: ${events.length} commands`)
  let sent = 0
  const startWallTime = Date.now()

  for (let i = 0; i < events.length; i++) {
    const evt = events[i]

    const playAtMs = evt.time * 1000
    const elapsed = Date.now() - startWallTime
    const waitMs = Math.max(0, playAtMs - elapsed)

    if (waitMs > 0) {
      await new Promise(r => setTimeout(r, waitMs))
    }

    try {
      const res = await fetch("/api/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: evt.command, repeats: evt.repeats || 2 }),
      })
      const data = await res.json()
      if (data.success) sent++
      else console.error("Send failed:", evt.command, data.error)
    } catch (e) {
      console.error("Send error:", evt.command, e.message)
    }

    btn.textContent = `⏳ ${sent}/${events.length}`
  }

  btn.disabled = false
  btn.textContent = "📡 Send Show"
  showToast(`Show complete! Sent ${sent}/${events.length} commands.`)
}

async function handleAudioUpload(e) {
  const file = e.target.files[0]
  if (!file) return

  const formData = new FormData()
  formData.append("file", file)
  const res = await fetch("/api/upload", { method: "POST", body: formData })
  const data = await res.json()

  if (data.success) {
    uploadedAudioFilename = data.filename
    uploadedAudioFile = file
    await loadAudio(file)
    const genStatus = document.getElementById("auto-gen-status")
    if (genStatus) {
      genStatus.textContent = `🎵 ${file.name} — ${detectedBPM} BPM`
      genStatus.style.color = "var(--accent)"
    }
    document.getElementById("btn-auto-generate").style.borderColor = "var(--accent)"
    showToast("Audio loaded! Click Generate to create a show.")
  }
}

function buildColorPool(selectedCategories) {
  const colorMap = {
    gold: [], red: [], blue: [], white: [],
    turquoise: [], wine: [], magenta: [], effects: [],
  }
  for (const cmd of COMMANDS) {
    if (colorMap[cmd.category]) colorMap[cmd.category].push(cmd)
  }
  let pool = []
  for (const cat of selectedCategories) {
    if (colorMap[cat]) pool = pool.concat(colorMap[cat])
  }
  return pool
}

function pickForClass(energyClass, pool, effectPool, rng) {
  return pickForClassWithFamily(energyClass, pool, effectPool, rng, null)
}

function filterForSectionType(pool, sectionType) {
  if (sectionType === 'ambient') {
    return pool.filter(c => ['blue', 'white', 'turquoise', 'wine'].includes(c.category))
  }
  if (sectionType === 'percussion' || sectionType === 'hardcore') {
    return pool.filter(c => ['gold', 'red', 'white', 'magenta', 'effects'].includes(c.category))
  }
  return pool
}

function pickForClassWithFamily(energyClass, pool, effectPool, rng, familyColors) {
  const biasPool = familyColors && familyColors.length > 0
    ? pool.filter(c => familyColors.includes(c.category))
    : []
  const useBias = biasPool.length >= 2

  if (energyClass === ENERGY_CLASS.SILENCE) {
    return { id: "nothing", label: "Wake Up (30s)", color: "#888", repeats: 1, duration: 0.1 }
  }

  if (energyClass === ENERGY_CLASS.QUIET) {
    const quietColors = (useBias ? biasPool : pool).filter(c =>
      ["wine", "blue", "white", "magenta", "turquoise"].includes(c.category)
    )
    const src = quietColors.length > 0 ? quietColors : (useBias ? biasPool : pool)
    const cmd = src[Math.floor(rng() * src.length)]
    return { ...cmd, repeats: 3, duration: 1.2 }
  }

  if (energyClass === ENERGY_CLASS.MEDIUM) {
    const src = useBias ? biasPool : pool
    const cmd = src[Math.floor(rng() * src.length)]
    return { ...cmd, repeats: 2, duration: 0.5 }
  }

  if (energyClass === ENERGY_CLASS.LOUD) {
    const bright = (useBias ? biasPool : pool).filter(c =>
      ["gold", "red", "white", "magenta", "effects"].includes(c.category)
    )
    const src = bright.length > 0 ? bright : (useBias ? biasPool : pool)
    const cmd = src[Math.floor(rng() * src.length)]
    return { ...cmd, repeats: 2, duration: 0.2 }
  }

  if (energyClass === ENERGY_CLASS.PEAK) {
    const flashPool = effectPool.length > 0 ? effectPool : (useBias ? biasPool : pool)
    const cmd = flashPool[Math.floor(rng() * flashPool.length)]
    return { ...cmd, repeats: 1, duration: 0.1 }
  }

  const src = useBias ? biasPool : pool
  const cmd = src[Math.floor(rng() * src.length)]
  return { ...cmd, repeats: 2, duration: 0.3 }
}

async function autoGenerateShow() {
  if (!audioBuffer || !uploadedAudioFilename) {
    showToast("Upload an audio file first", "error")
    return
  }

  const bpm = detectedBPM || 120
  const style = document.getElementById("auto-style").value
  const colorCheckboxes = document.querySelectorAll(".color-option input:checked")
  const selectedCategories = Array.from(colorCheckboxes).map(cb => cb.value)
  let effectPool = buildColorPool(selectedCategories.filter(c => c === "effects"))
  let colorPool = buildColorPool(selectedCategories.filter(c => c !== "effects"))
  let fullPool = buildColorPool(selectedCategories)

  if (!document.getElementById("include-wild-combo").checked) {
    const skip = [c => c.id === "wild_combo", c => c.id.startsWith("rand_")]
    const filterCommands = arr => arr.filter(c => !skip.some(fn => fn(c)))
    fullPool = filterCommands(fullPool); colorPool = filterCommands(colorPool); effectPool = filterCommands(effectPool)
  }

  if (fullPool.length === 0) {
    showToast("Select at least one color", "error")
    return
  }

  document.getElementById("auto-generate-modal").classList.add("hidden")
  showToast("Analyzing audio...")

  try {
    const analysis = analyzeAudioDeep(audioBuffer)
    const beatInterval = 60 / (detectedBPM || 120)

    let seed = Date.now()
    const rng = () => {
      seed = (seed * 16807) % 2147483647
      return (seed - 1) / 2147483646
    }

    const timeline = []
    const sections = analysis.sections
    console.log(`autoGenerateShow: ${sections.length} sections, ${Object.keys(analysis.familyInfo || {}).length} families, style=${style}, pool=${fullPool.length} commands`)

    if (sections.length === 0) {
      showToast("No audio sections found — try a different song", "error")
      return
    }

    // Assign color palettes per family for coordinated repeated sections
    const familyColors = {}
    if (analysis.familyInfo) {
      const palettePool = [
        ['gold', 'white'],
        ['red', 'gold', 'white'],
        ['blue', 'white', 'turquoise'],
        ['magenta', 'turquoise', 'white'],
        ['wine', 'gold', 'red'],
        ['turquoise', 'blue', 'white'],
        ['white', 'gold', 'magenta'],
        ['red', 'magenta', 'white'],
        ['blue', 'wine', 'magenta'],
        ['gold', 'turquoise', 'white'],
      ]
      let palIdx = 0
      for (const fid of Object.keys(analysis.familyInfo)) {
        const info = analysis.familyInfo[fid]
        const pal = palettePool[palIdx % palettePool.length]
        familyColors[fid] = pal
        palIdx++
        // Give same type name the same palette (so Verse A and Verse A repeat match)
        if (info.typeName) {
          const sameType = Object.entries(analysis.familyInfo).filter(([,v]) => v.typeName === info.typeName)
          if (sameType.length > 1) {
            for (const [sfid] of sameType) familyColors[sfid] = pal
          }
        }
      }
    }

    const familyOccurrences = {}
    for (const section of sections) {
      const energyClass = section.energyClass
      const sectionType = section.sectionType || 'verse'
      const famColors = familyColors[section.familyId] || null
      familyOccurrences[section.familyId] = (familyOccurrences[section.familyId] || 0) + 1
      const occurrence = familyOccurrences[section.familyId]
      const isRepeat = occurrence > 1

      const secPool = filterForSectionType(fullPool, sectionType)
      const cmd = pickForClassWithFamily(energyClass, secPool, effectPool, rng, famColors)
      if (!cmd) continue

      const isFirstSection = section.time < 0.1
      if (isFirstSection && (energyClass === ENERGY_CLASS.SILENCE || energyClass === ENERGY_CLASS.QUIET)) {
        const introCmd = pickForClassWithFamily(ENERGY_CLASS.QUIET, secPool, effectPool, rng, null)
        if (introCmd) {
          timeline.push({
            time: roundTime(section.time),
            command: introCmd.id,
            label: introCmd.label || introCmd.id,
            color: introCmd.color,
            repeats: 2,
            duration: 0.8,
          })
        }
        continue
      }

      if (style === "silence_respect") {
        if (energyClass === ENERGY_CLASS.SILENCE) {
          timeline.push({
            time: roundTime(section.time),
            command: "nothing",
            label: "Off",
            color: "#333",
            repeats: 1,
            duration: 0.1,
          })
          continue
        }

        const energies = section.frameEnergies
        const peakRatio = section.peakRatio
        const numSteps = Math.min(8, Math.ceil(section.duration / 0.2))
        const stepTime = section.duration / numSteps
        const fadeRestSteps = isRepeat ? 2 : 0

        for (let s = 0; s < numSteps; s++) {
          const t = section.time + s * stepTime
          const frameIdx = Math.floor((s / numSteps) * energies.length)
          const localEnergy = energies[Math.min(frameIdx, energies.length - 1)]
          const isPrePeak = (s / numSteps) < peakRatio

          if (localEnergy < 0.05 && !(fadeRestSteps > 0 && s >= numSteps - fadeRestSteps)) continue

          let subCmd, repeats, duration

          if (fadeRestSteps > 0 && s >= numSteps - fadeRestSteps) {
            const stepInFade = s - (numSteps - fadeRestSteps)
            if (stepInFade === 0) {
              const fadeCmd = pickForClassWithFamily(ENERGY_CLASS.QUIET, secPool, effectPool, rng, famColors)
              subCmd = fadeCmd || { id: "white_fade", label: "White Fade", color: "#FFFFFF" }
              repeats = 2
              duration = Math.max(0.5, stepTime * 0.8)
            } else {
              timeline.push({
                time: roundTime(t),
                command: "nothing",
                label: "Rest",
                color: "#222",
                repeats: 1,
                duration: stepTime,
              })
              continue
            }
          } else if (isPrePeak) {
            const fadeIn = localEnergy < 0.3
            const buildUp = localEnergy >= 0.3
            if (fadeIn) {
              const famPool = famColors ? secPool.filter(c => famColors.includes(c.category)) : secPool
              const fp = famPool.length > 0 ? famPool : secPool
              const quietColors = fp.filter(c =>
                ["blue", "white", "turquoise", "wine"].includes(c.category)
              )
              const src = quietColors.length > 0 ? quietColors : (famPool.length > 0 ? famPool : secPool)
              subCmd = src[Math.floor(rng() * src.length)]
              repeats = 2
              duration = Math.max(0.3, stepTime * 0.7)
            } else {
              const fp2 = famColors ? secPool.filter(c => famColors.includes(c.category)) : secPool
              subCmd = (fp2.length > 0 ? fp2 : secPool)[Math.floor(rng() * (fp2.length > 0 ? fp2.length : secPool.length))]
              repeats = 2
              duration = 0.2
            }
          } else {
            const afterPeak = localEnergy < 0.2
            if (afterPeak) {
              const fp3 = famColors ? secPool.filter(c => famColors.includes(c.category)) : secPool
              const pool3 = fp3.length > 0 ? fp3 : secPool
              const quietColors = pool3.filter(c =>
                ["blue", "wine", "white"].includes(c.category)
              )
              const src = quietColors.length > 0 ? quietColors : pool3
              subCmd = src[Math.floor(rng() * src.length)]
              repeats = 2
              duration = Math.max(0.4, stepTime * 0.8)
            } else if (localEnergy > 0.7 && s === Math.round(peakRatio * numSteps)) {
              subCmd = cmd
              repeats = 1
              duration = 0.08
            } else {
              const fp4 = famColors ? secPool.filter(c => famColors.includes(c.category)) : secPool
              subCmd = (fp4.length > 0 ? fp4 : secPool)[Math.floor(rng() * (fp4.length > 0 ? fp4.length : secPool.length))]
              repeats = localEnergy > 0.5 ? 1 : 2
              duration = localEnergy > 0.5 ? 0.12 : 0.3
            }
          }

          if (subCmd) {
            timeline.push({
              time: roundTime(t),
              command: subCmd.id,
              label: subCmd.label || subCmd.id,
              color: subCmd.color,
              repeats,
              duration,
              familyType: section.familyType,
            })
          }
        }
        continue
      }

      if (energyClass === ENERGY_CLASS.SILENCE) continue
      if (energyClass === ENERGY_CLASS.QUIET) {
        timeline.push({
          time: roundTime(section.time),
          command: cmd.id,
          label: cmd.label || cmd.id,
          color: cmd.color,
          repeats: 3,
          duration: Math.min(section.duration, 2.0),
          familyType: section.familyType,
        })
        continue
      }

      if (energyClass === ENERGY_CLASS.PEAK && style !== "slow_fade") {
        const numFlashes = Math.min(4, Math.ceil(section.duration / 0.12))
        for (let f = 0; f < numFlashes; f++) {
          const subCmd = f === 0 ? cmd : pickForClassWithFamily(ENERGY_CLASS.LOUD, secPool, effectPool, rng, famColors)
          if (subCmd) {
            timeline.push({
              time: roundTime(section.time + f * 0.12),
              command: subCmd.id,
              label: subCmd.label || subCmd.id,
              color: subCmd.color,
              repeats: 1,
              duration: 0.06,
            })
          }
        }
        continue
      }

      const beatBeats = Math.max(1, Math.round(section.duration / beatInterval))
      const beats = Math.min(beatBeats, 6)
      const step = section.duration / beats
      for (let b = 0; b < beats; b++) {
        const subCmd = b === 0 ? cmd : pickForClassWithFamily(energyClass, secPool, effectPool, rng, famColors)
        if (subCmd) {
          timeline.push({
            time: roundTime(section.time + b * step),
            command: subCmd.id,
            label: subCmd.label || subCmd.id,
            color: subCmd.color,
            repeats: energyClass === ENERGY_CLASS.LOUD ? 1 : 2,
            duration: energyClass === ENERGY_CLASS.LOUD ? 0.12 : 0.3,
          })
        }
      }
    }

    timeline.sort((a, b) => a.time - b.time)
    console.log(`autoGenerateShow: generated ${timeline.length} timeline events`)

    if (timeline.length === 0) {
      showToast("No commands generated — audio may be too quiet", "error")
      return
    }

    const duration = audioBuffer.duration
    clearTimeline()
    setTimelineDuration(Math.ceil(duration))
    loadTimelineEvents(timeline)
    console.log("autoGenerateShow: timeline loaded, events =", getTimelineEvents().length)
    currentShowName = `${currentShowName} (Auto)`
    document.getElementById("show-name").value = currentShowName
    showDirty = true
    setTimeout(() => {
      showToast(`Generated ${timeline.length} commands from audio analysis!`)
    }, 100)
  } catch (e) {
    console.error("Auto-generate error:", e)
    showToast("Generation failed: " + e.message, "error")
  }
}

function roundTime(t) {
  return Math.round(t * 100) / 100
}

function updateTitle() {
  document.title = `${currentShowName} - PixMob Show Creator`
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container")
  const toast = document.createElement("div")
  toast.className = `toast toast-${type}`
  toast.textContent = message
  container.appendChild(toast)
  setTimeout(() => {
    toast.classList.add("fade-out")
    setTimeout(() => toast.remove(), 300)
  }, 2500)
}

/* === Mic Mode === */
let micStream = null
let micAnalyser = null
let micAudioCtx = null
let micAnimationId = null
let micActive = false
let lastMicCommandTime = 0
let micManualMode = null
let micEnergyMode = "silence"
let micEnergyModeSince = 0
let lastStrobeTime = 0
let strobeStep = 0
let prevFreqData = null
let prevBandEnergies = null
let prevFreqMagnitudes = null
let micOnsetHistory = []
let micLongProfile = [] // 8s rolling profile (snapshots every ~500ms)
let micSectionStartTime = 0
let micSectionProfile = null
let micKnownSections = []
let sectionSequence = []
let micSectionConfidence = 1
let micProfileAge = 0
let micOnsetStrengthBuffer = []
let micDownbeatPhase = 0
let micLastBeatTime = 0
let micBeatInterval = 0
let micBeatConfidence = 0
let micBeatLocked = false
let micBeatPhase = 0
let micDownbeatEnergy = []
let micOnsetTimes = []
let micChromaBuffer = []
let micTempoConfidence = 0
let micDetectedKey = null
let micDetectedMood = null
let micMoodColors = null
let micManualSection = null

const NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
const A4 = 440

const KrumhanslMajor = [6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88]
const KrumhanslMinor = [6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17]

function freqToPitchClass(freq) {
  if (freq <= 0) return -1
  const n = Math.round(12 * Math.log2(freq / A4) + 69)
  return ((n % 12) + 12) % 12
}

function computeChroma(freqData, sampleRate) {
  const binFreq = sampleRate / (micAnalyser ? micAnalyser.fftSize : 1024)
  const chroma = new Array(12).fill(0)
  for (let i = 1; i < freqData.length; i++) {
    const freq = i * binFreq
    if (freq < 80 || freq > 4000) continue
    const pc = freqToPitchClass(freq)
    if (pc >= 0) chroma[pc] += freqData[i] / 255
  }
  const max = Math.max(...chroma, 0.001)
  return chroma.map(v => v / max)
}

function detectKey(chroma) {
  let bestCorr = -Infinity
  let bestKey = 0
  let bestMode = 'major'
  for (let shift = 0; shift < 12; shift++) {
    let corrMajor = 0, corrMinor = 0
    for (let i = 0; i < 12; i++) {
      const idx = (i + shift) % 12
      corrMajor += chroma[idx] * KrumhanslMajor[i]
      corrMinor += chroma[idx] * KrumhanslMinor[i]
    }
    if (corrMajor > bestCorr) { bestCorr = corrMajor; bestKey = shift; bestMode = 'major' }
    if (corrMinor > bestCorr) { bestCorr = corrMinor; bestKey = shift; bestMode = 'minor' }
  }
  const confidence = Math.min(1, Math.max(0, (bestCorr - 10) / 20))
  return { key: bestKey, mode: bestMode, name: NOTE_NAMES[bestKey] + ' ' + bestMode, confidence }
}

function updateBeatTracking(now, features) {
  if (features.onsetStrength > 0.012) {
    micOnsetTimes.push(now)
    micDownbeatEnergy.push({ time: now, energy: features.bandEnergies.bass + features.totalEnergy })
  }
  while (micOnsetTimes.length > 0 && now - micOnsetTimes[0] > 4000) {
    micOnsetTimes.shift()
    micDownbeatEnergy.shift()
  }

  if (micOnsetTimes.length < 5) { micBeatLocked = false; return }

  const intervals = []
  for (let i = 4; i < micOnsetTimes.length; i++) {
    for (let j = i - 4; j < i; j++) {
      const dt = (micOnsetTimes[i] - micOnsetTimes[j]) / (i - j)
      if (dt > 0.25 && dt < 2.0) intervals.push(dt)
    }
  }
  if (intervals.length < 4) { micBeatLocked = false; return }

  const hist = {}
  for (const iv of intervals) {
    const ms = Math.round(iv * 1000)
    const rounded = Math.round(ms / 10) * 10
    hist[rounded] = (hist[rounded] || 0) + 1
  }
  let bestInterval = 500, bestCount = 0
  for (const [ms, count] of Object.entries(hist)) {
    if (count > bestCount) { bestInterval = parseInt(ms); bestCount = count }
  }

  const intervalSec = bestInterval / 1000
  const bpm = Math.round(60 / intervalSec)
  if (bpm < 60 || bpm > 180) { micBeatLocked = false; return }

  const totalPossible = intervals.length
  const confidence = Math.min(1, bestCount / totalPossible * 3)
  micBeatInterval = intervalSec * 1000
  micBeatConfidence = confidence
  micBeatLocked = confidence > 0.35

  if (micBeatLocked) {
    const lastOnset = micOnsetTimes[micOnsetTimes.length - 1]
    const timeSinceLastOnset = now - lastOnset
    micBeatPhase = (timeSinceLastOnset / (intervalSec * 1000)) % 1
    if (micBeatPhase > 0.95) micBeatPhase = 0
    micLastBeatTime = lastOnset

    if (micDownbeatEnergy.length >= 8) {
      const measureLen = 4
      const energies = []
      for (let i = 0; i < measureLen && i < micDownbeatEnergy.length; i++) {
        const idx = micDownbeatEnergy.length - 1 - i
        energies.push(micDownbeatEnergy[idx].energy)
      }
      const maxAt = energies.indexOf(Math.max(...energies))
      micDownbeatPhase = maxAt >= 0 ? maxAt : 0
    }
  }
}

function getTempoInfo() {
  return {
    bpm: micBeatInterval > 0 ? Math.round(60000 / micBeatInterval) : 120,
    confidence: micBeatConfidence,
    locked: micBeatLocked,
    phase: micBeatPhase,
    interval: micBeatInterval,
    nextBeat: micLastBeatTime + micBeatInterval - performance.now(),
    downbeat: micDownbeatPhase
  }
}

function classifyMood(keyInfo, tempo, features) {
  const isMinor = keyInfo.mode === 'minor'
  const isMajor = keyInfo.mode === 'major'
  const fast = tempo.bpm > 120
  const slow = tempo.bpm < 85
  const highFlux = features.avgFlux > 0.04
  const highEnergy = features.rms > 0.2
  const lowEnergy = features.rms < 0.08

  if (isMinor && fast && highEnergy) return { mood: 'aggressive', colors: ['red', 'gold', 'white', 'magenta'] }
  if (isMinor && fast) return { mood: 'intense', colors: ['red', 'gold', 'magenta', 'white'] }
  if (isMinor && slow && lowEnergy) return { mood: 'melancholic', colors: ['blue', 'wine', 'turquoise', 'magenta'] }
  if (isMinor && slow) return { mood: 'dark', colors: ['wine', 'blue', 'magenta'] }
  if (isMajor && fast && highEnergy) return { mood: 'party', colors: ['gold', 'white', 'magenta', 'red', 'turquoise'] }
  if (isMajor && fast) return { mood: 'happy', colors: ['gold', 'white', 'turquoise', 'magenta'] }
  if (isMajor && slow && lowEnergy) return { mood: 'calm', colors: ['blue', 'white', 'turquoise'] }
  if (isMajor && slow) return { mood: 'epic', colors: ['white', 'gold', 'blue', 'turquoise'] }
  if (highFlux && highEnergy) return { mood: 'chaotic', colors: ['red', 'gold', 'white', 'magenta'] }
  if (lowEnergy) return { mood: 'peaceful', colors: ['blue', 'wine', 'turquoise'] }
  return { mood: 'neutral', colors: ['gold', 'red', 'blue', 'white', 'turquoise', 'wine', 'magenta'] }
}

function extractMicFeatures(freqData, timeData) {
  const len = freqData.length
  const n = timeData.length

  let rmsSum = 0
  let zcr = 0
  for (let i = 0; i < n; i++) {
    const v = (timeData[i] - 128) / 128
    rmsSum += v * v
    if (i > 0 && ((timeData[i] - 128) * (timeData[i - 1] - 128) < 0)) zcr++
  }
  const rms = Math.sqrt(rmsSum / n)
  const zcrRate = zcr / n

  const bins = [
    { name: "subBass", start: 0, end: 2 },
    { name: "bass", start: 2, end: 7 },
    { name: "lowMid", start: 7, end: 14 },
    { name: "highMid", start: 14, end: 48 },
    { name: "high", start: 48, end: 130 },
    { name: "veryHigh", start: 130, end: len - 1 },
  ]

  const magnitudes = new Float64Array(len)
  let totalSum = 0
  let weightedFreqSum = 0
  let cumulativeSum = 0
  let rolloffBin = len - 1
  for (let i = 0; i < len; i++) {
    const val = freqData[i] / 255
    magnitudes[i] = val
    totalSum += val
    weightedFreqSum += val * i
  }
  const totalEnergy = totalSum / len
  const spectralCentroid = totalSum > 0.001 ? weightedFreqSum / (totalSum * len) : 0

  const rolloffThreshold = totalSum * 0.85
  for (let i = 0; i < len; i++) {
    cumulativeSum += magnitudes[i]
    if (cumulativeSum >= rolloffThreshold) { rolloffBin = i; break }
  }
  const spectralRolloff = rolloffBin / len

  let flatnessNumerator = 0
  let flatnessDenominator = 0
  for (let i = 1; i < len; i++) {
    if (magnitudes[i] > 0.001) {
      flatnessNumerator += Math.log(magnitudes[i])
      flatnessDenominator++
    }
  }
  const spectralFlatness = flatnessDenominator > 0
    ? Math.exp(flatnessNumerator / flatnessDenominator) / (totalSum / len + 0.001)
    : 0

  const bandEnergies = {}
  for (const b of bins) {
    let s = 0, gp = 0, count = 0
    for (let i = b.start; i <= b.end && i < len; i++) {
      const v = magnitudes[i]
      s += v
      if (v > 0.001) gp += Math.log(v)
      count++
    }
    bandEnergies[b.name] = s / count
    bandEnergies[b.name + '_flatness'] = count > 0 && s > 0
      ? Math.exp(gp / count) / (s / count + 0.001)
      : 0
  }

  let flux = 0
  if (prevFreqData) {
    for (let i = 0; i < len; i++) flux += Math.abs(freqData[i] - prevFreqData[i])
    flux /= len * 255
  }
  prevFreqData = new Uint8Array(freqData)

  const bandFlux = {}
  for (const b of bins) {
    let bf = 0
    const count = b.end - b.start + 1
    if (prevBandEnergies) {
      const cur = bandEnergies[b.name]
      const prev = prevBandEnergies[b.name] || 0
      bf = Math.abs(cur - prev)
    }
    bandFlux[b.name] = bf
  }
  prevBandEnergies = { ...bandEnergies }

  let onsetStrength = 0
  if (prevFreqMagnitudes) {
    let posFlux = 0
    for (let i = 0; i < len; i++) {
      const diff = magnitudes[i] - prevFreqMagnitudes[i]
      if (diff > 0) posFlux += diff
    }
    onsetStrength = posFlux / len
  }
  prevFreqMagnitudes = magnitudes

  return {
    rms, zcrRate, totalEnergy, spectralCentroid, flux,
    spectralRolloff, spectralFlatness,
    bandEnergies, bandFlux, onsetStrength
  }
}

function computeSectionProfile(history, windowMs) {
  const now = performance.now()
  const window = history.filter(h => now - h.time < windowMs && now - h.time > 0)
  if (window.length < 10) return null

  const avg = (key) => window.reduce((s, f) => s + (f[key] || 0), 0) / window.length
  const avgBand = (band) => {
    let sum = 0, n = 0
    for (const f of window) {
      const v = f.bandEnergies && f.bandEnergies[band]
      if (v !== undefined) { sum += v; n++ }
    }
    return n > 0 ? sum / n : 0
  }

  return {
    rms: avg('rms'),
    totalEnergy: avg('totalEnergy'),
    flux: avg('flux'),
    spectralCentroid: avg('spectralCentroid'),
    spectralRolloff: avg('spectralRolloff'),
    spectralFlatness: avg('spectralFlatness'),
    zcrRate: avg('zcrRate'),
    onsetStrength: avg('onsetStrength'),
    bass: avgBand('bass'),
    lowMid: avgBand('lowMid'),
    highMid: avgBand('highMid'),
    high: avgBand('high'),
    subBass: avgBand('subBass'),
  }
}

function profileSimilarity(a, b) {
  if (!a || !b) return 0
  const keys = ['rms','totalEnergy','flux','spectralCentroid','spectralRolloff','spectralFlatness','zcrRate','onsetStrength','bass','lowMid','highMid']
  let sim = 0, w = 0
  for (const k of keys) {
    const va = a[k] || 0, vb = b[k] || 0
    const maxV = Math.max(Math.abs(va), Math.abs(vb), 0.01)
    const diff = Math.abs(va - vb) / maxV
    sim += Math.max(0, 1 - diff)
    w++
  }
  return w > 0 ? sim / w : 0
}

function profileEnergyLevel(p) {
  if (!p) return 'silence'
  const e = p.totalEnergy
  const b = p.bass || 0
  const f = p.flux || 0
  const o = p.onsetStrength || 0
  const fl = p.spectralFlatness || 0

  if (e < 0.015) return 'silence'
  if (f > 0.08 && p.zcrRate > 0.12 && e > 0.05) return 'noise'
  if (e < 0.04) return 'ambient'
  if (b > 0.04 && f > 0.03 && f < 0.08 && o > 0.01) return 'groove'
  if (e > 0.08 && f > 0.04 && o > 0.015) return 'drive'
  if (e > 0.08 && f < 0.04) return 'ambient'
  if (e > 0.05 && b > 0.03 && f > 0.02) return 'groove'
  if (e > 0.04) return 'ambient'
  return 'ambient'
}

const SECTION_MIN_HOLD_MS = 5000

function detectSectionChange() {
  const now = performance.now()
  const recent2s = computeSectionProfile(micHistory, 2000)
  const prev2s = computeSectionProfile(micHistory, 4000)
  if (!recent2s || !prev2s) return { changed: false }

  const sim = profileSimilarity(recent2s, prev2s)

  const recentEnergy = recent2s.totalEnergy
  const prevEnergy = prev2s.totalEnergy
  const energyJump = recentEnergy - prevEnergy

  const newLevel = profileEnergyLevel(recent2s)
  const oldLevel = profileEnergyLevel(prev2s)

  if (newLevel !== oldLevel && sim < 0.65) {
    return { changed: true, mode: newLevel, sim }
  }

  if (energyJump > 0.04 && sim < 0.65) {
    return { changed: true, mode: 'buildup', sim }
  }

  if (energyJump < -0.03 && sim < 0.65) {
    return { changed: true, mode: 'breakdown', sim }
  }

  if (recentEnergy > 0.08 && prevEnergy < 0.05 && sim < 0.6) {
    return { changed: true, mode: 'drop', sim }
  }

  return { changed: false, mode: null }
}

function detectRecentSpike() {
  if (micHistory.length < 3) return false
  const last3 = micHistory.slice(-3)
  const avgEnergy = last3.reduce((s, f) => s + f.totalEnergy, 0) / last3.length
  if (avgEnergy < 0.03) return false
  for (const f of last3) {
    if (f.onsetStrength > 0.04 || f.flux > 0.06) return true
  }
  return false
}

function classifySectionLong(now) {
  if (micHistory.length < 30) return { mode: 'silence', confidence: 0.5 }

  const recent4s = computeSectionProfile(micHistory, 4000)
  if (!recent4s) return { mode: micEnergyMode, confidence: 0.5 }

  const prior4s = computeSectionProfile(micHistory, 8000)
  const sectionAge = now - micSectionStartTime

  const lastSnapshot = micLongProfile.length > 0
    ? micLongProfile[micLongProfile.length - 1]
    : null

  if (!lastSnapshot || now - lastSnapshot.time > 500) {
    micLongProfile.push({ time: now, profile: recent4s })
  }
  while (micLongProfile.length > 0 && now - micLongProfile[0].time > 8000) micLongProfile.shift()

  const recent2s = computeSectionProfile(micHistory, 2000)
  const isNowSilence = recent2s && recent2s.totalEnergy < 0.015
  if (isNowSilence && micEnergyMode !== 'silence') {
    micSectionProfile = recent2s
    micSectionStartTime = now
    micSectionConfidence = 0.9
    return { mode: 'silence', confidence: 0.9 }
  }

  const sectionChange = detectSectionChange()
  if (sectionChange.changed) {
    micSectionProfile = recent4s
    micSectionStartTime = now
    micSectionConfidence = 0.85
    return { mode: sectionChange.mode, confidence: 0.85 }
  }

  if (sectionAge < SECTION_MIN_HOLD_MS && micSectionProfile) {
    const level = profileEnergyLevel(recent4s)
    if (level !== micEnergyMode) {
      micSectionProfile = recent4s
      micSectionStartTime = now
      micSectionConfidence = 0.8
      return { mode: level, confidence: 0.8 }
    }
    return { mode: micEnergyMode, confidence: micSectionConfidence }
  }

  const simToSection = micSectionProfile ? profileSimilarity(recent4s, micSectionProfile) : 0
  if (simToSection > 0.7 && sectionAge < 12000) {
    micSectionConfidence = Math.min(1, micSectionConfidence + 0.05)
    return { mode: micEnergyMode, confidence: micSectionConfidence }
  }

  const level = profileEnergyLevel(recent4s)
  if (level === micEnergyMode) {
    micSectionConfidence = Math.min(1, micSectionConfidence + 0.03)
    return { mode: micEnergyMode, confidence: micSectionConfidence }
  }

  const profile = computeSectionProfile(micHistory, 4000)
  if (!profile) return { mode: micEnergyMode, confidence: 0.5 }

  let bestSim = 0
  let bestMatch = null
  for (const stored of micKnownSections) {
    const sim = profileSimilarity(profile, stored.profile)
    if (sim > bestSim) { bestSim = sim; bestMatch = stored }
  }

  if (bestMatch && bestSim > 0.75) {
    micSectionProfile = bestMatch.profile
    micSectionStartTime = now
    micSectionConfidence = 0.85
    return { mode: bestMatch.mode, confidence: 0.85 }
  }

  let newMode = profileEnergyLevel(profile)

  micSectionProfile = profile
  micSectionStartTime = now
  micSectionConfidence = 0.7

  micKnownSections.push({ mode: newMode, profile: { ...profile }, time: now })
  if (micKnownSections.length > 20) micKnownSections.shift()

  return { mode: newMode, confidence: 0.7 }
}

function startMicMode() {
  const startBtn = document.getElementById("btn-mic-start")
  const stopBtn = document.getElementById("btn-mic-stop")
  const status = document.getElementById("mic-status")
  const meter = document.getElementById("mic-meter-fill")
  status.textContent = "Requesting mic access..."
  meter.style.width = "0%"
  meter.style.background = "var(--accent)"

  navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
    micStream = stream
    micAudioCtx = new (window.AudioContext || window.webkitAudioContext)()
    const source = micAudioCtx.createMediaStreamSource(stream)
    micAnalyser = micAudioCtx.createAnalyser()
    micAnalyser.fftSize = 1024
    source.connect(micAnalyser)
    micActive = true
    lastMicCommandTime = 0
    micHistory = []
    setMicMode("auto")
    startBtn.classList.add("hidden")
    stopBtn.classList.remove("hidden")
    status.textContent = "Listening..."
    status.style.color = "var(--success)"
    showToast("Mic mode started — make some noise!")
    processMicAudio()
  }).catch(err => {
    status.textContent = "Mic access denied: " + err.message
    status.style.color = "var(--danger)"
    showToast("Mic access denied", "error")
  })
}

function setMicMode(mode) {
  const wasManual = micManualMode !== null
  micManualMode = mode
  if (mode === "auto" || mode === null) {
    lastMicCommandTime = performance.now() - 1000
    micManualSection = null
    const now = performance.now()
    micSectionStartTime = now
    micEnergyModeSince = now
    micSectionProfile = null
    micSectionConfidence = 0
    if (wasManual) {
      sendCommandLive("turq_blink", 1)
    }
  }
  if (mode !== "strobe_wr") strobeStep = 0
  const badge = document.getElementById("mic-mode-badge")
  if (!badge) return
  const labels = { strobe_w: "STROBE W", strobe_wr: "STROBE ALL", strobe_r: "STROBE R", strobe_t: "STROBE T", fade: "FADE", random: "RANDOM", auto: "AUTO" }
  const colors = { strobe_w: "#FFFFFF", strobe_wr: "#FF6666", strobe_r: "#FF0000", strobe_t: "#00CED1", fade: "#44ff88", random: "#FFD700", auto: "var(--accent)" }
  badge.textContent = labels[mode || "auto"]
  badge.style.background = colors[mode || "auto"]
  badge.style.color = (mode === "random" || mode === "strobe_w") ? "#000" : "#fff"
}

function stopMicMode() {
  micActive = false
  if (micAnimationId) cancelAnimationFrame(micAnimationId)
  micAnimationId = null
  if (micStream) micStream.getTracks().forEach(t => t.stop())
  micStream = null
  if (micAudioCtx) micAudioCtx.close()
  micAudioCtx = null
  micAnalyser = null
  micHistory = []
  prevFreqData = null
  prevBandEnergies = null
  prevFreqMagnitudes = null
  micOnsetHistory = []
  micOnsetStrengthBuffer = []
  micOnsetTimes = []
  micDownbeatEnergy = []
  micBeatLocked = false
  micBeatConfidence = 0
  micBeatInterval = 0
  micBeatPhase = 0
  micLastBeatTime = 0
  micChromaBuffer = []
  micDetectedKey = null
  micDetectedMood = null
  micMoodColors = null
  micLongProfile = []
  micKnownSections = []
  micSectionProfile = null
  micSectionStartTime = 0

  const startBtn = document.getElementById("btn-mic-start")
  const stopBtn = document.getElementById("btn-mic-stop")
  const status = document.getElementById("mic-status")
  const meter = document.getElementById("mic-meter-fill")
  startBtn.classList.remove("hidden")
  stopBtn.classList.add("hidden")
  status.textContent = "Stopped"
  status.style.color = "var(--text-secondary)"
  meter.style.width = "0%"
}

function getMicPool() {
  const cbs = document.querySelectorAll("#mic-modal .color-option input:checked")
  const cats = Array.from(cbs).map(cb => cb.value)
  let ep = buildColorPool(cats.filter(c => c === "effects"))
  let cp = buildColorPool(cats.filter(c => c !== "effects"))
  let fp = buildColorPool(cats)
  if (!document.getElementById("mic-include-wild-combo").checked) {
    const f = a => a.filter(c => c.id !== "wild_combo")
    fp = f(fp); cp = f(cp); ep = f(ep)
  }
  const moodFp = micMoodColors ? fp.filter(c => micMoodColors.includes(c.category)) : fp
  return { fullPool: fp, colorPool: cp, effectPool: ep, moodPool: moodFp.length > 0 ? moodFp : fp }
}

function processMicAudio() {
  if (!micActive || !micAnalyser) { micAnimationId = null; return }

  const freqData = new Uint8Array(micAnalyser.frequencyBinCount)
  const timeData = new Uint8Array(micAnalyser.fftSize)
  micAnalyser.getByteFrequencyData(freqData)
  micAnalyser.getByteTimeDomainData(timeData)

  const features = extractMicFeatures(freqData, timeData)
  const now = performance.now()

  micHistory.push({ time: now, ...features })
  while (micHistory.length > 0 && now - micHistory[0].time > 3000) {
    micHistory.shift()
  }

  updateBeatTracking(now, features)

  if (features.onsetStrength > 0.015) {
    micOnsetHistory.push(now)
  }
  while (micOnsetHistory.length > 0 && now - micOnsetHistory[0] > 3000) micOnsetHistory.shift()

  if (micHistory.length % 60 === 0) {
    const sampleRate = micAudioCtx ? micAudioCtx.sampleRate : 44100
    const chroma = computeChroma(freqData, sampleRate)
    micChromaBuffer.push(chroma)
    if (micChromaBuffer.length > 10) micChromaBuffer.shift()
    if (micChromaBuffer.length >= 5) {
      const avgChroma = Array(12).fill(0)
      for (const c of micChromaBuffer) for (let i = 0; i < 12; i++) avgChroma[i] += c[i]
      const maxC = Math.max(...avgChroma, 0.001)
      const normChroma = avgChroma.map(v => v / (maxC * micChromaBuffer.length))
      micDetectedKey = detectKey(normChroma)
    }
    const tempo = getTempoInfo()
    const moodResult = classifyMood(
      micDetectedKey || { key:0, mode:'major', name:'C major', confidence:0 },
      tempo,
      { rms: features.rms, avgFlux: features.flux }
    )
    micDetectedMood = moodResult.mood
    micMoodColors = moodResult.colors
  }

  const pct = Math.min(100, features.rms * 200)
  const meter = document.getElementById("mic-meter-fill")
  if (meter) {
    meter.style.width = pct + "%"
    if (features.rms > 0.4) meter.style.background = "#FF4444"
    else if (features.rms > 0.25) meter.style.background = "#FF6600"
    else if (features.rms > 0.12) meter.style.background = "#44ff88"
    else if (features.rms > 0.06) meter.style.background = "#FFD700"
    else meter.style.background = "var(--accent)"
  }

  if (micHistory.length % 30 === 0) {
    const section = classifySectionLong(now)
    if (section.mode !== micEnergyMode) {
      sectionSequence.push(micEnergyMode)
      if (sectionSequence.length > 50) sectionSequence.shift()
      const seqStr = sectionSequence.join(",")
      if (seqStr.includes(section.mode)) {
        const idx = seqStr.indexOf(section.mode)
        const prev = seqStr.substring(0, idx).split(",").filter(Boolean).pop()
        if (prev && sectionSequence.filter(s => s === section.mode).length > 1) {
          console.debug(`♻️ Repeat section: ${section.mode}`)
        }
      }
      console.debug(`Section: ${micEnergyMode} → ${section.mode} (conf ${section.confidence.toFixed(2)})`)
      micEnergyMode = section.mode
      micEnergyModeSince = now
    }
  }

  let nowMode = micEnergyMode
  if (micManualSection) nowMode = micManualSection

  let intervalMs = 200
  if ((nowMode === "drop" || nowMode === "peak")) intervalMs = 60
  else if (nowMode === "percussion") intervalMs = 80
  else if (nowMode === "buildup") intervalMs = 100
  else if (nowMode === "drive") intervalMs = 150
  else if (nowMode === "groove") intervalMs = 180
  else if (nowMode === "breakdown") intervalMs = 250
  else if (nowMode === "ambient") intervalMs = 200
  else if (nowMode === "noise") intervalMs = 120
  else if (nowMode === "silence") intervalMs = 400

  if (micBeatLocked && micBeatConfidence > 0.35) {
    const beatMs = micBeatInterval
    const subdivisions = [beatMs, beatMs / 2, beatMs / 4, beatMs / 3]
    const best = subdivisions.reduce((best, sub) =>
      Math.abs(sub - intervalMs) < Math.abs(best - intervalMs) ? sub : best
    , intervalMs)
    intervalMs = Math.max(40, Math.min(1000, Math.round(best)))
  }

  const msSinceLast = now - lastMicCommandTime
  const modeAge = now - micEnergyModeSince
  let shouldSend = false
  const strobeActive = micManualMode === "strobe_w" || micManualMode === "strobe_wr" || micManualMode === "strobe_r" || micManualMode === "strobe_t"
  if (strobeActive && msSinceLast >= 50) shouldSend = true
  else if (micManualMode === "fade" && msSinceLast >= 400) shouldSend = true
  else if (micManualMode === "random" && msSinceLast >= 250) shouldSend = true
  else if (micManualMode === "auto" || !micManualMode) {
    if (msSinceLast >= intervalMs) shouldSend = true
  }

  if (shouldSend) {
    const pool = getMicPool()
    let cmd = null
    let modeLabel = ""

    if ((micManualMode === "auto" || !micManualMode) && nowMode === "silence") {
      cmd = { id: "nothing", label: "Off", color: "#333", repeats: 1, duration: 0.1 }
      modeLabel = "—"
    } else if ((micManualMode === "auto" || !micManualMode) && nowMode === "drop" && modeAge < 350) {
      const whiteCmds = pool.fullPool.filter(c => c.id.includes("white") || c.category === "white" || c.category === "effects")
      const src = whiteCmds.length > 0 ? whiteCmds : pool.fullPool
      const picked = src[Math.floor(Math.random() * src.length)]
      cmd = { ...picked, repeats: 3, duration: 0.1 }
      modeLabel = "💥 DROP"
    } else if ((micManualMode === "auto" || !micManualMode) && nowMode === "peak") {
      const bright = pool.fullPool.filter(c => ["gold", "red", "white", "magenta"].includes(c.category))
      const src = bright.length > 0 ? bright : pool.fullPool
      const picked = src[Math.floor(Math.random() * src.length)]
      cmd = { ...picked, repeats: 2, duration: 0.15 }
      modeLabel = "🔥 PEAK"
    } else if ((micManualMode === "auto" || !micManualMode) && nowMode === "percussion") {
      const bright = pool.fullPool.filter(c => ["gold", "red", "white", "magenta"].includes(c.category))
      const src = bright.length > 0 ? bright : pool.fullPool
      const picked = src[Math.floor(Math.random() * src.length)]
      cmd = { ...picked, repeats: 1, duration: 0.06 }
      modeLabel = "⚡ PERCUSSION"
    } else if ((micManualMode === "auto" || !micManualMode) && nowMode === "buildup") {
      const bright = pool.fullPool.filter(c => ["gold", "red", "white", "turquoise"].includes(c.category))
      const src = bright.length > 0 ? bright : pool.fullPool
      const picked = src[Math.floor(Math.random() * src.length)]
      cmd = { ...picked, repeats: 2, duration: 0.25 }
      modeLabel = "⬆ BUILDUP"
    } else if ((micManualMode === "auto" || !micManualMode) && nowMode === "drive") {
      const picked = pool.fullPool[Math.floor(Math.random() * pool.fullPool.length)]
      cmd = { ...picked, repeats: 2, duration: 0.35 }
      modeLabel = "🏁 DRIVE"
    } else if ((micManualMode === "auto" || !micManualMode) && nowMode === "groove") {
      const picked = pool.fullPool[Math.floor(Math.random() * pool.fullPool.length)]
      cmd = { ...picked, repeats: 3, duration: 0.5 }
      modeLabel = "🎵 GROOVE"
    } else if ((micManualMode === "auto" || !micManualMode) && nowMode === "breakdown") {
      const quiet = pool.fullPool.filter(c => ["wine", "blue", "magenta", "turquoise"].includes(c.category))
      const src = quiet.length > 0 ? quiet : pool.fullPool
      const picked = src[Math.floor(Math.random() * src.length)]
      cmd = { ...picked, repeats: 3, duration: 1.0 }
      modeLabel = "🌊 BREAKDOWN"
    } else if ((micManualMode === "auto" || !micManualMode) && nowMode === "noise") {
      const picked = pool.fullPool[Math.floor(Math.random() * pool.fullPool.length)]
      cmd = { ...picked, repeats: 1, duration: 0.08 }
      modeLabel = "🌀 NOISE"
    } else if ((micManualMode === "auto" || !micManualMode) && nowMode === "ambient") {
      const spike = detectRecentSpike()
      if (spike) {
        const bright = pool.fullPool.filter(c => ["gold", "red", "white", "magenta"].includes(c.category))
        const src = bright.length > 0 ? bright : pool.fullPool
        const picked = src[Math.floor(Math.random() * src.length)]
        cmd = { ...picked, repeats: 1, duration: 0.08 }
        modeLabel = "💥 AMBIENT SPIKE"
      } else {
        const quiet = pool.fullPool.filter(c => ["wine", "blue", "white", "turquoise", "magenta"].includes(c.category))
        const src = quiet.length > 0 ? quiet : pool.fullPool
        const picked = src[Math.floor(Math.random() * src.length)]
        cmd = { ...picked, repeats: 2, duration: 0.8 }
        modeLabel = "🌙 AMBIENT"
      }
    } else if (micManualMode === "strobe_w") {
      cmd = { id: "white_blink", label: "White Blink", color: "#FFFFFF", repeats: 1, duration: 0.05 }
      modeLabel = "⚡ STROBE W"
    } else if (micManualMode === "strobe_wr") {
      const wrColors = [["white_blink","#FFFFFF"],["red_fastblink","#FF4444"],["turq_blink","#00CED1"]]
      strobeStep = (strobeStep + 1) % wrColors.length
      const [wid,wcol] = wrColors[strobeStep]
      cmd = { id: wid, label: wid === "white_blink" ? "White Blink" : wid === "red_fastblink" ? "Red Fast Blink" : "Turq Blink", color: wcol, repeats: 1, duration: 0.05 }
      modeLabel = "⚡ STROBE W+R"
    } else if (micManualMode === "strobe_r") {
      cmd = { id: "red_fastblink", label: "Red Fast Blink", color: "#FF4444", repeats: 1, duration: 0.05 }
      modeLabel = "⚡ STROBE R"
    } else if (micManualMode === "strobe_t") {
      cmd = { id: "turq_blink", label: "Turq Blink", color: "#00CED1", repeats: 1, duration: 0.05 }
      modeLabel = "⚡ STROBE T"
    } else if (micManualMode === "fade") {
      const fadeCmds = pool.fullPool.filter(c =>
        c.id.includes("fade") || ["wine", "blue", "white", "turquoise"].includes(c.category)
      )
      const src = fadeCmds.length > 0 ? fadeCmds : pool.fullPool
      const picked = src[Math.floor(Math.random() * src.length)]
      cmd = { ...picked, repeats: 3, duration: 1.5 }
      modeLabel = "🌊 FADE"
    }

    lastMicCommandTime = now
    if (cmd) {
      sendCommandLive(cmd.id, cmd.repeats || 2)
      const status = document.getElementById("mic-status")
      if (status) {
        status.textContent = modeLabel || cmd.label || cmd.id
        if (micManualMode === "strobe_w") status.style.color = "#FFFFFF"
        else if (micManualMode === "strobe_wr") status.style.color = "#FF6666"
        else if (micManualMode === "strobe_r") status.style.color = "#FF0000"
        else if (micManualMode === "fade") status.style.color = "#44ff88"
        else if (micManualMode === "random") status.style.color = "#FFD700"
        else status.style.color = "var(--accent)"
      }
    }
  }

  const debug = document.getElementById("mic-debug")
  if (debug) {
    const tempo = getTempoInfo()
    const sectionAge = ((performance.now() - micSectionStartTime) / 1000).toFixed(1)
    debug.innerHTML =
      `E: ${features.totalEnergy.toFixed(2)} | ` +
      `B: ${features.bandEnergies.bass.toFixed(2)} | ` +
      `F: ${features.flux.toFixed(2)} | ` +
      `O: ${features.onsetStrength.toFixed(3)} | ` +
      `${micBeatLocked ? '🎵' + tempo.bpm : '⏱...'} | ` +
      `Sec: <strong>${micManualSection ? '🔒' + micManualSection : nowMode}</strong> ` +
      `(${sectionAge}s) | ` +
      `Secs: ${micKnownSections.length} | ` +
      `Key: ${micDetectedKey ? micDetectedKey.name : '...'} | ` +
      `Mood: ${micDetectedMood || '...'}`
  }

  micAnimationId = requestAnimationFrame(processMicAudio)
}

/* === End Mic Mode === */

document.addEventListener("keydown", (e) => {
  if (micActive && !e.target.closest("input, select, textarea")) {
    const key = e.key.toLowerCase()
    if (key === "s") { setMicMode("strobe_w"); e.preventDefault(); }
    else if (key === "a") { setMicMode("strobe_wr"); e.preventDefault(); }
    else if (key === "w") { setMicMode("strobe_r"); e.preventDefault(); }
    else if (key === "q") { setMicMode("strobe_t"); e.preventDefault(); }
    else if (key === "f") { setMicMode("fade"); e.preventDefault(); }
    else if (key === "h") { setMicMode("random"); e.preventDefault(); }
    else if (key === "d") { triggerDrop(); e.preventDefault(); }
    const sectionKeys = { z:"silence", x:"ambient", c:"breakdown", v:"groove", b:"drive", n:"buildup", m:"percussion" }
    if (key in sectionKeys) {
      micManualSection = sectionKeys[key]
      micEnergyMode = micManualSection
      micEnergyModeSince = performance.now()
      showToast(`Section locked: ${micManualSection}`, "info")
      e.preventDefault()
    }
    if (key === "escape" && micManualSection) {
      micManualSection = null
      showToast("Section auto", "info")
      e.preventDefault()
    }
  }
  if (e.key === "Delete" || e.key === "Backspace") {
    if (selectedEvent && !e.target.closest("input, select, textarea")) {
      deleteSelectedEvent()
    }
  }
  if ((e.ctrlKey || e.metaKey) && e.key === "s") {
    e.preventDefault()
    saveShow()
  }
})
document.addEventListener("keyup", (e) => {
  if (micActive && micManualMode && !e.target.closest("input, select, textarea")) {
    const key = e.key.toLowerCase()
    if (["s","a","w","q","f","h"].includes(key)) {
      setMicMode("auto")
    }
  }
})
