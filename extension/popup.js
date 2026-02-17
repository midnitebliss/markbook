const btn = document.getElementById("fetch");
const status = document.getElementById("status");

function showStatus(text, type) {
  status.style.display = "block";
  status.className = type || "";
  status.textContent = text;
}

btn.addEventListener("click", async () => {
  btn.disabled = true;
  showStatus("Starting...");

  try {
    // Get the active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab.url || !tab.url.includes("x.com")) {
      showStatus("Please navigate to x.com/i/bookmarks first.", "error");
      btn.disabled = false;
      return;
    }

    // Listen for progress messages from the content script
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg.type === "progress") {
        showStatus(msg.text);
      } else if (msg.type === "done") {
        showStatus(`Done! ${msg.count} bookmarks saved.`, "success");
        btn.disabled = false;
      } else if (msg.type === "error") {
        showStatus(`Error: ${msg.text}`, "error");
        btn.disabled = false;
      }
    });

    // Inject and run the content script
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content.js"],
    });
  } catch (e) {
    showStatus(`Error: ${e.message}`, "error");
    btn.disabled = false;
  }
});
