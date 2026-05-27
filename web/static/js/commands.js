const COMMAND_CATEGORIES = [
  { id: "system", label: "System", icon: "⚡" },
  { id: "gold", label: "Gold", icon: "✨" },
  { id: "red", label: "Red", icon: "🔴" },
  { id: "blue", label: "Blue", icon: "🔵" },
  { id: "white", label: "White", icon: "⚪" },
  { id: "turquoise", label: "Turquoise", icon: "🩵" },
  { id: "wine", label: "Wine", icon: "🍷" },
  { id: "magenta", label: "Magenta", icon: "💜" },
  { id: "effects", label: "Effects", icon: "🎆" },
  { id: "combos", label: "Combos", icon: "🌈" },
]

let COMMANDS = []

async function loadCommands() {
  const res = await fetch("/api/commands")
  COMMANDS = await res.json()
  return COMMANDS
}

function getCommandsByCategory() {
  const map = {}
  for (const cmd of COMMANDS) {
    if (!map[cmd.category]) map[cmd.category] = []
    map[cmd.category].push(cmd)
  }
  return map
}

function renderCommandPalette(container) {
  container.innerHTML = ""
  const byCat = getCommandsByCategory()

  for (const cat of COMMAND_CATEGORIES) {
    const cmds = byCat[cat.id] || []
    if (cmds.length === 0) continue

    const section = document.createElement("div")
    section.className = "palette-section"

    const header = document.createElement("div")
    header.className = "palette-header"
    header.innerHTML = `<span class="palette-icon">${cat.icon}</span> ${cat.label}`
    section.appendChild(header)

    const grid = document.createElement("div")
    grid.className = "palette-grid"

    for (const cmd of cmds) {
      const btn = document.createElement("button")
      btn.className = "palette-command"
      btn.dataset.command = cmd.id
      btn.dataset.color = cmd.color
      btn.title = cmd.label
      btn.style.setProperty("--cmd-color", cmd.color)
      btn.innerHTML = `<span class="cmd-dot" style="background:${cmd.color}"></span><span class="cmd-label">${cmd.label}</span>`
      btn.draggable = true

      btn.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("text/plain", JSON.stringify(cmd))
        e.dataTransfer.effectAllowed = "copy"
        btn.classList.add("dragging")
      })
      btn.addEventListener("dragend", () => {
        btn.classList.remove("dragging")
      })
      btn.addEventListener("dragleave", () => {
        btn.classList.remove("dragging")
      })

      btn.addEventListener("click", (e) => {
        btn.classList.remove("dragging")
        addTimelineEvent({
          time: 0,
          command: cmd.id,
          label: cmd.label,
          color: cmd.color,
          repeats: 2,
          duration: 0.3,
        })
      })

      grid.appendChild(btn)
    }

    section.appendChild(grid)
    container.appendChild(section)
  }
}
