let timelineEvents = []
let timelineDuration = 30
let timelineBPM = 120
let zoomLevel = 100
let scrollLeft = 0
let currentTime = 0
let isDragging = false
let dragEvent = null
let dragOffsetX = 0
let selectedEvent = null
let snapToGrid = true

const timelineCallbacks = {
  onChange: null,
  onEventSelect: null,
  onDurationChange: null,
}

function initTimeline() {
  const canvas = document.getElementById("timeline-canvas")
  if (!canvas) return

  const container = canvas.parentElement
  function resize() {
    canvas.width = container.clientWidth
    canvas.height = container.clientHeight
    renderTimeline()
  }
  window.addEventListener("resize", resize)
  setTimeout(resize, 50)

  canvas.addEventListener("mousedown", onTimelineMouseDown)
  canvas.addEventListener("mousemove", onTimelineMouseMove)
  canvas.addEventListener("mouseup", onTimelineMouseUp)
  canvas.addEventListener("mouseleave", onTimelineMouseUp)
  canvas.addEventListener("wheel", onTimelineWheel)
  canvas.addEventListener("dblclick", onTimelineDblClick)
  canvas.addEventListener("contextmenu", (e) => e.preventDefault())

  canvas.addEventListener("dragover", (e) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "copy"
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left + scrollLeft
    const time = x / zoomLevel
    drawDropIndicator(time)
  })

  canvas.addEventListener("dragleave", () => {
    clearDropIndicator()
  })

  canvas.addEventListener("drop", (e) => {
    e.preventDefault()
    clearDropIndicator()
    try {
      const cmd = JSON.parse(e.dataTransfer.getData("text/plain"))
      const rect = canvas.getBoundingClientRect()
      const x = e.clientX - rect.left + scrollLeft
      const time = snapToGrid ? snapToGridValue(x / zoomLevel) : x / zoomLevel
      addTimelineEvent({
        time: Math.max(0, time),
        command: cmd.id,
        label: cmd.label,
        color: cmd.color,
        repeats: 2,
        duration: 0.3,
      })
    } catch (err) {
      // ignore
    }
  })
}

function snapTime(time) {
  if (!snapToGrid) return time
  return snapToGridValue(time)
}

function snapToGridValue(time) {
  const gridSize = 0.1
  return Math.round(time / gridSize) * gridSize
}

function addTimelineEvent(event) {
  timelineEvents.push({
    ...event,
    id: event.id || "evt_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
  })
  timelineEvents.sort((a, b) => a.time - b.time)
  if (event.time + 1 > timelineDuration) {
    timelineDuration = Math.ceil(event.time + 5)
    if (timelineCallbacks.onDurationChange) timelineCallbacks.onDurationChange(timelineDuration)
  }
  renderTimeline()
  if (timelineCallbacks.onChange) timelineCallbacks.onChange(timelineEvents)
}

function removeTimelineEvent(id) {
  timelineEvents = timelineEvents.filter((e) => e.id !== id)
  selectedEvent = null
  renderTimeline()
  if (timelineCallbacks.onChange) timelineCallbacks.onChange(timelineEvents)
  updateEventInspector(null)
}

function updateTimelineEvent(id, changes) {
  const idx = timelineEvents.findIndex((e) => e.id === id)
  if (idx === -1) return
  timelineEvents[idx] = { ...timelineEvents[idx], ...changes }
  renderTimeline()
  if (timelineCallbacks.onChange) timelineCallbacks.onChange(timelineEvents)
}

function clearTimeline() {
  timelineEvents = []
  selectedEvent = null
  renderTimeline()
  if (timelineCallbacks.onChange) timelineCallbacks.onChange(timelineEvents)
  updateEventInspector(null)
}

function renderTimeline() {
  const canvas = document.getElementById("timeline-canvas")
  if (!canvas) { console.log("renderTimeline: canvas not found"); return }

  const ctx = canvas.getContext("2d")
  const w = canvas.width
  const h = canvas.height
  if (w === 0 || h === 0) console.log(`renderTimeline: canvas has zero dimensions (${w}x${h})`)
  const totalWidth = timelineDuration * zoomLevel

  ctx.clearRect(0, 0, w, h)
  ctx.save()
  ctx.translate(-scrollLeft, 0)

  drawGrid(ctx, totalWidth, h)
  drawWaveformOverlay(ctx, totalWidth, h)
  drawEvents(ctx, totalWidth, h)
  drawPlayhead(ctx, h)
  drawTimeRuler(ctx, totalWidth, h)

  ctx.restore()

  updateScrollbar(totalWidth, w)
}

function drawGrid(ctx, totalWidth, h) {
  const gridSize = 0.5
  const pxInterval = gridSize * zoomLevel

  ctx.strokeStyle = "rgba(255,255,255,0.06)"
  ctx.lineWidth = 1

  const startBeat = Math.floor(scrollLeft / pxInterval)
  const endBeat = Math.ceil((scrollLeft + ctx.canvas.width) / pxInterval)

  for (let i = startBeat; i <= endBeat; i++) {
    const x = i * pxInterval
    if (i % 2 === 0) {
      ctx.strokeStyle = "rgba(255,255,255,0.1)"
      ctx.lineWidth = 1
    } else {
      ctx.strokeStyle = "rgba(255,255,255,0.04)"
      ctx.lineWidth = 0.5
    }
    ctx.beginPath()
    ctx.moveTo(x, 20)
    ctx.lineTo(x, h)
    ctx.stroke()
  }
}

function drawTimeRuler(ctx, totalWidth, h) {
  const rulerH = 20

  ctx.fillStyle = "rgba(0,0,0,0.5)"
  ctx.fillRect(0, 0, totalWidth, rulerH)

  ctx.fillStyle = "#888"
  ctx.font = "10px monospace"
  ctx.textAlign = "center"

  const interval = Math.max(1, Math.ceil(50 / zoomLevel))
  const pxInterval = interval * zoomLevel

  const start = Math.floor(scrollLeft / pxInterval)
  const end = Math.ceil((scrollLeft + ctx.canvas.width) / pxInterval)

  for (let i = start; i <= end; i++) {
    const x = i * pxInterval
    ctx.fillStyle = "#888"
    ctx.fillText(formatTime(i * interval) + "     ", x + 4, 13)
    ctx.fillStyle = "rgba(255,255,255,0.15)"
    ctx.fillRect(x, rulerH, 1, h - rulerH)
  }
}

function drawEvents(ctx, totalWidth, h) {
  ctx.save()
  ctx.setTransform(1, 0, 0, 1, 0, 0)

  console.log(`drawEvents: ${timelineEvents.length} events, totalWidth=${totalWidth}, h=${h}`)

  ctx.fillStyle = "#00ff00"
  ctx.fillRect(50, 50, 200, 40)
  ctx.fillStyle = "#ffffff"
  ctx.font = "bold 20px monospace"
  ctx.fillText(`Events: ${timelineEvents.length}`, 60, 80)

  ctx.restore()

  for (const evt of timelineEvents) {
    const x = evt.time * zoomLevel
    const durPx = Math.max(6, evt.duration * zoomLevel)

    if (x + durPx < scrollLeft || x > scrollLeft + ctx.canvas.width) continue

    const y = 20
    const hh = h - 20 - 4

    ctx.fillStyle = evt.color || "#4A9EFF"
    ctx.globalAlpha = 0.85 + (selectedEvent && selectedEvent.id === evt.id ? 0.15 : 0)
    const bx = x
    const by = y + 2
    const bw = durPx
    const bh = hh - 4
    ctx.fillRect(bx, by, bw, bh)

    ctx.globalAlpha = 1

    ctx.beginPath()
    ctx.strokeStyle = "#ffffff"
    ctx.lineWidth = 1
    ctx.strokeRect(bx, by, bw, bh)

    if (durPx > 20) {
      ctx.fillStyle = "#fff"
      ctx.font = "9px monospace"
      ctx.textAlign = "left"
      ctx.fillText(evt.label || evt.command, x + 4, y + hh / 2 + 3)
    }
  }
}

function drawPlayhead(ctx, h) {
  const x = currentTime * zoomLevel
  ctx.strokeStyle = "#FFD700"
  ctx.lineWidth = 2
  ctx.shadowColor = "#FFD700"
  ctx.shadowBlur = 8
  ctx.beginPath()
  ctx.moveTo(x, 0)
  ctx.lineTo(x, h)
  ctx.stroke()
  ctx.shadowBlur = 0

  ctx.fillStyle = "#FFD700"
  ctx.beginPath()
  ctx.arc(x, h - 6, 5, 0, Math.PI * 2)
  ctx.fill()
}

function drawWaveformOverlay(ctx, totalWidth, canvasHeight) {
  const waveformCanvas = document.getElementById("waveform-canvas")
  if (!waveformCanvas) return
  const w = Math.min(totalWidth, waveformCanvas.width)
  const h = canvasHeight - 20

  ctx.globalAlpha = 0.25
  try {
    ctx.drawImage(waveformCanvas, 0, 20, w, h)
  } catch (e) {
    console.log("drawWaveformOverlay error:", e)
  }
  ctx.globalAlpha = 1
}

let dropTime = -1
function drawDropIndicator(time) {
  dropTime = time
  renderTimeline()
  const canvas = document.getElementById("timeline-canvas")
  if (!canvas) return
  const ctx = canvas.getContext("2d")
  ctx.save()
  ctx.translate(-scrollLeft, 0)
  const x = time * zoomLevel
  ctx.strokeStyle = "#4A9EFF"
  ctx.lineWidth = 2
  ctx.setLineDash([4, 4])
  ctx.beginPath()
  ctx.moveTo(x, 20)
  ctx.lineTo(x, canvas.height)
  ctx.stroke()
  ctx.setLineDash([])
  ctx.restore()
}

function clearDropIndicator() {
  dropTime = -1
  renderTimeline()
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 100)
  return `${m}:${s.toString().padStart(2, "0")}.${ms.toString().padStart(2, "0")}`
}

function updateScrollbar(totalWidth, viewWidth) {
  const scrollbar = document.getElementById("timeline-scrollbar")
  if (!scrollbar) return
  const ratio = viewWidth / totalWidth
  if (ratio >= 1) {
    scrollbar.style.display = "none"
    return
  }
  scrollbar.style.display = "block"
  const thumbWidth = Math.max(30, ratio * scrollbar.parentElement.clientWidth)
  const maxScroll = totalWidth - viewWidth
  const thumbPos = (scrollLeft / maxScroll) * (scrollbar.parentElement.clientWidth - thumbWidth)

  scrollbar.innerHTML = `<div class="scroll-thumb" style="width:${thumbWidth}px;left:${thumbPos}px"></div>`
  const thumb = scrollbar.querySelector(".scroll-thumb")
  if (thumb) {
    let dragging = false
    let startX = 0
    let startLeft = 0

    thumb.addEventListener("mousedown", (e) => {
      dragging = true
      startX = e.clientX
      startLeft = parseInt(thumb.style.left) || 0
      e.stopPropagation()
    })

    document.addEventListener("mousemove", (e) => {
      if (!dragging) return
      const dx = e.clientX - startX
      const maxThumb = scrollbar.parentElement.clientWidth - thumbWidth
      let newLeft = Math.max(0, Math.min(maxThumb, startLeft + dx))
      thumb.style.left = newLeft + "px"
      scrollLeft = (newLeft / maxThumb) * maxScroll
      renderTimeline()
    })

    document.addEventListener("mouseup", () => {
      dragging = false
    })
  }
}

function onTimelineMouseDown(e) {
  const canvas = document.getElementById("timeline-canvas")
  const rect = canvas.getBoundingClientRect()
  const mx = e.clientX - rect.left + scrollLeft
  const my = e.clientY - rect.top
  const time = mx / zoomLevel

  const clicked = findEventAt(mx, my)
  if (clicked) {
    selectedEvent = clicked
    isDragging = true
    dragEvent = clicked
    dragOffsetX = mx - clicked.time * zoomLevel
    renderTimeline()
    updateEventInspector(clicked)
    if (timelineCallbacks.onEventSelect) timelineCallbacks.onEventSelect(clicked)
  } else {
    selectedEvent = null
    renderTimeline()
    updateEventInspector(null)
    if (timelineCallbacks.onEventSelect) timelineCallbacks.onEventSelect(null)
  }
}

function onTimelineMouseMove(e) {
  if (isDragging && dragEvent) {
    const canvas = document.getElementById("timeline-canvas")
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left + scrollLeft
    let newTime = (mx - dragOffsetX) / zoomLevel
    newTime = snapToGrid ? snapToGridValue(newTime) : newTime
    newTime = Math.max(0, newTime)
    dragEvent.time = newTime
    timelineEvents.sort((a, b) => a.time - b.time)
    renderTimeline()
  }
}

function onTimelineMouseUp(e) {
  if (isDragging && dragEvent) {
    if (timelineCallbacks.onChange) timelineCallbacks.onChange(timelineEvents)
  }
  isDragging = false
  dragEvent = null
}

function onTimelineWheel(e) {
  e.preventDefault()
  const canvas = document.getElementById("timeline-canvas")
  const rect = canvas.getBoundingClientRect()
  const mx = e.clientX - rect.left

  if (e.ctrlKey || e.metaKey) {
    const oldZoom = zoomLevel
    zoomLevel = Math.max(20, Math.min(500, zoomLevel - e.deltaY * 0.5))
    const timeAtMouse = (mx + scrollLeft) / oldZoom
    scrollLeft = timeAtMouse * zoomLevel - mx
    scrollLeft = Math.max(0, scrollLeft)
    renderTimeline()
  } else {
    scrollLeft = Math.max(0, Math.min(timelineDuration * zoomLevel - canvas.width, scrollLeft + e.deltaX * 2 || e.deltaY * 2))
    renderTimeline()
  }
}

function onTimelineDblClick(e) {
  const canvas = document.getElementById("timeline-canvas")
  const rect = canvas.getBoundingClientRect()
  const mx = e.clientX - rect.left + scrollLeft
  const my = e.clientY - rect.top
  const time = snapToGrid ? snapToGridValue(mx / zoomLevel) : mx / zoomLevel

  if (my > 20) {
    addTimelineEvent({
      time: Math.max(0, time),
      command: "gold_fade",
      label: "Gold Fade",
      color: "#FFD700",
      repeats: 2,
      duration: 0.3,
    })
  }
}

function findEventAt(mx, my) {
  if (my < 20) return null
  for (const evt of timelineEvents) {
    const ex = evt.time * zoomLevel
    const ew = Math.max(6, evt.duration * zoomLevel)
    if (mx >= ex - 2 && mx <= ex + ew + 2) {
      return evt
    }
  }
  return null
}

function updateEventInspector(event) {
  const panel = document.getElementById("event-inspector")
  if (!panel) return

  if (!event) {
    panel.classList.remove("visible")
    panel.classList.add("hidden")
    return
  }

  panel.classList.remove("hidden")
  panel.classList.add("visible")

  panel.innerHTML = `
    <div class="inspector-header">
      <span class="inspector-dot" style="background:${event.color || "#4A9EFF"}"></span>
      <span>${event.label || event.command}</span>
      <button class="btn-icon" onclick="deleteSelectedEvent()" title="Delete">🗑️</button>
    </div>
    <div class="inspector-body">
      <label>Time: <input type="number" step="0.1" value="${event.time}" 
        onchange="updateTimelineEvent('${event.id}', {time: parseFloat(this.value) || 0})"></label>
      <label>Duration (s): <input type="number" step="0.05" value="${event.duration}" min="0.05"
        onchange="updateTimelineEvent('${event.id}', {duration: parseFloat(this.value) || 0.3})"></label>
      <label>Repeats: <input type="number" step="1" value="${event.repeats}" min="1"
        onchange="updateTimelineEvent('${event.id}', {repeats: parseInt(this.value) || 1})"></label>
      <label>Command:
        <select onchange="updateTimelineEvent('${event.id}', {command: this.value, label: this.options[this.selectedIndex].text, color: this.options[this.selectedIndex].dataset.color})">
          ${COMMANDS.map(c => `<option value="${c.id}" data-color="${c.color}" ${c.id === event.command ? "selected" : ""}>${c.label}</option>`).join("")}
        </select>
      </label>
    </div>
  `
}

function deleteSelectedEvent() {
  if (selectedEvent) {
    removeTimelineEvent(selectedEvent.id)
  }
}

function setTimelinePlaybackTime(time) {
  currentTime = time
  renderTimeline()

  const canvas = document.getElementById("timeline-canvas")
  if (!canvas) return
  const viewWidth = canvas.width
  const playheadX = time * zoomLevel
  if (playheadX < scrollLeft || playheadX > scrollLeft + viewWidth) {
    scrollLeft = Math.max(0, playheadX - viewWidth / 2)
    renderTimeline()
  }
}

function setTimelineDuration(duration) {
  timelineDuration = Math.max(1, duration)
  renderTimeline()
  if (timelineCallbacks.onDurationChange) timelineCallbacks.onDurationChange(timelineDuration)
}

function getTimelineEvents() {
  return [...timelineEvents]
}

function loadTimelineEvents(events) {
  console.log(`loadTimelineEvents: ${events.length} events, first:`, events[0])
  timelineEvents = events.map((e, i) => ({
    ...e,
    id: e.id || "evt_" + i + "_" + Date.now(),
  }))
  scrollLeft = 0
  const canvas = document.getElementById("timeline-canvas")
  console.log(`timelineEvents length: ${timelineEvents.length}, canvas: ${canvas?.width}x${canvas?.height}, zoom: ${zoomLevel}, scroll: ${scrollLeft}`)
  renderTimeline()
  if (timelineCallbacks.onChange) timelineCallbacks.onChange(timelineEvents)
}

function seekTimelineToTime(time) {
  setTimelinePlaybackTime(time)
}
