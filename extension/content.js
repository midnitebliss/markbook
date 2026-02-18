(async () => {
  const SERVER = "http://localhost:7799/api/bookmarks";
  const SCROLL_PAUSE = 2000;
  const MAX_NO_NEW = 5;

  function notify(type, data) {
    chrome.runtime.sendMessage({ type, ...data });
  }

  function extractTweet(article) {
    try {
      // Tweet ID and URL
      let tweetId = null;
      let tweetUrl = null;
      const links = article.querySelectorAll('a[href*="/status/"]');
      for (const link of links) {
        const href = link.getAttribute("href") || "";
        if (href.includes("/status/") && !href.includes("/photo/") && !href.includes("/analytics")) {
          tweetId = href.split("/status/")[1].split("?")[0].split("/")[0];
          tweetUrl = href.startsWith("/") ? "https://x.com" + href : href;
          break;
        }
      }
      if (!tweetId) return null;

      // Tweet text
      const textEl = article.querySelector('[data-testid="tweetText"]');
      const text = textEl ? textEl.innerText : "";

      // Author
      let authorName = null;
      let authorHandle = null;
      const userLinks = article.querySelectorAll('a[role="link"]');
      for (const ul of userLinks) {
        const href = ul.getAttribute("href") || "";
        if (href.startsWith("/") && !href.includes("/status/") && href !== "/") {
          const handle = href.replace(/^\//, "").split("/")[0];
          if (handle && !handle.startsWith("i/") && !handle.startsWith("search")) {
            authorHandle = handle;
            const spans = ul.querySelectorAll("span");
            for (const s of spans) {
              const t = s.innerText.trim();
              if (t && !t.startsWith("@")) {
                authorName = t;
                break;
              }
            }
            break;
          }
        }
      }

      // Timestamp
      const timeEl = article.querySelector("time");
      const createdAt = timeEl ? timeEl.getAttribute("datetime") : null;

      // Media
      const mediaUrls = [];
      const imgs = article.querySelectorAll('[data-testid="tweetPhoto"] img');
      for (const img of imgs) {
        const src = img.getAttribute("src") || "";
        if (src && !src.includes("emoji") && !src.includes("profile")) {
          mediaUrls.push(src);
        }
      }

      // Engagement metrics
      function getMetric(testid) {
        const el = article.querySelector(`[data-testid="${testid}"]`);
        if (el) {
          const aria = el.getAttribute("aria-label") || "";
          const parts = aria.split(" ");
          if (parts.length && parts[0].replace(/,/g, "").match(/^\d+$/)) {
            return parseInt(parts[0].replace(/,/g, ""), 10);
          }
        }
        return 0;
      }

      return {
        tweet_id: tweetId,
        url: tweetUrl,
        text,
        author_name: authorName,
        author_handle: authorHandle,
        created_at: createdAt,
        media_urls: mediaUrls,
        like_count: getMetric("like"),
        retweet_count: getMetric("retweet"),
        reply_count: getMetric("reply"),
      };
    } catch (e) {
      console.warn("markbook: failed to parse tweet", e);
      return null;
    }
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  try {
    notify("progress", { text: "Scrolling through bookmarks..." });

    const allBookmarks = {};
    let noNewCount = 0;

    while (noNewCount < MAX_NO_NEW) {
      const articles = document.querySelectorAll("article");

      let newFound = 0;
      for (const article of articles) {
        const data = extractTweet(article);
        if (data && !allBookmarks[data.tweet_id]) {
          allBookmarks[data.tweet_id] = data;
          newFound++;
        }
      }

      const total = Object.keys(allBookmarks).length;

      if (newFound > 0) {
        noNewCount = 0;
        notify("progress", { text: `Found ${total} bookmarks so far...` });
      } else {
        noNewCount++;
      }

      window.scrollBy(0, window.innerHeight * 2);
      await sleep(SCROLL_PAUSE);
    }

    const bookmarks = Object.values(allBookmarks);
    notify("progress", { text: `Sending ${bookmarks.length} bookmarks to server...` });

    // Send to local server
    const resp = await fetch(SERVER, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(bookmarks),
    });

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`Server returned ${resp.status}: ${errText}`);
    }

    const result = await resp.json();
    notify("done", { count: result.count });
  } catch (e) {
    notify("error", { text: e.message });
  }
})();
