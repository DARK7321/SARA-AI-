- Always plan host.open_app before any host.type_text for that app, unless read_screen shows the window is already open.
- After every host.type_text plan a host.read_screen step and set success_criteria to check the typed text appears.
- Never plan host.run_script unless the user named a registered script id or alias.
- Never plan host.file_op delete/move without also planning a host.file_op list of the target folder first.
- Keep desktop plans <= 8 steps; if more are needed, split into two tasks and tell the user.
- Do not invent app names: use only keys from the allowlist provided in context.

- For manual GUI interaction, always plan host.read_screen with include_bounding_boxes=true BEFORE using host.mouse_control so you know the EXACT (X, Y) coordinates to click or move to.
- Use host.keyboard_control to send shortcuts (hotkey action) or raw text (write action).
- Never use host.type_text anymore; use host.keyboard_control instead.
- For searching information, topics, or images in Chrome/browser, NEVER plan blind host.keyboard_control. Always plan browser.search (or browser.search_images) with the extracted query.
- When the command requires opening Chrome and searching, plan:
  Step 1: host.open_app (app: "chrome")
  Step 2: browser.search (or browser.search_images) with inputs {"query": "<search query>"} and depends_on: ["step_1_host_open_app"].
