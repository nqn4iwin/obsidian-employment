document.addEventListener("nav", () => {
  const list = document.querySelector<HTMLUListElement>("[data-employment-pins] > ul")
  if (!list) return

  const storageKey = "employment-pinned-jobs"
  const pinned = new Set<string>()
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(storageKey) ?? "[]")
    if (Array.isArray(stored)) {
      for (const key of stored) if (typeof key === "string") pinned.add(key)
    }
  } catch {
    // Keep pinning available for the current page when storage is unavailable.
  }

  const section = document.createElement("section")
  const heading = document.createElement("h2")
  heading.textContent = "고정한 공고"
  const pinnedList = document.createElement("ul")
  pinnedList.className = list.className
  section.append(heading, pinnedList)
  list.before(section)

  const rows = Array.from(list.querySelectorAll<HTMLLIElement>(":scope > li")).flatMap((row) => {
    const link = row.querySelector<HTMLAnchorElement>("a[data-slug]")
    const key = link?.dataset.slug
    if (!link || !key) return []

    const button = document.createElement("button")
    button.type = "button"
    button.className = "employment-pin"
    button.setAttribute("aria-label", `${link.textContent?.trim()} 고정`)
    row.append(button)
    button.addEventListener("click", () => {
      if (pinned.has(key)) pinned.delete(key)
      else pinned.add(key)
      try {
        localStorage.setItem(storageKey, JSON.stringify([...pinned]))
      } catch {
        // The current page still reflects the selection.
      }
      render()
      button.focus()
    })
    return [{ row, key, button }]
  })

  function render() {
    for (const { row, key, button } of rows) {
      const selected = pinned.has(key)
      button.textContent = selected ? "★" : "☆"
      button.setAttribute("aria-pressed", String(selected))
      const target = selected ? pinnedList : list
      target.append(row)
    }
    section.hidden = pinnedList.childElementCount === 0
  }

  render()
})
