let audioContext = null
let audioBuffer = null
let audioSource = null
let analyserNode = null
let isPlaying = false
let startTime = 0
let pauseOffset = 0
let animationId = null
let gainNode = null
let detectedBPM = 120

const audioCallbacks = { onTimeUpdate: null, onPlayStateChange: null, onLoad: null }

function getAudioContext() {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)()
  }
  return audioContext
}

async function loadAudio(file) {
  const ctx = getAudioContext()
  const arrayBuffer = await file.arrayBuffer()
  audioBuffer = await ctx.decodeAudioData(arrayBuffer)
  if (audioCallbacks.onLoad) audioCallbacks.onLoad(audioBuffer)
  return audioBuffer
}

function drawWaveform(canvas, buffer, color = "#4A9EFF") {
  const ctx = canvas.getContext("2d")
  const w = canvas.width
  const h = canvas.height
  const data = buffer.getChannelData(0)
  const step = Math.ceil(data.length / w)
  const amp = h / 2

  ctx.clearRect(0, 0, w, h)

  ctx.fillStyle = "rgba(74, 158, 255, 0.05)"
  ctx.fillRect(0, 0, w, h)

  ctx.beginPath()
  ctx.moveTo(0, amp)

  for (let i = 0; i < w; i++) {
    let min = 1.0
    let max = -1.0
    for (let j = 0; j < step; j++) {
      const idx = i * step + j
      if (idx < data.length) {
        const datum = data[idx]
        if (datum < min) min = datum
        if (datum > max) max = datum
      }
    }
    ctx.lineTo(i, amp + min * amp * 0.8)
  }

  for (let i = w - 1; i >= 0; i--) {
    let min = 1.0
    let max = -1.0
    for (let j = 0; j < step; j++) {
      const idx = i * step + j
      if (idx < data.length) {
        const datum = data[idx]
        if (datum < min) min = datum
        if (datum > max) max = datum
      }
    }
    ctx.lineTo(i, amp + max * amp * 0.8)
  }

  ctx.closePath()
  const gradient = ctx.createLinearGradient(0, 0, 0, h)
  gradient.addColorStop(0, "rgba(74, 158, 255, 0.3)")
  gradient.addColorStop(0.5, "rgba(74, 158, 255, 0.15)")
  gradient.addColorStop(1, "rgba(74, 158, 255, 0.3)")
  ctx.fillStyle = gradient
  ctx.fill()
  ctx.strokeStyle = color
  ctx.lineWidth = 1
  ctx.stroke()
}

function getAudioDuration() {
  return audioBuffer ? audioBuffer.duration : 0
}

function playAudio(fromTime = 0) {
  if (isPlaying) return
  const ctx = getAudioContext()
  if (ctx.state === "suspended") ctx.resume()

  audioSource = ctx.createBufferSource()
  audioSource.buffer = audioBuffer

  gainNode = ctx.createGain()
  gainNode.gain.value = 1.0

  analyserNode = ctx.createAnalyser()
  analyserNode.fftSize = 2048

  audioSource.connect(analyserNode)
  analyserNode.connect(gainNode)
  gainNode.connect(ctx.destination)

  pauseOffset = fromTime
  audioSource.start(0, fromTime)
  isPlaying = true
  startTime = ctx.currentTime - fromTime

  if (audioCallbacks.onPlayStateChange) audioCallbacks.onPlayStateChange(true)
  startTimeUpdateLoop()
}

function pauseAudio() {
  if (!isPlaying || !audioSource) return
  const ctx = getAudioContext()
  pauseOffset = ctx.currentTime - startTime
  try { audioSource.stop() } catch (e) {}
  isPlaying = false
  stopTimeUpdateLoop()
  if (audioCallbacks.onPlayStateChange) audioCallbacks.onPlayStateChange(false)
}

function stopAudio() {
  if (audioSource) {
    try { audioSource.stop() } catch (e) {}
  }
  isPlaying = false
  pauseOffset = 0
  stopTimeUpdateLoop()
  if (audioCallbacks.onPlayStateChange) audioCallbacks.onPlayStateChange(false)
}

function getCurrentTime() {
  if (!isPlaying) return pauseOffset
  const ctx = getAudioContext()
  return ctx.currentTime - startTime
}

function setVolume(v) {
  if (gainNode) gainNode.gain.value = Math.max(0, v)
}

function startTimeUpdateLoop() {
  const loop = () => {
    if (!isPlaying) return
    if (audioCallbacks.onTimeUpdate) audioCallbacks.onTimeUpdate(getCurrentTime())
    animationId = requestAnimationFrame(loop)
  }
  animationId = requestAnimationFrame(loop)
}

function stopTimeUpdateLoop() {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }
}

function getAnalyserData() {
  if (!analyserNode) return null
  const data = new Uint8Array(analyserNode.frequencyBinCount)
  analyserNode.getByteFrequencyData(data)
  return data
}

function detectBPM(buffer) {
  const data = buffer.getChannelData(0)
  const sr = buffer.sampleRate

  const windowSize = Math.round(sr * 0.05)
  const energy = []
  for (let i = 0; i < data.length; i += Math.round(windowSize / 2)) {
    let sum = 0
    const end = Math.min(i + windowSize, data.length)
    for (let j = i; j < end; j++) {
      sum += data[j] * data[j]
    }
    energy.push(sum / (end - i))
  }

  const minBPM = 60
  const maxBPM = 200
  const minLag = Math.round((60 / maxBPM) * sr / (windowSize / 2))
  const maxLag = Math.round((60 / minBPM) * sr / (windowSize / 2))

  let bestBPM = 120
  let bestScore = 0

  for (let lag = minLag; lag <= maxLag; lag++) {
    let score = 0
    let count = 0
    for (let i = 0; i + lag < energy.length; i++) {
      score += energy[i] * energy[i + lag]
      count++
    }
    score = count > 0 ? score / count : 0
    if (score > bestScore) {
      bestScore = score
      bestBPM = Math.round(60 / ((lag * (windowSize / 2)) / sr))
    }
  }

  const harmonicBPMs = [bestBPM / 2, bestBPM, bestBPM * 2]
  const validBPMs = harmonicBPMs.filter(b => b >= minBPM && b <= maxBPM)

  let finalBPM = 120
  let finalScore = 0
  for (const bpm of validBPMs) {
    const lag = Math.round((60 / bpm) * sr / (windowSize / 2))
    if (lag >= minLag && lag <= maxLag) {
      let score = 0
      let count = 0
      for (let i = 0; i + lag < energy.length; i++) {
        score += energy[i] * energy[i + lag]
        count++
      }
      score = count > 0 ? score / count : 0
      if (score > finalScore) {
        finalScore = score
        finalBPM = Math.round(bpm)
      }
    }
  }

  detectedBPM = finalBPM
  return detectedBPM
}

const ENERGY_CLASS = { SILENCE: "silence", QUIET: "quiet", MEDIUM: "medium", LOUD: "loud", PEAK: "peak" }

function analyzeAudioDeep(buffer) {
  const data = buffer.getChannelData(0)
  const sr = buffer.sampleRate
  const windowMs = 50
  const hopMs = 25
  const windowSamples = Math.round(sr * windowMs / 1000)
  const hopSamples = Math.round(sr * hopMs / 1000)

  const frames = []
  for (let i = 0; i < data.length; i += hopSamples) {
    let sumSq = 0, peak = 0, zcr = 0, bassSumSq = 0, highSumSq = 0
    const end = Math.min(i + windowSamples, data.length)
    const n = end - i
    const decStep = Math.max(1, Math.round(sr / 4000))

    for (let j = i; j < end; j++) {
      const s = data[j]
      sumSq += s * s
      const abs = Math.abs(s)
      if (abs > peak) peak = abs
      if (j > i && (s * data[j - 1] < 0)) zcr++

      // Bass energy: decimated signal (low-pass via local averaging)
      // Divide by decStep to avoid double-counting
      if ((j - i) % decStep === 0) {
        // Simple: just accumulate every decStep sample for "sub" feel
        bassSumSq += s * s
      }
      // High-frequency energy: first-difference (emphasizes transients)
      if (j > i) {
        const diff = s - data[j - 1]
        highSumSq += diff * diff
      }
    }

    const zcrRate = n > 1 ? zcr / (n - 1) : 0
    const bassN = Math.ceil(n / decStep)
    frames.push({
      time: i / sr,
      rms: Math.sqrt(sumSq / n),
      peak,
      zcrRate,
      bassEnergy: Math.sqrt(bassSumSq / bassN),
      highEnergy: Math.sqrt(highSumSq / n),
    })
  }

  const rmsValues = frames.map(f => f.rms)
  const sorted = [...rmsValues].sort((a, b) => a - b)
  const median = sorted[Math.floor(sorted.length / 2)] || 0.001
  const p95 = sorted[Math.floor(sorted.length * 0.95)] || 0.01

  let silenceFloor = median * 1.2
  const noiseFloor = sorted[Math.floor(sorted.length * 0.05)] || 0.0001
  silenceFloor = Math.max(silenceFloor, noiseFloor * 2)

  for (const f of frames) {
    if (f.rms < silenceFloor) {
      f.energyClass = ENERGY_CLASS.SILENCE
    } else if (f.rms < p95 * 0.35) {
      f.energyClass = ENERGY_CLASS.QUIET
    } else if (f.rms < p95 * 0.65) {
      f.energyClass = ENERGY_CLASS.MEDIUM
    } else if (f.rms < p95 * 0.9) {
      f.energyClass = ENERGY_CLASS.LOUD
    } else {
      f.energyClass = ENERGY_CLASS.PEAK
    }
    f.energyNorm = Math.min(1, f.rms / p95)
  }

  const minSilenceMs = 80
  const minSilenceFrames = Math.round(minSilenceMs / hopMs)
  for (let i = 1; i < frames.length; i++) {
    if (frames[i].energyClass !== ENERGY_CLASS.SILENCE &&
        frames[i - 1].energyClass === ENERGY_CLASS.SILENCE) {
      let j = i - 1
      let count = 0
      while (j >= 0 && frames[j].energyClass === ENERGY_CLASS.SILENCE && count < minSilenceFrames) {
        count++
        j--
      }
      if (count < minSilenceFrames) {
        for (let k = j + 1; k < i; k++) {
          frames[k].energyClass = frames[i].energyClass
        }
      }
    }
  }

  const sections = []
  let start = 0
  for (let i = 1; i <= frames.length; i++) {
    if (i === frames.length || frames[i].energyClass !== frames[start].energyClass) {
      const dur = frames[i - 1].time + (hopMs / 1000) - frames[start].time
      if (dur > 0.15) {
        const slice = frames.slice(start, i)
        const avgEnergy = slice.reduce((s, f) => s + f.energyNorm, 0) / slice.length
        const peakIdx = slice.reduce((best, f, idx) => f.energyNorm > slice[best].energyNorm ? idx : best, 0)
        const avgZcr = slice.reduce((s, f) => s + f.zcrRate, 0) / slice.length
        const avgBass = slice.reduce((s, f) => s + f.bassEnergy, 0) / slice.length
        const avgHigh = slice.reduce((s, f) => s + f.highEnergy, 0) / slice.length
        sections.push({
          time: frames[start].time,
          duration: dur,
          endTime: frames[i - 1].time + (hopMs / 1000),
          energyClass: frames[start].energyClass,
          avgEnergy,
          peakEnergy: slice[peakIdx].energyNorm,
          peakTime: frames[start + peakIdx].time,
          peakRatio: peakIdx / slice.length,
          frameEnergies: slice.map(f => f.energyNorm),
          avgZcr,
          avgBass,
          avgHigh,
        })
      }
      start = i
    }
  }

  // --- Section profiling and repeat detection ---
  function makeProfile(sec) {
    return { e: sec.avgEnergy, p: sec.peakEnergy, z: sec.avgZcr, b: sec.avgBass, h: sec.avgHigh, d: sec.duration }
  }

  function profileSim(a, b) {
    let s = 0
    const pairs = [['e','e'],['p','p'],['z','z'],['b','b'],['h','h'],['d','d']]
    for (const [ka, kb] of pairs) {
      const va = a[ka] || 0, vb = b[kb] || 0
      const m = Math.max(Math.abs(va), Math.abs(vb), 0.01)
      s += Math.max(0, 1 - Math.abs(va - vb) / m)
    }
    return s / pairs.length
  }

  const totalTime = frames.length > 0 ? frames[frames.length - 1].time : 240
  const numEighths = 8
  const eighthDur = totalTime / numEighths

  for (let i = 0; i < sections.length; i++) {
    sections[i].familyId = -1
    sections[i].profile = makeProfile(sections[i])
  }

  let nextFamilyId = 0
  for (let i = 0; i < sections.length; i++) {
    if (sections[i].familyId >= 0) continue
    sections[i].familyId = nextFamilyId

    const eighthI = Math.floor(sections[i].time / eighthDur)
    const sameClass = sections[i].energyClass

    for (let j = i + 1; j < Math.min(i + 100, sections.length); j++) {
      if (sections[j].familyId >= 0) continue
      const eighthJ = Math.floor(sections[j].time / eighthDur)

      const classOk = sameClass === sections[j].energyClass ||
        (sameClass === ENERGY_CLASS.MEDIUM && sections[j].energyClass === ENERGY_CLASS.LOUD) ||
        (sameClass === ENERGY_CLASS.LOUD && sections[j].energyClass === ENERGY_CLASS.MEDIUM)
      if (!classOk) continue

      const eighthDist = Math.abs(eighthI - eighthJ)
      if (eighthDist < 2 || eighthDist >= numEighths - 1) continue

      const sim = profileSim(sections[i].profile, sections[j].profile)
      if (sim >= 0.7) {
        sections[j].familyId = nextFamilyId
      }
    }
    nextFamilyId++
  }

  const familyInfo = {}
  for (const sec of sections) {
    if (!familyInfo[sec.familyId]) familyInfo[sec.familyId] = { times: [], classes: {} }
    familyInfo[sec.familyId].times.push(sec.time)
    familyInfo[sec.familyId].classes[sec.energyClass] = (familyInfo[sec.familyId].classes[sec.energyClass] || 0) + 1
  }
  for (const [fid, info] of Object.entries(familyInfo)) {
    info.times.sort((a, b) => a - b)
    const domClass = Object.entries(info.classes).sort((a, b) => b[1] - a[1])[0][0]
    const first8th = Math.floor(info.times[0] / eighthDur)
    const last8th = Math.floor(info.times[info.times.length - 1] / eighthDur)

    let t
    if (first8th <= 0) t = domClass === 'silence' || domClass === 'quiet' ? 'Intro' : 'Verse'
    else if (last8th >= numEighths - 1) t = 'Outro'
    else if (info.times.length >= 2) t = 'Chorus'
    else if (domClass === 'loud' || domClass === 'peak') t = 'Drop'
    else if (domClass === 'silence' || domClass === 'quiet') t = 'Bridge'
    else t = 'Verse'
    if (info.times.length > 1) {
      const occ = info.times.reduce((acc, t) => { acc[t] = (acc[t] || 0) + 1; return acc }, {})
      const idx = Math.min(Object.keys(occ).length - 1, 25)
      t += ' ' + String.fromCharCode(65 + Math.min(idx, 25))
    }
    familyInfo[fid].typeName = t
  }
  for (const sec of sections) {
    sec.familyType = familyInfo[sec.familyId]?.typeName || `S${sec.familyId}`
  }

  // --- Section type classification ---
  for (let i = 0; i < sections.length; i++) {
    const sec = sections[i]
    const e = sec.energyClass
    const fe = sec.frameEnergies
    const half = Math.max(1, Math.floor(fe.length / 2))
    const firstHalf = fe.slice(0, half).reduce((a,b) => a+b, 0) / half
    const secondHalf = fe.slice(half).reduce((a,b) => a+b, 0) / (fe.length - half || 1)
    const highRatio = fe.filter(v => v > 0.5).length / fe.length

    if (e === ENERGY_CLASS.SILENCE) {
      sec.sectionType = 'silence'
    } else if (highRatio > 0.7 && sec.duration > 0.3) {
      sec.sectionType = 'hardcore'
    } else if (sec.avgZcr > 0.12 && sec.avgHigh > sec.avgBass * 1.1) {
      sec.sectionType = 'percussion'
    } else if (secondHalf > firstHalf * 1.4 && sec.duration > 0.4) {
      sec.sectionType = 'buildup'
    } else if (firstHalf > secondHalf * 1.4 && sec.duration > 0.4) {
      sec.sectionType = 'breakdown'
    } else if (i > 0 && sections[i-1].energyClass === ENERGY_CLASS.PEAK && sec.avgEnergy < 0.5) {
      sec.sectionType = 'breakdown'
    } else if (e === ENERGY_CLASS.QUIET || e === ENERGY_CLASS.MEDIUM) {
      sec.sectionType = sec.avgZcr < 0.08 ? 'ambient' : 'verse'
    } else {
      sec.sectionType = 'verse'
    }
  }

  const peaks = []
  for (let i = 2; i < frames.length; i++) {
    const f = frames[i]
    if (f.energyClass === ENERGY_CLASS.LOUD || f.energyClass === ENERGY_CLASS.PEAK) {
      if (f.rms > frames[i - 1].rms && f.rms > frames[i - 2].rms &&
          f.rms > frames[i + 1]?.rms) {
        peaks.push({ time: f.time, intensity: f.energyNorm })
      }
    }
  }

  return { frames, sections, peaks, silenceFloor, p95, median, hopMs, familyInfo }
}

function analyzeBeats(buffer, bpm) {
  const data = buffer.getChannelData(0)
  const sampleRate = buffer.sampleRate
  const beatInterval = 60 / bpm
  const beatSamples = Math.round(beatInterval * sampleRate)
  const windowSize = Math.round(beatSamples * 0.5)

  const energy = []
  for (let i = 0; i < data.length; i += windowSize) {
    let sum = 0
    const end = Math.min(i + windowSize, data.length)
    for (let j = i; j < end; j++) {
      sum += data[j] * data[j]
    }
    energy.push(sum / (end - i))
  }

  const avg = energy.reduce((a, b) => a + b, 0) / energy.length
  const threshold = avg * 1.5

  const beats = []
  for (let i = 1; i < energy.length - 1; i++) {
    if (energy[i] > threshold && energy[i] > energy[i - 1] && energy[i] > energy[i + 1]) {
      const time = (i * windowSize) / sampleRate
      const intensity = Math.min(1, energy[i] / (avg * 3))
      beats.push({ time, intensity })
    }
  }

  return beats
}
